import {toDraft, poolPayload, eventPayload, addQuest, unitPreview} from './admin-model.mjs';

const $ = selector => document.querySelector(selector);
const state = {page:'gachas',config:null,catalog:null,availability:null,draft:null,kind:null,dirty:false,busy:false};
let sequence=0;
function el(tag, attrs={}, ...children) {
  const node=document.createElement(tag);
  for (const [key,value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2),value);
    else if (key==='class') node.className=value;
    else if (['value','checked','disabled','hidden','open','required','inert','htmlFor'].includes(key)) node[key]=value;
    else node.setAttribute(key,String(value));
  }
  for (const child of children.flat(Infinity)) if (child!==null && child!==undefined) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
function button(text, action, cls='secondary', attrs={}) {
  return el('button',{type:'button',class:`button ${cls}`,onclick:action,...attrs},text);
}
function field(text,input,hint='') {
  input.id=`field-${++sequence}`;
  return el('div',{class:'field'},el('label',{class:'field-label',htmlFor:input.id},text),input,
    hint ? el('span',{class:'field-hint'},hint):null);
}
function textInput(value,action,attrs={}) {
  return el('input',{value:value??'',oninput:e=>{action(e.target.value);markDirty();},...attrs});
}
function numberInput(value,action,label,min=0,max=1000000) {
  return textInput(value,action,{type:'number',min,max,step:1,'aria-label':label});
}
function markDirty() {state.dirty=true;$('#draft-status').textContent='有未保存的修改';}
function notify(message,error=false) {
  const node=$('#notice');node.textContent=message;node.className=`notice${error?' error':''}`;node.hidden=false;
}
function formError(message) {
  const node=$('#form-error');node.textContent=message;node.hidden=false;node.focus();
}
function setBusy(busy) {
  state.busy=busy;document.body.classList.toggle('is-busy',busy);
  $('#content').inert=busy;$('.sidebar nav').inert=busy;
  $('#refresh').disabled=busy;$('#create-event').disabled=busy;
  $('#editor-fields').disabled=busy;$('#save-editor').disabled=busy;
  $('#cancel-editor').disabled=busy;$('#close-editor').disabled=busy;
  $('#save-editor').textContent=busy?'正在保存…':'保存配置';
}
async function request(path, method='GET', body) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetch(path,{method,cache:'no-store',signal:controller.signal,
      headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    let data;
    try {data=await response.json();} catch {throw new Error('服务返回了无法读取的响应，请检查本地服务是否已更新');}
    if (!response.ok) {
      const message=response.status===409?'配置已被其他操作更新。当前草稿已保留，请记录修改后关闭并刷新，再重新编辑。':
        `保存失败：${data.error?.message ?? `HTTP ${response.status}`}`;
      throw new Error(message);
    }
    return data;
  } catch (error) {
    if (error.name==='AbortError' || error instanceof TypeError) throw new Error('无法确认请求结果。请检查服务连接，并刷新配置核对后再操作。');
    throw error;
  } finally {clearTimeout(timer);}
}
function accept(result) {
  state.config=result.data;state.availability=result.availability;state.updated=new Date();
}
async function refresh() {
  if (state.busy || !closeEditor()) return;
  setBusy(true);
  try {
    const [config,catalog]=await Promise.all([request('/admin/v1/config'),request('/admin/v1/catalog')]);
    if (!catalog.data.quests.every(q=>typeof q.event_openable==='boolean' && Array.isArray(q.next_quest_ids))) {
      throw new Error('服务端目录尚未更新，请使用包含 Web 后台的新版服务');
    }
    state.catalog=catalog.data;accept(config);buildCatalogs();$('#notice').hidden=true;render();
    $('#connection').textContent='本地服务已连接';
  } catch (error) {notify(error.message,true);$('#connection').textContent='连接未完成';}
  finally {setBusy(false);}
}
function buildCatalogs() {
  $('#unit-catalog').replaceChildren(...state.catalog.units.map(u=>el('option',{value:String(u.unit_id),label:u.name})));
  $('#quest-catalog').replaceChildren(...state.catalog.quests.filter(q=>q.event_configurable)
    .map(q=>el('option',{value:String(q.quest_id),label:`${q.name}${q.event_openable?'':'（仅可保存关闭配置）'}`})));
}
const unitName=id=>state.catalog.units.find(u=>u.unit_id===Number(id))?.name ?? '未找到该单位';
function unitThumbnail(id) {
  const info=unitPreview(id,state.catalog);
  if (!info.url) return el('span',{class:'unit-thumb missing',role:'img','aria-label':'暂无角色图像'},'暂无图像');
  const control=button('',()=>showUnitPreview(id),'unit-thumb',{'aria-label':`预览${info.name}（${id}）`});
  control.append(el('img',{src:info.url,alt:info.name,loading:'lazy',onerror:()=>{
    control.replaceChildren(el('span',{},'图像不可用'));control.classList.add('missing');
  }}));
  return control;
}
function showUnitPreview(id) {
  const info=unitPreview(id,state.catalog),body=$('#unit-preview-body');
  $('#unit-preview-title').textContent=info.name;
  body.replaceChildren(el('p',{class:'muted'},`角色 ID ${id}`));
  if (info.url) body.append(el('img',{class:'unit-image-large',src:info.url,alt:info.name,onerror:event=>{
    event.target.replaceWith(el('p',{class:'hint-box'},'角色图像暂不可用，仍可按名称和 ID 配置。'));
  }}));
  else body.append(el('p',{class:'hint-box'},'暂无角色图像'));
  body.append(el('p',{class:'muted'},'原版角色头像 · 放大显示'));
  $('#unit-preview').showModal();
}
$('#close-unit-preview').addEventListener('click',()=>$('#unit-preview').close());
const questInfo=id=>state.catalog.quests.find(q=>q.quest_id===Number(id));
function scheduleText(item) {
  const fmt=value=>new Intl.DateTimeFormat('zh-CN',{dateStyle:'short',timeStyle:'short'}).format(new Date(value));
  if (!item.starts_at && !item.ends_at) return '开放时间不限';
  return `${item.starts_at?fmt(item.starts_at):'即刻'} 至 ${item.ends_at?fmt(item.ends_at):'长期'}`;
}
function activeBadge(kind,item) {
  const active=state.availability[kind].find(r=>r.id===item.id)?.effective_open;
  return el('span',{class:`badge${active?' open':item.enabled?' pending':''}`},active?'开放中':item.enabled?'时间外':'已关闭');
}
function toggle(kind,item) {
  return el('button',{type:'button',class:'toggle',role:'switch','aria-checked':String(item.enabled),
    'aria-label':`${item.enabled?'关闭':'开启'}${item.name}`,onclick:()=>quickToggle(kind,item)},
    el('span',{class:'toggle-track','aria-hidden':'true'}),item.enabled?'已启用':'已停用');
}
function render() {
  if (!state.config) return;
  const eventPage=state.page==='events',title=eventPage?'活动管理':'卡池管理';
  $('#page-title').textContent=title;$('#breadcrumb').textContent=title;
  $('#page-description').textContent=eventPage?'组织活动关卡，配置日程与掉落规则。':'配置召唤内容、条目权重与开放时间。';
  $('#list-title').textContent=eventPage?'全部活动':'全部卡池';
  $('#create-event').hidden=!eventPage;
  $('#pool-count').textContent=state.config.gachas.length;$('#event-count').textContent=state.config.events.length;
  $('#updated-at').textContent=`更新于 ${state.updated.toLocaleTimeString('zh-CN',{hour12:false})}`;
  $('#page-footnote').textContent=eventPage?'配置保存后立即用于新请求。客户端已缓存的活动列表可通过返回标题刷新。':'卡池消耗与抽数沿用原客户端规则。教程首次召唤不受卡池配置影响。';
  for (const nav of document.querySelectorAll('[data-page]')) {
    const selected=nav.dataset.page===state.page;nav.classList.toggle('selected',selected);
    if (selected) nav.setAttribute('aria-current','page');else nav.removeAttribute('aria-current');
  }
  const cards=[['开放卡池',state.availability.gachas.filter(g=>g.effective_open).length,'/ 3','◇'],
    ['开放活动',state.availability.events.filter(e=>e.effective_open).length,`/ ${state.config.events.length}`,'▦'],
    ['配置版本',state.config.revision,'','↗']];
  $('#summary').replaceChildren(...cards.map(([label,n,extra,symbol])=>el('div',{class:'summary-card'},
    el('div',{},el('div',{class:'summary-label'},label),el('div',{class:'summary-number'},n,el('small',{},extra))),el('div',{class:'summary-symbol','aria-hidden':'true'},symbol))));
  const content=$('#content');content.className=eventPage?'event-list':'pool-grid';
  if (!eventPage) content.replaceChildren(...state.config.gachas.map(poolCard));
  else if (!state.config.events.length) {
    content.replaceChildren(el('div',{class:'empty-state'},el('span',{class:'empty-icon','aria-hidden':'true'},'▦'),
      el('h2',{},'还没有活动'),el('p',{},'将已恢复的关卡组成活动，并设置开放时间与掉落规则。'),
      button('＋ 创建第一个活动',()=>openEvent(),'primary')));
  } else content.replaceChildren(...state.config.events.map(eventCard));
}
function poolCard(pool) {
  const info=state.availability.gachas.find(p=>p.id===pool.id),rare=pool.id===20000,ten=pool.id===30000;
  return el('article',{class:`pool-card${rare?' rare':ten?' ten':''}`},
    el('div',{class:'card-heading'},el('span',{class:'pool-symbol','aria-hidden':'true'},rare?'◇':ten?'Ⅹ':'券'),activeBadge('gachas',pool)),
    el('div',{class:'card-body'},el('h3',{},pool.name),el('span',{class:'pool-id'},`POOL ${pool.id}`),
      el('dl',{class:'pool-meta'},el('div',{},el('dt',{},'每次消耗'),el('dd',{},el('strong',{},info.cost),rare?'水晶':'友情点')),
        el('div',{},el('dt',{},'召唤数量'),el('dd',{},el('strong',{},info.draw_count),'名'))),
      el('div',{class:'minor-label'},`卡池内容 · ${pool.entries.length} 名单位`),
      el('div',{class:'unit-tags'},pool.entries.slice(0,4).map(e=>el('span',{class:'unit-tag'},unitThumbnail(e.unit_id),unitName(e.unit_id))),
        pool.entries.length>4?el('span',{class:'unit-tag'},`＋${pool.entries.length-4}`):null),
      el('p',{class:'card-schedule'},scheduleText(pool))),
    el('div',{class:'card-footer'},toggle('gachas',pool),button('配置卡池 →',()=>openPool(pool),'ghost')));
}
function eventCard(event) {
  return el('article',{class:'event-card'},el('div',{},
    el('div',{class:'event-name'},el('h3',{},event.name),activeBadge('events',event)),
    el('div',{class:'event-info'},el('span',{},event.id),el('span',{},`${event.quests.length} 个关卡`),el('span',{},scheduleText(event)))),
    el('div',{class:'event-actions'},toggle('events',event),button('编辑活动',()=>openEvent(event),'secondary small'),
      button('删除',()=>deleteEvent(event),'danger small')));
}
async function quickToggle(kind,item) {
  if (state.busy) return;
  setBusy(true);
  try {accept(await request(`/admin/v1/${kind}/${encodeURIComponent(item.id)}`,'PATCH',
    {enabled:!item.enabled,expected_revision:state.config.revision}));notify(`${item.name} 已${item.enabled?'停用':'启用'}`);render();}
  catch (error) {notify(error.message,true);} finally {setBusy(false);}
}
async function deleteEvent(event) {
  if (state.busy || !confirm(`删除活动“${event.name}”？关卡将解除该活动的绑定。`)) return;
  setBusy(true);
  try {
    accept(await request('/admin/v1/config','PUT',{expected_revision:state.config.revision,
      gachas:state.config.gachas,events:state.config.events.filter(e=>e.id!==event.id)}));
    notify('活动已删除');render();
  } catch (error) {notify(error.message,true);} finally {setBusy(false);}
}
function closeEditor() {
  if (state.busy) return false;
  if (!$('#editor').open) return true;
  if (state.dirty && !confirm('放弃尚未保存的修改？')) return false;
  $('#editor').close();state.draft=null;state.dirty=false;return true;
}
function openPool(pool) {openEditor('gachas',toDraft(pool));}
function openEvent(event) {
  const blank={id:'',name:'',enabled:false,starts_at:null,ends_at:null,quests:[]};
  openEditor('events',toDraft(event??blank),!event);
}
function openEditor(kind,draft,isNew=false) {
  if (state.busy) return;
  state.kind=kind;state.draft=draft;state.isNew=isNew;state.dirty=false;state.editRevision=state.config.revision;
  $('#form-error').hidden=true;$('#draft-status').textContent=`基于配置版本 ${state.editRevision}`;
  $('#editor-title').textContent=kind==='gachas'?`编辑${draft.name}`:isNew?'新建活动':`编辑${draft.name}`;
  $('#editor-kicker').textContent=kind==='gachas'?`POOL ${draft.id}`:'活动设置';
  renderEditor();$('#editor').showModal();
}
function renderEditor() {
  const draft=state.draft,root=$('#editor-fields');root.replaceChildren();
  const common=el('div',{class:'form-grid'},field('名称',textInput(draft.name,v=>draft.name=v,{required:true,maxLength:80,placeholder:'输入名称'})));
  if (state.kind==='events') common.append(field('活动标识',textInput(draft.id,v=>draft.id=v,{required:true,maxLength:64,
    pattern:'[a-z0-9][a-z0-9-]{0,63}',disabled:!state.isNew,placeholder:'例如 summer-event'}),'小写字母、数字和连字符，创建后不更改。'));
  root.append(common);
  const tz=Intl.DateTimeFormat().resolvedOptions().timeZone;
  root.append(el('div',{class:'schedule-box'},el('label',{class:'check-label'},
    el('input',{type:'checkbox',checked:draft.enabled,onchange:e=>{draft.enabled=e.target.checked;markDirty();}}),'启用此'+(state.kind==='gachas'?'卡池':'活动')),
    el('div',{class:'form-grid'},field('开始时间',textInput(draft.starts_local,v=>draft.starts_local=v,{type:'datetime-local',step:1})),
      field('结束时间',textInput(draft.ends_local,v=>draft.ends_local=v,{type:'datetime-local',step:1}))),
    el('p',{class:'field-hint'},`时间按浏览器时区 ${tz} 输入。留空表示不限制；启用且处于时间范围内才会开放。`)));
  if (state.kind==='gachas') {
    root.append(el('div',{class:'form-section-heading'},el('h3',{},'卡池单位'),el('span',{class:'muted'},'各次独立按权重抽取')),
      renderEntries(draft.entries,false));
  } else renderEventQuests(root);
}
function renderEntries(rows,drop,rule=null) {
  const box=el('div',{}),body=el('tbody',{}),totalLabel=el('span',{class:'muted'});
  const probs=[];
  function updateProbabilities() {
    const weights=rows.map(r=>/^\d+$/.test(String(r.weight)) && Number(r.weight)>0?Number(r.weight):NaN);
    const empty=drop?Number(rule.no_drop_weight):0;
    const total=weights.reduce((a,b)=>a+b,0)+empty;
    probs.forEach((node,i)=>node.textContent=Number.isFinite(total)&&total>0?`${(weights[i]/total*100).toFixed(2)}%`:'—');
    totalLabel.textContent=Number.isFinite(total)?`总权重 ${total.toLocaleString()}${drop?` · 空掉落 ${total>0?(empty/total*100).toFixed(2):'—'}%`:''}`:'请填写有效权重';
  }
  function draw() {
    probs.length=0;body.replaceChildren();
    rows.forEach((row,index)=>{
      const name=el('span',{class:'unit-name'},unitName(row.unit_id));
      const preview=el('div',{class:'unit-row-image'},unitThumbnail(row.unit_id));
      const unit=textInput(row.unit_id,v=>{row.unit_id=v;name.textContent=unitName(v);preview.replaceChildren(unitThumbnail(v));},
        {class:'unit-input',list:'unit-catalog',required:true,inputMode:'numeric','aria-label':`单位 ID 第 ${index+1} 行`});
      const cells=[el('td',{},el('div',{class:'unit-selector'},preview,el('div',{},unit,name)))];
      for (const [key,label] of (drop?[['level_min','最低等级'],['level_max','最高等级']]:[['level','等级']])) {
        cells.push(el('td',{},numberInput(row[key],v=>row[key]=v,`${label}第 ${index+1} 行`,1,999)));
      }
      cells.push(el('td',{},numberInput(row.weight,v=>{row.weight=v;updateProbabilities();},`权重第 ${index+1} 行`,1)));
      const probability=el('td',{class:'muted'});probs.push(probability);cells.push(probability);
      cells.push(el('td',{},el('button',{class:'remove-row',type:'button','aria-label':`移除第 ${index+1} 个单位`,onclick:()=>{rows.splice(index,1);markDirty();draw();}},'×')));
      body.append(el('tr',{},cells));
    });
    updateProbabilities();
  }
  const headers=drop?['单位 ID / 名称','最低等级','最高等级','权重','概率','']:['单位 ID / 名称','等级','权重','概率',''];
  box.append(el('div',{class:'entry-table-wrap'},el('table',{class:'entry-table'},el('thead',{},el('tr',{},headers.map(h=>el('th',{scope:'col'},h)))),body)),
    el('div',{class:'entry-bottom'},button('＋ 添加单位',()=>{
      if (rows.length>=256) {formError('最多配置 256 个单位');return;}
      const unit=state.catalog.units.find(u=>!rows.some(r=>Number(r.unit_id)===u.unit_id));
      if (!unit) return;
      rows.push({unit_id:unit.unit_id,...(drop?{level_min:1,level_max:1}:{level:1}),weight:1});markDirty();draw();
    },'ghost'),totalLabel));
  box.updateProbabilities=updateProbabilities;draw();return box;
}
function renderEventQuests(root) {
  const draft=state.draft;
  root.append(el('div',{class:'form-section-heading'},el('h3',{},'活动关卡'),el('span',{class:'muted'},`${draft.quests.length} 个关卡`)),
    el('p',{class:'editor-description'},'添加入口会包含全部必需子层。默认保留原始掉落；展开掉落表后可选择本地覆盖。'));
  const questInput=el('input',{list:'quest-catalog',placeholder:'输入关卡 ID 或搜索名称',inputMode:'numeric'});
  root.append(el('div',{class:'quest-add'},field('添加关卡',questInput),button('＋ 添加关卡',()=>{
    try {
      state.draft=addQuest(state.draft,questInput.value,state.catalog);markDirty();renderEditor();
    } catch (error) {formError(error.message);}
  })));
  if (!draft.quests.length) root.append(el('div',{class:'hint-box'},'请先添加关卡。未验收关卡可以保存关闭配置，不能在正式模式启用。'));
  for (const quest of draft.quests) {
    const info=questInfo(quest.quest_id),card=el('section',{class:'quest-card'}),body=el('div',{class:'quest-card-body'});
    card.append(el('div',{class:'quest-card-head'},el('div',{},el('strong',{},`${quest.quest_id} · ${info?.name??'未知关卡'}`),
      el('span',{class:`badge ${info?.event_openable?'open':'pending'}`},info?.event_openable?'允许开放':'仅可保存关闭配置')),
      button('移除',()=>{draft.quests=draft.quests.filter(q=>q.quest_id!==quest.quest_id);markDirty();renderEditor();},'ghost small')));
    if (info?.next_quest_ids.length) body.append(el('p',{class:'quest-help'},`必需子层：${info.next_quest_ids.join('、')}`));
    const originals=state.catalog.event_quest_drops[String(quest.quest_id)]??[];
    for (const original of originals) body.append(dropEditor(quest,original,info));
    if (!originals.length) body.append(el('p',{class:'quest-help'},'此关卡没有可覆盖的掉落表。'));
    card.append(body);root.append(card);
  }
}
function dropEditor(quest,original,info) {
  const existing=quest.drops.find(d=>d.drop_data_id===original.drop_data_id),details=el('details',{class:'drop-rule',open:!!existing});
  const status=el('span',{class:`badge${original.original_missing?' alert':''}`},existing?'使用本地覆盖':original.original_missing?'原始数据缺失，需明确配置':'保留原始掉落');
  details.append(el('summary',{},`掉落表 ${original.drop_data_id}`,status));
  const body=el('div',{class:'drop-content'}),fields=el('div',{});
  const checkbox=el('input',{type:'checkbox',checked:!!existing,onchange:e=>{
    if (e.target.checked) {
      const copy=structuredClone(original);delete copy.original_missing;quest.drops.push(copy);
    } else quest.drops=quest.drops.filter(d=>d.drop_data_id!==original.drop_data_id);
    markDirty();draw();
  }});
  body.append(el('label',{class:'check-label'},checkbox,'使用本地规则覆盖此掉落表'));
  if (original.original_missing) body.append(el('div',{class:'hint-box'},'原始掉落数据尚未恢复。勾选覆盖后，按下方明确指定的本地规则生效；单位列表为空且空掉落权重大于 0 表示不掉卡。'));
  body.append(fields);details.append(body);
  function draw() {
    fields.replaceChildren();
    const rule=quest.drops.find(d=>d.drop_data_id===original.drop_data_id);
    status.textContent=rule?'使用本地覆盖':original.original_missing?'原始数据缺失，需明确配置':'保留原始掉落';
    if (!rule) return;
    const entries=renderEntries(rule.entries,true,rule);
    fields.append(el('div',{class:'reward-grid'},
      field('空掉落权重',numberInput(rule.no_drop_weight,v=>{rule.no_drop_weight=v;entries.updateProbabilities();},'空掉落权重')),
      field('每敌属性经验',numberInput(rule.attribute_exp??0,v=>rule.attribute_exp=v,'每敌属性经验',0,999999)),
      field('每敌活动积分',numberInput(rule.sp_event_point??0,v=>rule.sp_event_point=v,'每敌活动积分',0,999),
        info?.event_point_configurable?`原活动 ID ${info.sp_event_id}`:'此关卡没有原活动积分身份，只允许 0。')),
      entries);
  }
  draw();return details;
}
$('#editor-form').addEventListener('submit',async event=>{
  event.preventDefault();if (state.busy) return;
  let payload;
  try {payload=state.kind==='gachas'?poolPayload(state.draft,state.catalog,state.editRevision):
    eventPayload(state.draft,state.catalog,state.editRevision,state.config.events,state.isNew);}
  catch (error) {formError(error.message);return;}
  setBusy(true);$('#form-error').hidden=true;
  try {
    const result=await request(`/admin/v1/${state.kind}/${encodeURIComponent(payload.id)}`,'PUT',payload);
    accept(result);state.dirty=false;$('#editor').close();state.draft=null;notify('配置已保存，新请求按此配置执行。');render();
  } catch (error) {formError(error.message);} finally {setBusy(false);}
});
for (const button of document.querySelectorAll('[data-page]')) button.addEventListener('click',()=>{
  if (!state.busy && closeEditor()) {state.page=button.dataset.page;render();}
});
$('#refresh').addEventListener('click',refresh);
$('#create-event').addEventListener('click',()=>openEvent());
$('#cancel-editor').addEventListener('click',closeEditor);$('#close-editor').addEventListener('click',closeEditor);
$('#editor').addEventListener('cancel',event=>{event.preventDefault();closeEditor();});
window.addEventListener('beforeunload',event=>{if (state.dirty) {event.preventDefault();event.returnValue='';}});
refresh();
