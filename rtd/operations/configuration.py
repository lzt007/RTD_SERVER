import copy
import datetime as dt
import re
import time
from ..common import compact
from ..config import path_for
from ..policies.quest_content import EVENT_POINT_QUESTS
import json
import zlib

GACHA_IDS=(10000,20000,30000)
EVENT_QUESTS={11000}


class ConfigurationError(ValueError):
    def __init__(self,message,status=422):
        super().__init__(message);self.status=status


def timestamp(value):
    if not isinstance(value,str):raise ConfigurationError('Time must be an ISO8601 string with timezone or null')
    try:
        value=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError()
        return value.astimezone(dt.timezone.utc)
    except (ValueError,OverflowError):raise ConfigurationError('Time must include a valid timezone within UTC date range') from None


def is_open(item,now=None):
    now=time.time() if now is None else now
    return (item['enabled'] and (item['starts_at'] is None or now>=timestamp(item['starts_at']).timestamp())
            and (item['ends_at'] is None or now<timestamp(item['ends_at']).timestamp()))


def exact(item,keys):
    if not isinstance(item,dict) or set(item)!=set(keys):raise ConfigurationError('Unexpected or missing configuration fields')


def integer(value,minimum,maximum):
    if type(value) is not int or not minimum<=value<=maximum:raise ConfigurationError('Integer outside allowed range')


class Operations:
    def __init__(self,store,masters,pools,*,event_quests=None,configurable_quests=None,playable_quests=None):
        self.store=store;self.masters=masters
        self.units={u['id']:u for u in masters[10]['data_list']}
        self.quests={q['id']:q for q in masters[30]['data_list']}
        self.event_quests=set(EVENT_QUESTS if event_quests is None else event_quests)
        self.configurable_quests=set(self.event_quests if configurable_quests is None else configurable_quests)
        self.playable_quests=set((10000,10001,11000) if playable_quests is None else playable_quests)
        with store.transaction():
            with store.connect() as db:
                if db.execute('SELECT 1 FROM runtime_config WHERE id=1').fetchone():return
                pools=pools()
                names=('普通单抽','稀有单抽','普通十连')
                default=dict(revision=1,gachas=[dict(id=id,name=name,enabled=True,starts_at=None,ends_at=None,
                    entries=copy.deepcopy(pools['rare' if id==20000 else 'normal'])) for id,name in zip(GACHA_IDS,names)],events=[])
                db.execute('INSERT INTO runtime_config VALUES(1,?)',(compact(default),))

    def read(self):
        with self.store.connect() as db:
            return json.loads(db.execute('SELECT document FROM runtime_config WHERE id=1').fetchone()[0])

    def _save(self,document):
        with self.store.connect() as db:db.execute('UPDATE runtime_config SET document=? WHERE id=1',(compact(document),))

    def schedule(self,item):
        if (not isinstance(item['name'],str) or not item['name'].strip() or len(item['name'])>80
                or type(item['enabled']) is not bool):raise ConfigurationError('Invalid name or enabled flag')
        for key in ('starts_at','ends_at'):
            if item[key] is not None:item[key]=timestamp(item[key]).isoformat()
        if item['starts_at'] and item['ends_at'] and timestamp(item['starts_at'])>=timestamp(item['ends_at']):
            raise ConfigurationError('ends_at must be later than starts_at')

    def entries(self,rows,drop=False,allow_empty=False):
        if not isinstance(rows,list) or not (0 if allow_empty else 1)<=len(rows)<=256:
            raise ConfigurationError('Expected up to 256 weighted entries')
        seen=set()
        for row in rows:
            exact(row,('unit_id','level_min','level_max','weight') if drop else ('unit_id','level','weight'))
            integer(row['unit_id'],1,2147483647);integer(row['weight'],1,1000000)
            unit=self.units.get(row['unit_id'])
            if unit is None or row['unit_id'] in seen:raise ConfigurationError('Unknown or duplicated unit_id')
            seen.add(row['unit_id'])
            if drop:
                integer(row['level_min'],1,unit['lv_max']);integer(row['level_max'],row['level_min'],unit['lv_max'])
            else:integer(row['level'],1,unit['lv_max'])

    def drop_ids(self,quest_id):
        quest=self.quests[quest_id]
        table=next(t for t in self.masters[21]['data_list'] if t['id']==quest['enemy_table_id'])
        types={e['id']:e['type'] for e in self.masters[20]['data_list']}
        return {v for k,v in table.items() if k.endswith('_drop_id') and types.get(table[k.replace('_drop_id','_set_id')]) not in (20,21)}

    def next_quests(self,quest_id):
        table=next(t for t in self.masters[21]['data_list'] if t['id']==self.quests[quest_id]['enemy_table_id'])
        types={e['id']:e['type'] for e in self.masters[20]['data_list']}
        return {table[k.replace('_set_id','_drop_id')] for k,id in table.items() if k.endswith('_set_id') and types.get(id)==20}

    def quest_table(self):
        source=self.masters[30];table=None
        for event in self.read()['events']:
            for quest in event['quests']:
                if quest['quest_id'] not in {20000}|EVENT_POINT_QUESTS:continue
                if table is None:table=copy.deepcopy(source)
                row=next(q for q in table['data_list'] if q['id']==quest['quest_id'])
                for i in range(1,7):
                    if row[f'open_type_{i}'] in (1,4,5,6):row[f'open_type_{i}']=row[f'open_param_{i}']=0
                row.update(open_type_6=6,open_param_6=0 if quest['quest_id'] in self.event_quests and is_open(event) else 1)
        if table is None:return source
        table['hash']=str(zlib.crc32(compact(table['data_list']).encode()))
        return table

    def validate(self,cfg):
        exact(cfg,('revision','gachas','events'))
        if not isinstance(cfg['gachas'],list) or len(cfg['gachas'])!=3:raise ConfigurationError('All three fixed gacha IDs are required')
        ids=[]
        for pool in cfg['gachas']:
            exact(pool,('id','name','enabled','starts_at','ends_at','entries'))
            integer(pool['id'],1,2147483647);ids.append(pool['id']);self.schedule(pool);self.entries(pool['entries'])
        if sorted(ids)!=list(GACHA_IDS):raise ConfigurationError('Expected fixed gacha IDs 10000, 20000, 30000')
        cfg['gachas'].sort(key=lambda p:p['id'])
        if not isinstance(cfg['events'],list) or len(cfg['events'])>100:raise ConfigurationError('Expected up to 100 events')
        seen=set();managed=set()
        for event in cfg['events']:
            exact(event,('id','name','enabled','starts_at','ends_at','quests'))
            if (not isinstance(event['id'],str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',event['id'])
                    or event['id'] in seen):raise ConfigurationError('Invalid or duplicated event ID')
            seen.add(event['id']);self.schedule(event)
            if not isinstance(event['quests'],list) or not event['quests']:raise ConfigurationError('Event needs at least one supported quest')
            for quest in event['quests']:
                exact(quest,('quest_id','drops'))
                integer(quest['quest_id'],1,2147483647)
                if quest['quest_id'] not in self.configurable_quests:raise ConfigurationError('Quest protocol is not configurable')
                if event['enabled'] and quest['quest_id'] not in self.event_quests:
                    raise ConfigurationError('Unverified quest cannot open outside experimental mode')
                if quest['quest_id'] in managed:raise ConfigurationError('A quest may belong to only one event')
                managed.add(quest['quest_id']);allowed=self.drop_ids(quest['quest_id']);drop_ids=set()
                if not isinstance(quest['drops'],list):raise ConfigurationError('Expected drop override list')
                for rule in quest['drops']:
                    optional=tuple(k for k in ('attribute_exp','sp_event_point') if isinstance(rule,dict) and k in rule)
                    exact(rule,('drop_data_id','no_drop_weight','entries')+optional)
                    if 'attribute_exp' in rule:integer(rule['attribute_exp'],0,999999)
                    if 'sp_event_point' in rule:
                        integer(rule['sp_event_point'],0,999)
                        original=self.quests[quest['quest_id']]['sp_event_id']
                        if rule['sp_event_point'] and original not in {r['sp_event_id'] for r in self.masters[34]['data_list']}:
                            raise ConfigurationError('Nonzero points require an original registered event')
                    integer(rule['drop_data_id'],0,2147483647);integer(rule['no_drop_weight'],0,1000000)
                    if rule['drop_data_id'] not in allowed or rule['drop_data_id'] in drop_ids:
                        raise ConfigurationError('Unknown or duplicated drop_data_id for quest')
                    drop_ids.add(rule['drop_data_id']);self.entries(rule['entries'],drop=True,allow_empty=True)
                    if not rule['entries'] and not rule['no_drop_weight']:raise ConfigurationError('Drop rule must have a positive total weight')
                if event['enabled']:
                    known={d['id'] for d in self.masters[22]['data_list']}
                    if allowed-known-drop_ids:raise ConfigurationError('Explicit local rules required for missing original drop masters')
            if event['enabled']:
                covered={q['quest_id'] for q in event['quests']}
                pending=list(covered);visited=set()
                while pending:
                    id=pending.pop()
                    if id in visited:continue
                    visited.add(id);children=self.next_quests(id)
                    if not children<=covered:raise ConfigurationError('Event must configure all reachable staircase destinations')
                    pending.extend(children-visited)
        return cfg

    def update(self,resource,key,body,method='PUT'):
        with self.store.transaction():
            cfg=self.read();body=copy.deepcopy(body)
            if method!='DELETE':
                if not isinstance(body,dict):raise ConfigurationError('Expected a JSON object')
                if 'expected_revision' in body:
                    expected=body.pop('expected_revision');integer(expected,1,2147483647)
                    if expected!=cfg['revision']:raise ConfigurationError('Configuration revision changed',409)
            if resource=='config' and method=='PUT':
                exact(body,('gachas','events'));cfg.update(body)
            elif resource in ('gachas','events'):
                rows=cfg[resource];index=next((i for i,row in enumerate(rows) if str(row['id'])==key),None)
                if method=='DELETE':
                    if resource!='events':raise ConfigurationError('Fixed gacha pools cannot be deleted',405)
                    if index is None:raise ConfigurationError('Event not found',404)
                    rows.pop(index)
                elif method in ('PUT','PATCH'):
                    if resource=='gachas' and key not in tuple(map(str,GACHA_IDS)):raise ConfigurationError('Gacha pool not found',404)
                    if 'id' in body and str(body['id'])!=key:raise ConfigurationError('Resource ID does not match URL')
                    if method=='PATCH':
                        if index is None:raise ConfigurationError('Resource not found',404)
                        row=copy.deepcopy(rows[index]);row.update(body)
                    else:row=body;row.setdefault('id',int(key) if resource=='gachas' else key)
                    if index is None:rows.append(row)
                    else:rows[index]=row
                else:raise ConfigurationError('Unsupported method',405)
            else:raise ConfigurationError('Management resource not found',404)
            cfg['revision']+=1;self.validate(cfg);self._save(cfg)
            return cfg

    def gacha(self,id):
        cfg=self.read();return next(p for p in cfg['gachas'] if p['id']==id),cfg['revision']

    def availability(self,cfg):
        now=time.time()
        return dict(gachas=[dict(id=p['id'],effective_open=is_open(p,now),
            currency='crystals' if p['id']==20000 else 'friend_point',
            cost=5 if p['id']==20000 else 1000 if p['id']==30000 else 100,
            draw_count=10 if p['id']==30000 else 1) for p in cfg['gachas']],
            events=[dict(id=e['id'],effective_open=is_open(e,now)) for e in cfg['events']])

    def event_for_quest(self,id):
        cfg=self.read()
        for event in cfg['events']:
            for quest in event['quests']:
                if quest['quest_id']==id:return event,quest,cfg['revision']
        return None

    def catalog(self):
        drop_masters={d['id']:d for d in self.masters[22]['data_list']};drops={}
        for id in sorted(self.configurable_quests):
            rules=[]
            for drop_id in sorted(self.drop_ids(id)):
                if drop_id not in drop_masters:
                    rules.append(dict(drop_data_id=drop_id,entries=[],no_drop_weight=1,original_missing=True));continue
                drop=drop_masters[drop_id];entries=[]
                for i in range(1,5):
                    if drop[f'unit{i}_id'] and drop[f'unit{i}_rate']:
                        entries.append(dict(unit_id=drop[f'unit{i}_id'],level_min=drop[f'unit{i}_lv_min'],
                                            level_max=drop[f'unit{i}_lv_max'],weight=drop[f'unit{i}_rate']))
                rules.append(dict(drop_data_id=drop_id,entries=entries,no_drop_weight=100-sum(r['weight'] for r in entries)))
            drops[str(id)]=rules
        point_events={r['sp_event_id'] for r in self.masters[34]['data_list']}
        return dict(units=[dict(unit_id=u['id'],name=u.get('name',''),max_level=u['lv_max'],
                        icon_url=f"/admin/assets/unit-icons/{u['g_id']}.png" if (path_for('unit_icons')/f"{u['g_id']}.png").is_file() else None) for u in self.units.values()],
                    quests=[dict(quest_id=q['id'],name=q['name'],division=q['division'],category=q['category'],
                        playable=q['id'] in self.playable_quests,event_configurable=q['id'] in self.configurable_quests,
                        event_openable=q['id'] in self.event_quests,
                        next_quest_ids=sorted(self.next_quests(q['id'])) if q['id'] in self.configurable_quests else [],
                        sp_event_id=q['sp_event_id'],event_point_configurable=q['sp_event_id'] in point_events,
                        reason='' if q['id'] in self.event_quests else 'Tutorial is not event-configurable' if q['id'] in (10000,10001) else 'Gameplay/resources not yet verified; opening requires experimental mode') for q in self.quests.values()],
                    event_quest_drops=drops)
