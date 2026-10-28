"""Owned inbox and atomic ordinary gift claims; no external payments."""
import copy
import datetime as dt
import hashlib
import time

from ..common import ProtocolError, compact
from ..policies.instance_ids import allocate_instance_ids
from ..policies.unit_progression import level_exp

PRESENT_FIELDS=('serial_number','send_user_id','send_user_name','message','present_type',
                'present_param_0','present_param_1','date','open_limit')
USER_FIELDS=('user_id','user_name','action_point','action_point_recover','max_action_point',
             'game_money','total_paid_point','paid_point','free_paid_point','friend_point',
             'rank','exp','max_unit','max_cost','max_friend','login_days','sequence_login_days')


def expired(gift):
    if gift['open_limit']==0:return False
    try:
        created=dt.datetime.fromisoformat(gift['date'].replace('Z','+00:00'))
        if created.tzinfo is None:created=created.replace(tzinfo=dt.timezone.utc)
        return time.time()>=created.timestamp()+7*86400
    except (ValueError,TypeError,AttributeError):
        raise ProtocolError(8197,'Invalid gift date')


def issue(state,kind,param,level,message):
    gifts=state.setdefault('presents',[])
    serial=max(state.get('present_serial_high_water',0),
               max((g['serial_number'] for g in gifts),default=0))+1
    state['present_serial_high_water']=serial
    gift=dict(serial_number=serial,send_user_id=0,send_user_name='LOCAL',message=message,
              present_type=kind,present_param_0=param,present_param_1=level,
              date=dt.datetime.fromtimestamp(time.time(),dt.timezone.utc).isoformat(),open_limit=0)
    gifts.append(gift)
    return gift


def get_presents(self,state,req,token,operation):
    result=[{k:g[k] for k in PRESENT_FIELDS} for g in state.get('presents',[]) if not expired(g)]
    return dict(code=4096,session_id=token,result=result)


def open_present(self,state,req,token,operation):
    ids=req.get('serial_number_list')
    if (not isinstance(ids,list) or not 1<=len(ids)<=100
            or any(type(n) is not int or n<=0 for n in ids) or len(set(ids))!=len(ids)):
        raise ProtocolError(8194,'Expected 1-100 unique positive gift serials')
    fingerprint=hashlib.sha256(compact(sorted(ids)).encode()).hexdigest()
    receipts=state.get('present_claim_receipts',{})
    player=state['player'];units=[]
    if fingerprint in receipts:
        receipt=receipts[fingerprint]
        if any(g['serial_number'] in ids for g in state.get('presents',[])):
            raise ProtocolError(8197,'Gift receipt conflicts with inbox')
        retry=req.get('retry',0)
        owned={u['instance_id']:{k:v for k,v in u.items() if k!='leader'} for u in state['units']}
        if (type(retry) is int and retry>0
                and all(owned.get(u['instance_id'])==u for u in receipt['units'])):
            units=copy.deepcopy(receipt['units'])
    else:
        owned={g['serial_number']:g for g in state.get('presents',[])}
        if not set(ids)<=owned.keys():raise ProtocolError(8198,'Gift is not in this inbox')
        gifts=[owned[n] for n in ids]
        masters={m['id']:m for m in self.masters[10]['data_list']}
        delta={'game_money':0,'friend_point':0,'free_paid_point':0}
        books=[]
        for g in gifts:
            kind,param,level=g['present_type'],g['present_param_0'],g['present_param_1']
            if expired(g):raise ProtocolError(8197,'Gift expired')
            if type(param) is not int or param<=0:raise ProtocolError(8197,'Invalid gift amount')
            if kind in (1,2,3):
                delta[{1:'game_money',2:'friend_point',3:'free_paid_point'}[kind]]+=param
            elif kind==4:
                m=masters.get(param)
                if m is None or type(level) is not int or not 1<=level<=m['lv_max']:
                    raise ProtocolError(8197,'Invalid gift unit or level')
                snapshot=state.get('gift_unit_snapshots',{}).get(str(g['serial_number']))
                if snapshot and (snapshot['unit_id']!=param or snapshot['level']!=level):
                    raise ProtocolError(8197,'Friend gift snapshot does not match inbox')
                books.append((param,level,level_exp(m,level),snapshot))
            else:raise ProtocolError(8197,'Unsupported gift kind')
        if ((delta['game_money'] and player['game_money']+delta['game_money']>9999999)
                or (delta['friend_point'] and player['friend_point']+delta['friend_point']>10000)
                or (delta['free_paid_point'] and player['total_paid_point']+delta['free_paid_point']>999)
                or (books and len(state['units'])+len(books)>player['max_unit'])):
            raise ProtocolError(9472,'Gift exceeds currency or unit capacity')
        state['present_serial_high_water']=max(state.get('present_serial_high_water',0),max(owned))
        for k,value in delta.items():player[k]+=value
        player['total_paid_point']+=delta['free_paid_point']
        instances=allocate_instance_ids(state,len(books)) if books else []
        for instance,(unit_id,level,exp,snapshot) in zip(instances,books):
            unit=dict(instance_id=instance,user_id=player['user_id'],unit_id=unit_id,
                      member_id=0,leader=0,level=level,exp=exp,attribute_exp=0,
                      bonus_life=0,bonus_attack=0,bonus_heal=0,bonus_limit=0,favorite=0)
            if snapshot:unit.update(snapshot)
            state['units'].append(unit);units.append({k:v for k,v in unit.items() if k!='leader'})
        state['presents']=[g for g in state['presents'] if g['serial_number'] not in ids]
        for serial in ids:state.get('gift_unit_snapshots',{}).pop(str(serial),None)
        state.setdefault('present_claim_receipts',{})[fingerprint]=dict(units=copy.deepcopy(units))
        self.store.save(state)
    return dict(code=4096,session_id=token,result=dict(serial_number_list=ids,
                user={k:player[k] for k in USER_FIELDS},get_units=units))
