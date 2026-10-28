"""Original draw DTOs with configured local pools and bounded network replay."""
import copy
import hashlib
from ..common import compact
from ..operations.configuration import is_open
from ..common import ProtocolError
from ..policies.gacha_pools import draw
from ..policies.instance_ids import allocate_instance_ids
from ..policies.unit_progression import level_exp
from .presents import USER_FIELDS
from .shop import number
from . import rewards


def tutorial_flag(value):
    if type(value) is bool:return value
    if value in ('True','true'):return True
    if value in ('False','false'):return False
    raise ProtocolError(8194,'Invalid tutorial flag')


def response(state,token,operation,units):
    result={k:state['player'][k] for k in USER_FIELDS}
    if operation=='buy_gacha':result['unit']=copy.deepcopy(units[0])
    else:
        result['gacha_units']=[dict(gacha_unit=[dict(kind=0,**{k:u[k] for k in
            ('instance_id','user_id','unit_id','member_id','level','exp')}) for u in units])]
    return dict(code=4096,session_id=token,result=result)


def purchase(api,state,req,token,operation):
    gacha_id=number(req.get('gacha_id'),True);retry=number(req.get('retry',0))
    tutorial=tutorial_flag(req.get('tutorial_flag',False))
    if tutorial:
        if operation!='buy_gacha' or gacha_id!=20000:
            raise ProtocolError(8194,'Invalid tutorial draw')
        return rewards.buy_gacha(api,state,req,token,operation)
    if gacha_id not in (10000,20000,30000):raise ProtocolError(8197,'Local pool is not configured')
    if (operation=='buy_gacha_special')!=(gacha_id==30000):
        raise ProtocolError(8194,'Draw type does not match operation')
    if state.get('battle'):raise ProtocolError(8197,'Draw is unavailable during an active battle')
    balance=number(req.get('paid_point')) if gacha_id==20000 else None
    receipts=state.get('gacha_receipts',{});key=str(gacha_id)
    if retry:
        receipt=receipts.get(key)
        if not receipt or receipt['request_balance']!=balance:
            raise ProtocolError(8197,'No matching local draw receipt')
        owned={u['instance_id']:{k:v for k,v in u.items() if k!='leader'} for u in state['units']}
        if any(owned.get(u['instance_id'])!=u for u in receipt['units']):
            raise ProtocolError(8197,'Previous draw units have changed; refresh inventory')
        return response(state,token,operation,receipt['units'])
    pool,revision=api.operations.gacha(gacha_id)
    if not is_open(pool):raise ProtocolError(8197,'Local pool is closed')
    player=state['player']
    funds=[player[k] for k in ('free_paid_point','paid_point','total_paid_point','friend_point')]
    if (any(type(n) is not int or n<0 for n in funds) or funds[0]+funds[1]!=funds[2]
            or funds[3]>10000):raise ProtocolError(8197,'Invalid local draw currency')
    if gacha_id==20000 and balance!=player['total_paid_point']:
        raise ProtocolError(8197,'Crystal balance no longer matches request')
    count=10 if gacha_id==30000 else 1
    if len(state['units'])+count>player['max_unit']:
        raise ProtocolError(9472,'Not enough unit capacity for this draw')
    cost=5 if gacha_id==20000 else 100*count
    field='total_paid_point' if gacha_id==20000 else 'friend_point'
    if player[field]<cost:raise ProtocolError(8961,'Not enough local draw currency')
    selected=draw(pool['entries'],count)
    if gacha_id==20000:
        free=min(cost,player['free_paid_point']);player['free_paid_point']-=free
        player['paid_point']-=cost-free
    player[field]-=cost
    masters={u['id']:u for u in api.masters[10]['data_list']}
    units=[]
    for instance,row in zip(allocate_instance_ids(state,count),selected):
        unit=dict(instance_id=instance,user_id=player['user_id'],unit_id=row['unit_id'],
            member_id=0,leader=0,level=row['level'],exp=level_exp(masters[row['unit_id']],row['level']),
            attribute_exp=0,bonus_life=0,bonus_attack=0,bonus_heal=0,bonus_limit=0,favorite=0)
        state['units'].append(unit);units.append({k:v for k,v in unit.items() if k!='leader'})
    state.setdefault('gacha_receipts',{})[key]=dict(request_balance=balance,
        pool_digest=hashlib.sha256(compact(pool).encode('utf-8')).hexdigest(),
        configuration_revision=revision,cost=cost,units=copy.deepcopy(units))
    api.store.save(state)
    return response(state,token,operation,units)
