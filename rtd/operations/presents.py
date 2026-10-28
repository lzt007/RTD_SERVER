"""Local operator delivery into the original inbox, with durable retry identity."""
import copy
import hashlib
import json
import re

from .configuration import ConfigurationError
from ..common import compact
from ..services.presents import PRESENT_FIELDS, expired, issue


class Delivery:
    def __init__(self,store,masters):
        self.store=store
        self.units={row['id']:row for row in masters[10]['data_list']}

    @staticmethod
    def player_id(key):
        if not isinstance(key,str) or not re.fullmatch(r'[1-9][0-9]{0,9}',key,re.ASCII) or int(key)>2147483647:
            raise ConfigurationError('Player not found',404)
        return int(key)

    @staticmethod
    def load(db,uid):
        row=db.execute('SELECT state FROM players WHERE id=?',(uid,)).fetchone()
        if row is None:raise ConfigurationError('Player not found',404)
        return json.loads(row[0])

    @staticmethod
    def inbox(state):
        return [{key:gift[key] for key in PRESENT_FIELDS}
                for gift in state.get('presents',[]) if not expired(gift)]

    def players(self):
        with self.store.connect() as db:
            states=[json.loads(row[0]) for row in db.execute('SELECT state FROM players ORDER BY id')]
        return [dict(user_id=s['player']['user_id'],user_name=s['player']['user_name'],
                     rank=s['player']['rank'],pending_present_count=len(self.inbox(s))) for s in states]

    def read(self,key):
        uid=self.player_id(key)
        with self.store.connect() as db:return self.inbox(self.load(db,uid))

    def validate(self,body):
        fields={'request_id','message','present_type','present_param_0','present_param_1'}
        if not isinstance(body,dict) or set(body)!=fields:
            raise ConfigurationError('Expected exactly the five delivery fields')
        request=body['request_id'];message=body['message']
        if not isinstance(request,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}',request,re.ASCII):
            raise ConfigurationError('Invalid request_id')
        if (not isinstance(message,str) or not 1<=len(message)<=120
                or any(ord(ch)<32 and ch!='\n' for ch in message)
                or any(0xD800<=ord(ch)<=0xDFFF for ch in message)):
            raise ConfigurationError('Invalid message')
        kind,param,level=(body[k] for k in ('present_type','present_param_0','present_param_1'))
        if any(type(n) is not int for n in (kind,param,level)):
            raise ConfigurationError('Gift kind, amount and level must be integers')
        if kind in (1,2,3):
            if not 1<=param<={1:9999999,2:10000,3:999}[kind] or level!=0:
                raise ConfigurationError('Invalid currency amount or parameter')
        elif kind==4:
            master=self.units.get(param)
            if master is None or not 1<=level<=master['lv_max']:
                raise ConfigurationError('Invalid original unit or level')
        else:raise ConfigurationError('Only ordinary gift kinds 1 through 4 are supported')

    def send(self,key,body):
        uid=self.player_id(key)
        with self.store.transaction() as db:
            state=self.load(db,uid)
            self.validate(body)
            fingerprint=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()
            receipts=state.get('admin_present_receipts',{})
            previous=receipts.get(body['request_id'])
            if previous is not None:
                if previous['fingerprint']!=fingerprint:
                    raise ConfigurationError('request_id already used with different delivery content',409)
                gift=copy.deepcopy(previous['present']);replayed=True
            else:
                gift=issue(state,body['present_type'],body['present_param_0'],body['present_param_1'],body['message'])
                state.setdefault('admin_present_receipts',{})[body['request_id']]=dict(fingerprint=fingerprint,present=copy.deepcopy(gift))
                self.store.save(state);replayed=False
            return dict(data=dict(user_id=uid,request_id=body['request_id'],present=gift),replayed=replayed)
