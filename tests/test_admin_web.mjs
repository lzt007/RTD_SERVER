import test from 'node:test';
import assert from 'node:assert/strict';
import { integer, localTime, isoTime, toDraft, poolPayload, eventPayload, addQuest, unitPreview } from '../rtd/web/admin-model.mjs';

test('preview follows catalog icon mapping, rejects unknown IDs and external URLs',()=>{
  const c={units:[{unit_id:10000,name:'ラビ',icon_url:'/admin/assets/unit-icons/13.png'},
    {unit_id:2,name:'missing',icon_url:null},{unit_id:3,name:'bad',icon_url:'https://example.org/a.png'}]};
  assert.equal(unitPreview('10000',c).url,'/admin/assets/unit-icons/13.png');
  assert.equal(unitPreview('10000x',c).url,null);
  assert.equal(unitPreview('2',c).url,null);
  assert.equal(unitPreview('3',c).url,null);
  assert.equal(unitPreview('9',c).name,'未找到该单位');
});

const catalog = {
  units: [{unit_id:1,name:'A',max_level:10},{unit_id:2,name:'B',max_level:50}],
  quests: [
    {quest_id:11,name:'First',event_configurable:true,event_openable:true,next_quest_ids:[12],event_point_configurable:false},
    {quest_id:12,name:'Second',event_configurable:true,event_openable:true,next_quest_ids:[11],event_point_configurable:true},
    {quest_id:13,name:'Draft only',event_configurable:true,event_openable:false,next_quest_ids:[],event_point_configurable:false},
    {quest_id:99,name:'Unavailable',event_configurable:false,event_openable:false,next_quest_ids:[]},
  ],
  event_quest_drops: {
    '11': [{drop_data_id:1,entries:[{unit_id:1,level_min:1,level_max:2,weight:1}],no_drop_weight:2}],
    '12': [{drop_data_id:2,entries:[],no_drop_weight:1,original_missing:true}], '13': [],
  },
};
const common = {name:'测试',enabled:true,starts_at:null,ends_at:null};
const pool = () => toDraft({...common,id:10000,entries:[{unit_id:1,level:1,weight:7},{unit_id:2,level:3,weight:3}]});
const event = () => toDraft({...common,id:'local-test',quests:[{quest_id:11,drops:[]},{quest_id:12,drops:[{drop_data_id:2,entries:[],no_drop_weight:1,original_missing:true,attribute_exp:25,sp_event_point:1}]}]});

test('integers reject partial, fractional, empty and unsafe inputs', () => {
  assert.equal(integer('10',1,10,'数量'),10);
  for (const v of ['', '1x', '1.5', '1e2', true, -1, Number.MAX_SAFE_INTEGER+1]) {
    assert.throws(() => integer(v,1,1000000,'数量'));
  }
});
test('time editing keeps original precision and handles local timezone and clearing', () => {
  const old = process.env.TZ; process.env.TZ = 'Asia/Shanghai';
  try {
    const original='2026-10-28T01:02:03.123456+00:00';
    assert.equal(localTime(original),'2026-10-28T09:02:03');
    assert.equal(isoTime(localTime(original),original), original);
    assert.equal(isoTime('2026-10-28T10:02:03',original),'2026-10-28T02:02:03.000Z');
    assert.equal(isoTime('',original),null);
    for (const bad of ['2026-02-31T10:00','2026-10-28','bad']) assert.throws(() => isoTime(bad,null));
  } finally { if (old===undefined) delete process.env.TZ; else process.env.TZ=old; }
});
test('pool payload includes revision, validates catalog and leaves draft untouched', () => {
  const draft=pool();const frozen=structuredClone(draft);
  const result=poolPayload(draft,catalog,7);
  assert.equal(result.expected_revision,7);assert.equal(result.entries[1].weight,3);
  assert.deepEqual(draft,frozen);assert.equal(result.starts_at,null);
  draft.entries[0].unit_id=99;assert.throws(() => poolPayload(draft,catalog,7));
});
test('pool rejects duplicates, invalid levels, empty pools and invalid time windows', () => {
  for (const change of [p=>p.entries.push({...p.entries[0]}),p=>p.entries[0].level=11,p=>p.entries=[],
    p=>p.enabled='false',p=>p.id=123,p=>{p.starts_local='2026-10-29T00:00';p.ends_local='2026-10-28T00:00';}]) {
    const p=pool();change(p);assert.throws(() => poolPayload(p,catalog,1));
  }
});
test('adding a quest resolves cycles and all required children without mutating draft', () => {
  const draft=event();draft.quests=[];
  const result=addQuest(draft,11,catalog);
  assert.deepEqual(result.quests.map(q=>q.quest_id),[11,12]);assert.deepEqual(draft.quests,[]);
  assert.deepEqual(result.quests[1].drops,[],'missing original drop never silently becomes a local no-drop override');
  assert.throws(() => addQuest(draft,99,catalog));
  assert.throws(() => addQuest(draft,777,catalog));
});
test('event retains optional rewards and strips read-only drop metadata', () => {
  const result=eventPayload(event(),catalog,5);
  assert.equal(result.expected_revision,5);assert.deepEqual(result.quests[0].drops,[]);
  assert.equal(result.quests[1].drops[0].attribute_exp,25);
  assert.equal(result.quests[1].drops[0].sp_event_point,1);
  assert.equal('original_missing' in result.quests[1].drops[0],false);
});

test('adding an existing entrance repairs removed children while preserving its drops', () => {
  const draft=event();draft.quests.pop();
  draft.quests[0].drops=[{drop_data_id:1,entries:[],no_drop_weight:5}];
  const result=addQuest(draft,11,catalog);
  assert.deepEqual(result.quests.map(q=>q.quest_id),[11,12]);
  assert.deepEqual(result.quests[0].drops,draft.quests[0].drops);
});

test('creating an event cannot overwrite an existing ID; editing it is allowed', () => {
  const draft=event(),existing=[structuredClone(draft)];
  assert.throws(()=>eventPayload(draft,catalog,5,existing,true),/标识已存在/);
  assert.doesNotThrow(()=>eventPayload(draft,catalog,5,existing,false));
});
test('enabled event requires explicit missing drops and complete staircase chain', () => {
  const e=event();e.quests[1].drops=[];assert.throws(()=>eventPayload(e,catalog,1));
  e.enabled=false;assert.doesNotThrow(()=>eventPayload(e,catalog,1));
  const incomplete=event();incomplete.quests.pop();assert.throws(()=>eventPayload(incomplete,catalog,1));
});
test('event rejects unverified opening, duplicate bindings, unknown drops and non-event points', () => {
  const e=event();e.quests=[{quest_id:13,drops:[]}];assert.throws(()=>eventPayload(e,catalog,1));
  e.enabled=false;assert.doesNotThrow(()=>eventPayload(e,catalog,1));
  assert.throws(()=>eventPayload(event(),catalog,1,[{id:'other',quests:[{quest_id:11,drops:[]}]}]));
  const bad=event();bad.quests[0].drops=[{drop_data_id:999,entries:[],no_drop_weight:1}];
  assert.throws(()=>eventPayload(bad,catalog,1));
  bad.quests[0].drops=[{drop_data_id:1,entries:[],no_drop_weight:1,sp_event_point:1}];
  assert.throws(()=>eventPayload(bad,catalog,1));
});
test('dropping a unit uses valid ranges, positive totals and unique unit IDs', () => {
  for (const rule of [
    {drop_data_id:1,entries:[],no_drop_weight:0},
    {drop_data_id:1,entries:[{unit_id:1,level_min:3,level_max:2,weight:1}],no_drop_weight:0},
    {drop_data_id:1,entries:[{unit_id:1,level_min:1,level_max:11,weight:1}],no_drop_weight:0},
    {drop_data_id:1,entries:[],no_drop_weight:1,attribute_exp:1000000},
    {drop_data_id:1,entries:[],no_drop_weight:1,sp_event_point:true},
  ]) { const e=event();e.quests[0].drops=[rule];assert.throws(()=>eventPayload(e,catalog,1)); }
});
