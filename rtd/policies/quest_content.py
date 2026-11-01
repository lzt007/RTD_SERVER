"""Implemented protocol content is distinct from verified/approved client visuals."""
from ..common import ProtocolError
import datetime as dt

STORY_BATCH_QUESTS={11010,11011,11012,11020,11021,11022,
                    11030,11031,11032,11040,11041,11042}
AREA_150_QUESTS={11050,11051,11052,11053}
STORY_160_200_QUESTS={11100,11101,11102,11103,11110,11111,11112,11113,
                      11120,11121,11122,11123,11130,11131,11132,11133,
                      11140,11141,11142,11143}
ORDINARY_QUESTS={11000,11001,11002}|STORY_BATCH_QUESTS|AREA_150_QUESTS|STORY_160_200_QUESTS
EVENT_POINT_QUESTS={13206,13207,13208}
SINGLE_QUESTS={10001}|ORDINARY_QUESTS|EVENT_POINT_QUESTS
LAYER_ROOTS={20000}
VERIFIED_LAYER_QUESTS={20000,20100,20103,20110,20120,20122,20131}
VERIFIED_QUESTS={10001}|ORDINARY_QUESTS|VERIFIED_LAYER_QUESTS


def layer_quests(api):
    return LAYER_ROOTS|{id for id in api.levels if 20100<=id<=20163}


def available(api,quest_id):
    return quest_id not in getattr(api, 'blocked_quests', set())


def require_unlocked(api,state,quest,*,local_schedule=False):
    from .event_points import require_points
    require_points(state,quest,{r['sp_event_id'] for r in api.masters[34]['data_list']})
    quests={q['id']:q for q in api.masters[30]['data_list']}
    for i in range(1,7):
        kind=quest[f'open_type_{i}'];value=quest[f'open_param_{i}']
        if kind==0:continue
        if local_schedule and kind in (1,4,5,6):continue
        if kind==6 and value==0:continue
        if kind==1:
            # Original client: Sunday=0 ... Saturday=6, 7 is every day.
            day=(dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).weekday()+1)%7
            if value not in (day,7):raise ProtocolError(8197,'Quest is not open on this weekday')
            continue
        if kind in (4,5):
            # Legacy YYYYMMDDHH windows are expressed in the game's Japan clock.
            raw=str(value)
            try:boundary=dt.datetime.strptime(raw,'%Y%m%d%H').replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
            except ValueError:raise ProtocolError(8197,'Invalid quest time boundary') from None
            now=dt.datetime.now(boundary.tzinfo)
            if (kind==4 and now<boundary) or (kind==5 and now>boundary):
                raise ProtocolError(8197,'Quest is outside its original time window')
            continue
        if kind==2:
            if not value:continue
            prerequisite=quests.get(value)
            if prerequisite is None:raise ProtocolError(8197,'Missing prerequisite master')
            flag=prerequisite['flag_no']
            if not state['player']['quest_clear_flags'][flag//8]&(1<<(flag%8)):
                raise ProtocolError(9472,'Required quest is not complete')
        else:raise ProtocolError(8197,'Quest open condition is not implemented')
