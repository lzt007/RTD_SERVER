"""Explicit local policy: one successful use per directed pair/UTC entry day."""
import datetime as dt
import time

from ..common import ProtocolError

CAP=10000
BASE=10


def today():return dt.datetime.fromtimestamp(time.time(),dt.timezone.utc).date().isoformat()


def claimed(state,helper_id,day=None):
    last=state.get('helper_reward_days',{}).get(str(helper_id))
    # Monotonic day receipts also prevent earning again after clock rollback.
    return last is not None and last >= (day or today())


def freeze(state,helper,bonus):
    uid=helper['user_id'];day=today()
    if not uid:return None
    extra=bonus.get('num',0) if bonus.get('type')==10 else 0
    if type(extra) is not int or extra<0:raise ProtocolError(8197,'Invalid helper login bonus')
    return dict(helper_id=uid,day=day,points=BASE,bonus=extra,eligible=not claimed(state,uid,day))


def balance(player):
    value=player['friend_point']
    if type(value) is not int or value<0:raise ProtocolError(8197,'Invalid helper friendship balance')
    return value


def pending(state):
    value=state.get('helper_reward_pending',dict(count=0,points=0))
    if (not isinstance(value,dict) or set(value)!={'count','points'}
            or any(type(n) is not int or n<0 for n in value.values())):
        raise ProtocolError(8197,'Invalid pending helper rewards')
    return value


def credit(api,state):
    reward=state.get('battle_helper_reward')
    if not reward or not reward['eligible'] or reward.get('applied'):return
    uid=reward['helper_id']
    if claimed(state,uid,reward['day']):return
    if uid==state['player']['user_id'] or uid!=state.get('battle_helper',{}).get('user_id'):
        raise ProtocolError(8197,'Helper reward snapshot differs from accepted order')
    peer=api.store.by_id(uid)
    if peer is None:raise ProtocolError(8197,'Accepted helper account is unavailable')
    waiting=pending(peer)
    current=balance(state['player'])
    state['player']['friend_point']+=min(reward['points']+reward['bonus'],max(0,CAP-current))
    state.setdefault('helper_reward_days',{})[str(uid)]=reward['day']
    reward['applied']=True
    peer['helper_reward_pending']=dict(count=waiting['count']+1,points=min(CAP,waiting['points']+BASE))
    api.store.save(peer)


def claim(api,state):
    if 'helper_reward_pending' not in state:return 0,0
    waiting=pending(state);current=balance(state['player'])
    granted=min(waiting['points'],max(0,CAP-current))
    state['player']['friend_point']+=granted
    state.pop('helper_reward_pending')
    api.store.save(state)
    return waiting['count'],granted
