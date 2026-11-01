"""Local account profiles and the original three friend relationship states."""
import datetime as dt
from ..common import ProtocolError
from .shop import number


def stamp(value=None):
    return dt.datetime.fromtimestamp(value if value is not None else dt.datetime.now().timestamp(),
                                    dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def leader(state):
    party=state['party'];instance=party['party'][party['active']]['instanceIds'][0]
    unit=next((u for u in state['units'] if u['instance_id']==instance),None)
    if unit is None:raise ProtocolError(8197,'Local peer has no active leader')
    return unit


def profile(state):
    p=state['player'];u=leader(state);created=stamp(state.get('created_at',0))
    last=state.get('last_login')
    last=last+'T00:00:00Z' if isinstance(last,str) and len(last)==10 else created
    return dict(user_id=p['user_id'],user_name=p['user_name'],rank=p['rank'],
                unit_id=u['unit_id'],unit_level=u['level'],unit_bonus_life=u['bonus_life'],
                unit_bonus_attack=u['bonus_attack'],unit_bonus_heal=u['bonus_heal'],
                last_play_date=last,create_date=created)


def count(state):return sum(r['status']==0 for r in state.get('friend_links',{}).values())


def capacity(state,code):
    if count(state)>=state['player']['max_friend']:raise ProtocolError(code,'Local friend capacity reached')


def target(api,state,user_id):
    if user_id==state['player']['user_id']:raise ProtocolError(8194,'Cannot target this account itself')
    other=api.store.by_id(user_id)
    if other is None:raise ProtocolError(8200,'No local account')
    return other


def ids(req):
    values=req.get('friend_user_id')
    if not isinstance(values,list) or not 1<=len(values)<=100:raise ProtocolError(8194,'Expected friend ID list')
    values=[number(n,True) for n in values]
    if len(set(values))!=len(values):raise ProtocolError(8194,'Duplicate friend IDs')
    return values


def get_friends(api,state,req,token,operation):
    rows=[]
    for key,relation in sorted(state.get('friend_links',{}).items(),key=lambda r:int(r[0])):
        peer=api.store.by_id(int(key))
        if peer is None:continue
        row=profile(peer);row.pop('create_date')
        row.update(friend_status=relation['status'],invite_flag=0,
                   update_date=relation['date'],invalid_user_flag=0)
        rows.append(row)
    return dict(code=4096,session_id=token,result=rows)


def search(api,state,req,token,operation):
    peer=api.store.by_id(number(req.get('user_id'),True))
    return dict(code=4096,session_id=token,result=profile(peer) if peer else None)


def relation(api,state,req,token,operation):
    mine=state['player']['user_id'];links=state.setdefault('friend_links',{});accepted=0
    if operation=='send_friend_request' and number(req.get('friend_user_id'))==0:
        raise ProtocolError(8706,'Local companion cannot receive friend requests')
    targets=[number(req.get('friend_user_id'),True)] if operation=='send_friend_request' else ids(req)
    for uid in targets:
        key=str(uid);other=target(api,state,uid);their=other.setdefault('friend_links',{});my_key=str(mine)
        left=links.get(key);right=their.get(my_key)
        if operation=='send_friend_request':
            if left and right and (left['status'],right['status'])==(1,2):continue
            if left or right:raise ProtocolError(8706,'Local friend relationship already exists')
            capacity(state,8704);capacity(other,8704)
            if len(links)>=100 or len(their)>=100:raise ProtocolError(8704,'Local friend queue is full')
            date=stamp();links[key]=dict(status=1,date=date);their[my_key]=dict(status=2,date=date)
        elif operation=='accept_friend_request':
            if left and right and left['status']==right['status']==0:continue
            if not left or not right or (left['status'],right['status'])!=(2,1):
                raise ProtocolError(8198,'No incoming local friend request')
            capacity(state,8704);capacity(other,8705)
            date=stamp();links[key]=dict(status=0,date=date);their[my_key]=dict(status=0,date=date);accepted+=1
        else:
            links.pop(key,None);their.pop(my_key,None)
        api.store.save(other)
    api.store.save(state)
    return dict(code=4096,session_id=token,result=dict(count=accepted) if operation=='accept_friend_request' else [])


def helper_profile(api,state,uid):
    peer=api.store.by_id(uid)
    if uid==state['player']['user_id'] or peer is None:
        raise ProtocolError(9472,'Helper account is unavailable')
    row=profile(peer);row.pop('create_date')
    from ..policies.helper_rewards import claimed
    row.update(friend=state.get('friend_links',{}).get(str(uid),{}).get('status')==0,
               friend_point=claimed(state,uid))
    return row
