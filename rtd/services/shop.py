"""Three original menus with explicit local cost, limits and replay policy."""
import time
from ..common import ProtocolError
from .presents import USER_FIELDS

CAPACITY={'buy_max_unit':('max_unit',1000),'buy_max_friend':('max_friend',100)}


def number(value,positive=False):
    if type(value) is str:
        if (not value.isascii() or not value.isdecimal() or len(value)>10
                or str(int(value))!=value):raise ProtocolError(8194,'Expected canonical integer')
        value=int(value)
    if type(value) is not int or value<(1 if positive else 0) or value>2147483647:
        raise ProtocolError(8194,'Invalid integer')
    return value


def purchase(api,state,req,token,operation):
    retry=number(req.get('retry',0))
    old=number(req.get(CAPACITY[operation][0]),True) if operation in CAPACITY else None
    # Stamina and capacity belong to the account, not the frozen battle.
    # A retained run can remain after the original client returns to menus.
    player=state['player'];receipts=state.get('shop_receipts',{})
    funds=[player[k] for k in ('free_paid_point','paid_point','total_paid_point')]
    if any(type(n) is not int or n<0 for n in funds) or funds[0]+funds[1]!=funds[2]:
        raise ProtocolError(8197,'Invalid local currency balance')
    def response():
        return dict(code=4096,session_id=token,result={k:player[k] for k in USER_FIELDS})
    if operation in CAPACITY:
        field,maximum=CAPACITY[operation]
        if str(old) in receipts.get(operation,{}):return response()
        if old!=player[field]:raise ProtocolError(8197,'Capacity no longer matches request')
    elif retry:
        if not receipts.get(operation):raise ProtocolError(8197,'No AP purchase receipt')
        return response()
    if player['total_paid_point']<1:raise ProtocolError(8961,'Not enough local crystals')
    if operation in CAPACITY:
        if player[field]+5>maximum:raise ProtocolError(9217,'Local capacity limit')
        player[field]+=5
        state.setdefault('shop_receipts',{}).setdefault(operation,{})[str(old)]=True
    else:
        if player['action_point']>=player['max_action_point']:
            raise ProtocolError(9216,'Stamina is already full')
        player['action_point']=player['max_action_point']
        player['action_point_recover']=int(time.time())
        state.setdefault('shop_receipts',{})[operation]=True
    player['free_paid_point' if player['free_paid_point'] else 'paid_point']-=1
    player['total_paid_point']-=1
    api.store.save(state)
    return response()
