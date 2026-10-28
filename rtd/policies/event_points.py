"""Original event IDs/caps; quantities are explicit local operator configuration."""
import re
from ..common import ProtocolError


def integer(value,minimum,maximum):
    if type(value) is not int or not minimum<=value<=maximum:
        raise ProtocolError(8197,'Invalid event point value')
    return value


def balances(state,registered_ids):
    value=state.get('sp_event_points',{})
    if not isinstance(value,dict):raise ProtocolError(8197,'Invalid stored event points')
    for key,amount in value.items():
        if not isinstance(key,str) or not re.fullmatch(r'[1-9][0-9]{0,9}',key,re.ASCII):
            raise ProtocolError(8197,'Invalid stored event identity')
        integer(int(key),1,2147483647);integer(amount,0,99999)
        if int(key) not in registered_ids:raise ProtocolError(8197,'Unknown stored event identity')
    return value


def login_points(state,registered_ids):
    return [dict(sp_event_id=int(key),point=value) for key,value in sorted(balances(state,registered_ids).items(),key=lambda r:int(r[0]))]


def freeze(quest,enemies,registered_ids):
    event_id=integer(quest.get('sp_event_id',0),0,2147483647)
    if event_id and event_id not in registered_ids:raise ProtocolError(8197,'Unknown original event identity')
    total=0
    for enemy in enemies:
        value=integer(enemy.get('sp_event_point',0),0,999)
        if enemy.get('flag') is True:total+=value
    if not event_id and total:raise ProtocolError(8197,'Points require an original event identity')
    return dict(event_id=event_id,maximum=min(999,total))


def apply(state,reported,snapshot,registered_ids):
    stored=balances(state,registered_ids)
    if snapshot is None:snapshot=dict(event_id=0,maximum=0)
    if not isinstance(snapshot,dict) or set(snapshot)!={'event_id','maximum'}:
        raise ProtocolError(8197,'Invalid frozen event points')
    event_id=integer(snapshot['event_id'],0,2147483647)
    if event_id and event_id not in registered_ids:raise ProtocolError(8197,'Unknown frozen event identity')
    maximum=integer(snapshot['maximum'],0,999)
    if not event_id and maximum:raise ProtocolError(8197,'Invalid frozen event identity')
    integer(reported,0,maximum)
    if reported:
        updated=dict(stored);key=str(event_id)
        updated[key]=min(99999,updated.get(key,0)+reported)
        state['sp_event_points']=updated


def require_points(state,quest,registered_ids):
    stored=balances(state,registered_ids)
    event_id=quest.get('open_sp_event_id',0);required=quest.get('open_sp_event_point',0)
    if event_id:
        integer(event_id,1,2147483647)
        if event_id not in registered_ids:raise ProtocolError(8197,'Unknown threshold event identity')
    if not event_id or not required:return
    integer(event_id,1,2147483647);integer(required,1,99999)
    if stored.get(str(event_id),0)<required:
        raise ProtocolError(9472,'Original event point requirement is not met')
