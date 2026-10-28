"""UTC attendance and original calendar rows; streak cap is local policy."""
import copy
import datetime as dt
from ..common import ProtocolError


def utc_today():
    return dt.datetime.now(dt.timezone.utc).date()


def daily(api,state):
    # Imported here to keep gift acquisition and attendance independent.
    from ..services.presents import issue
    player=state['player'];today=utc_today()
    previous=dt.date.fromisoformat(state['last_login']) if state.get('last_login') else None
    snapshot=state.get('login_reward_snapshot')
    if previous and today<=previous and snapshot:
        return copy.deepcopy(snapshot)
    new_day=previous is None or today>previous
    if new_day:
        player['login_days']=(player['login_days']+1 if previous and
            (previous.year,previous.month)==(today.year,today.month) else 1)
        player['sequence_login_days']=(player['sequence_login_days']+1
            if previous==today-dt.timedelta(days=1) else 1)
        state['last_login']=today.isoformat()
    streak=max(1,player['sequence_login_days'])
    rows=[r for r in api.masters[52]['data_list'] if r['id']==min(streak,7)]
    if len(rows)!=1 or rows[0]['type'] not in range(1,11) or rows[0]['num']<0:
        raise ProtocolError(8197,'Consecutive login master is unavailable')
    bonus={k:rows[0][k] for k in ('type','num')}
    if not new_day:
        # Legacy clients may already have cached today's zero bonus. Do not
        # start validating extra rewards they cannot yet compute.
        bonus=dict(type=0,num=0)
    gifts=[r for r in api.masters[51]['data_list'] if
           (dt.date.fromisoformat(r['day']).month,dt.date.fromisoformat(r['day']).day)
           ==(today.month,player['login_days'])] if new_day else []
    if len(gifts)>1:raise ProtocolError(8197,'Ambiguous login calendar')
    for gift in gifts:
        kind,param=gift['present_type'],gift['present_param']
        if kind not in (1,2,3,4) or type(param) is not int or param<=0:
            raise ProtocolError(8197,'Unsupported calendar gift')
        if kind==4 and not any(m['id']==param for m in api.masters[10]['data_list']):
            raise ProtocolError(8197,'Calendar unit is unavailable')
        issue(state,kind,param,1 if kind==4 else 0,'ログインボーナス')
    snapshot=dict(date=state['last_login'],bonus=bonus,calendar=bool(gifts))
    state['login_reward_snapshot']=snapshot
    api.store.save(state)
    return copy.deepcopy(snapshot)


def active_bonus(state):
    """The last login's durable bonus, including battles across midnight."""
    return copy.deepcopy(state.get('login_reward_snapshot',{}).get('bonus',dict(type=0,num=0)))
