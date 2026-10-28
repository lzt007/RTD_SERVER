/** Pure form conversion; the API remains the authority for all configuration. */
export function unitPreview(id,catalog) {
  const unit=/^\d+$/.test(String(id))?catalog.units.find(u=>u.unit_id===Number(id)):null;
  const url=unit?.icon_url;
  return {name:unit?.name??'未找到该单位',url:typeof url==='string' && /^\/admin\/assets\/unit-icons\/[1-9][0-9]{0,7}\.png$/.test(url)?url:null};
}

export function integer(value, min, max, label) {
  if (!['string','number'].includes(typeof value) || !/^\d+$/.test(String(value))) throw new Error(`${label}必须为整数`);
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < min || number > max) throw new Error(`${label}须在 ${min}–${max} 之间`);
  return number;
}

export function localTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) throw new Error('时间格式无效');
  const pad = n => String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function isoTime(value, original = null) {
  if (!value) return null;
  if (original && localTime(original) === value) return original;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) throw new Error('请选择有效的日期与时间');
  const [, y,m,d,h,minute,s='00'] = match;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()) || date.getFullYear()!==Number(y) || date.getMonth()+1!==Number(m)
      || date.getDate()!==Number(d) || date.getHours()!==Number(h) || date.getMinutes()!==Number(minute)
      || date.getSeconds()!==Number(s)) throw new Error('请选择有效的日期与时间');
  return date.toISOString();
}

export function toDraft(item) {
  return {...structuredClone(item), starts_local:localTime(item.starts_at), ends_local:localTime(item.ends_at)};
}

function schedule(draft) {
  const name = draft.name?.trim();
  if (!name || name.length>80) throw new Error('名称须为 1–80 个字符');
  if (typeof draft.enabled!=='boolean') throw new Error('启用状态无效');
  const starts_at=isoTime(draft.starts_local,draft.starts_at), ends_at=isoTime(draft.ends_local,draft.ends_at);
  if (starts_at && ends_at && Date.parse(ends_at)<=Date.parse(starts_at)) throw new Error('结束时间必须晚于开始时间');
  return {name,enabled:draft.enabled,starts_at,ends_at};
}

function entries(rows, catalog, drop=false) {
  if (!Array.isArray(rows) || rows.length>(256) || (!drop && !rows.length)) throw new Error('条目数量须为 1–256 项；掉落条目允许为空');
  const seen=new Set();
  return rows.map(row=>{
    const unit_id=integer(row.unit_id,1,2147483647,'单位 ID');
    const unit=catalog.units.find(u=>u.unit_id===unit_id);
    if (!unit || seen.has(unit_id)) throw new Error(`单位 ${unit_id} 不在目录中或重复出现`);
    seen.add(unit_id);
    const weight=integer(row.weight,1,1000000,'权重');
    if (!drop) return {unit_id,level:integer(row.level,1,unit.max_level,`${unit.name}等级`),weight};
    const level_min=integer(row.level_min,1,unit.max_level,'最低等级');
    const level_max=integer(row.level_max,level_min,unit.max_level,'最高等级');
    return {unit_id,level_min,level_max,weight};
  });
}

export function poolPayload(draft,catalog,revision) {
  const id=integer(draft.id,1,30000,'卡池 ID');
  if (![10000,20000,30000].includes(id)) throw new Error('只能修改现有的三个卡池');
  return {id,...schedule(draft),entries:entries(draft.entries,catalog),expected_revision:revision};
}

export function addQuest(draft,id,catalog) {
  const copy=structuredClone(draft), seen=new Set(copy.quests.map(q=>q.quest_id)), walked=new Set(), pending=[Number(id)];
  while (pending.length) {
    const next=pending.shift();
    const quest=catalog.quests.find(q=>q.quest_id===next);
    if (!quest?.event_configurable) throw new Error(`关卡 ${next} 尚不支持活动配置`);
    // Walk existing entrances too, so re-adding one repairs removed children.
    if (walked.has(next)) continue;
    walked.add(next);
    if (!seen.has(next)) {seen.add(next);copy.quests.push({quest_id:next,drops:[]});}
    pending.push(...quest.next_quest_ids);
  }
  return copy;
}

export function eventPayload(draft,catalog,revision,events=[],isNew=false) {
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(draft.id)) throw new Error('活动标识须为小写字母、数字或连字符，最多 64 字符');
  if (isNew && events.some(e=>e.id===draft.id)) throw new Error('活动标识已存在，请使用新的标识或编辑现有活动');
  const base=schedule(draft),seen=new Set();
  if (!draft.quests.length) throw new Error('请至少添加一个关卡');
  const quests=draft.quests.map(q=>{
    const id=integer(q.quest_id,1,2147483647,'关卡 ID');
    const source=catalog.quests.find(c=>c.quest_id===id);
    if (!source?.event_configurable || seen.has(id)) throw new Error(`关卡 ${id} 不可配置或重复出现`);
    if (base.enabled && !source.event_openable) throw new Error(`关卡 ${id} 尚未验收，只能保存为关闭状态`);
    if (events.some(e=>e.id!==draft.id && e.quests.some(c=>c.quest_id===id))) throw new Error(`关卡 ${id} 已被其他活动占用`);
    seen.add(id);
    const originals=catalog.event_quest_drops[String(id)] ?? [],dropIds=new Set();
    const drops=q.drops.map(rule=>{
      const drop_data_id=integer(rule.drop_data_id,0,2147483647,'掉落表 ID');
      if (!originals.some(o=>o.drop_data_id===drop_data_id) || dropIds.has(drop_data_id)) throw new Error(`关卡 ${id} 的掉落表 ${drop_data_id} 无效或重复`);
      dropIds.add(drop_data_id);
      const clean={drop_data_id,no_drop_weight:integer(rule.no_drop_weight,0,1000000,'空掉落权重'),entries:entries(rule.entries,catalog,true)};
      if (!clean.entries.length && !clean.no_drop_weight) throw new Error('空掉落规则必须有正的空掉落权重');
      if ('attribute_exp' in rule) clean.attribute_exp=integer(rule.attribute_exp,0,999999,'属性经验');
      if ('sp_event_point' in rule) {
        clean.sp_event_point=integer(rule.sp_event_point,0,999,'活动积分');
        if (clean.sp_event_point && !source.event_point_configurable) throw new Error(`关卡 ${id} 没有可用的原活动积分身份`);
      }
      return clean;
    });
    if (base.enabled && originals.some(o=>o.original_missing && !dropIds.has(o.drop_data_id))) throw new Error(`关卡 ${id} 缺少原掉落数据，请明确配置本地覆盖规则`);
    return {quest_id:id,drops};
  });
  if (base.enabled) for (const q of quests) {
    const source=catalog.quests.find(c=>c.quest_id===q.quest_id);
    if (source.next_quest_ids.some(id=>!seen.has(id))) throw new Error(`关卡 ${q.quest_id} 缺少必需子层，请重新添加入口补齐`);
  }
  return {id:draft.id,...base,quests,expected_revision:revision};
}
