"""Archive per-quest reconstruction readiness without touching real accounts or schedules."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rtd.services.api import API
from rtd.policies.quest_content import SINGLE_QUESTS,VERIFIED_LAYER_QUESTS
from rtd.policies.event_content import audit_events,recovered_asset_names


def report():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'0','RTD_SHINGETSU_RECONSTRUCTION':'1'}):
            baseline=API(Path(tmp)/'baseline.sqlite3')
        with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1','RTD_SHINGETSU_RECONSTRUCTION':'1'}):
            repaired=API(Path(tmp)/'repaired.sqlite3')
        normal=baseline.event_quests|SINGLE_QUESTS|VERIFIED_LAYER_QUESTS
        candidate=repaired.event_reconstruction
        sources={p['quest_id']:p for p in json.loads((Path(__file__).resolve().parents[1]/'config/event-reconstruction-sources.json').read_text())['profiles']}
        categories={q['id']:q['name'] for q in baseline.masters[31]['data_list']}
        tables={t['id']:t for t in baseline.masters[21]['data_list']}
        enemies={e['id']:e for e in baseline.masters[20]['data_list']}
        units={u['id']:u['name'] for u in baseline.masters[10]['data_list']}
        drops={r['id']:r for r in candidate['drops']}
        rows=[]
        for quest in baseline.masters[30]['data_list']:
            if quest['division']!=20000:continue
            id=quest['id'];source=sources.get(id)
            row=dict(id=id,name=quest['name'],category=categories[quest['category']],
                     source=source['path'] if source else None,section=source['section'] if source else None,
                     status='unchanged' if id in normal else 'ready_closed' if id in repaired.reconstructed_quests else 'blocked',
                     repairs=[],blockers=[],client_verified=False)
            if row['status']=='ready_closed':
                row['repairs'].append('保留原图' if id in baseline.levels else '推测单层地图与可行挑战路线，保留原距离/场景')
                provenance=next(p for p in candidate['provenance'] if p['quest_id']==id)
                row['inferred_drop_ids']=sorted(set(provenance['drop_ids']))
                row['drop_candidates']={str(did):[dict(unit_id=drop[f'unit{i}_id'],name=units[drop[f'unit{i}_id']],rate=drop[f'unit{i}_rate'],level=1) for i in range(1,5) if drop[f'unit{i}_id']]
                                        for did in row['inferred_drop_ids'] for drop in [drops[did]]}
                row['repairs'].append('补缺失掉落表 '+','.join(map(str,row['inferred_drop_ids']))+'；概率/等级为估算')
                table=tables[quest['enemy_table_id']];boss=enemies[table['death_set_id']]
                row['boss']=dict(enemy_id=boss['id'],name=boss['name'],model=boss['model'],type=boss['type'])
                row['repairs'].append('Boss沿用 '+str(boss['id'])+' '+boss['model'])
                row['visual_substitutions']=[r for r in candidate['visual_substitutions'] if id in r['quest_ids']]
                if row['visual_substitutions']:
                    row['repairs'].append('缺失外观替代 '+','.join(str(r['enemy_id'])+':'+r['before']['model']+'→'+r['after']['model'] for r in row['visual_substitutions']))
                else:row['repairs'].append('已有外观保持')
                row['repairs'].append('未排期，客户端停止标记+服务端入口关闭；待实机')
            elif row['status']=='blocked':
                row['blockers']=candidate['blocked'].get(str(id),[])
                if not row['blockers']:
                    if not source:row['blockers'].append('现有106页攻略没有可靠对应章节，不猜测身份及掉落')
                    if id not in baseline.levels:row['blockers'].append('原始地图缺失')
                    row['blockers'].extend(baseline.event_rejections.get(id,[]))
                    if id==20000 or 20100<=id<=20163:row['blockers'].append('多层协议关卡，不能摊平成单层')
                    if not row['blockers']:row['blockers'].append('未通过现有协议及资源准入检查')
            rows.append(row)
        return dict(policy=candidate['policy'],summary={state:sum(r['status']==state for r in rows) for state in ('unchanged','ready_closed','blocked')},
                    quests=rows),candidate


def markdown(data):
    summary=data['summary']
    lines=['# 活动关卡批量修复记录（2026-11-03）','',
           f"全量核对882条活动记录：新增可排期且保持关闭 {summary['ready_closed']} 条；原本可用并保持不变 {summary['unchanged']} 条；在当前证据和协议下仍受阻 {summary['blocked']} 条。",'',
           '新增关卡完成数据检查、离线资源清单及文件校验与服务端协议验证，均待客户端实机。神月只确认曾成功进入，不将该结果扩大为本批关卡已实机通过。受阻不等于永久无法恢复。', '',
           '原始地图、掉落、敌人配置优先；只补缺失记录。权重、等级、路线及怪物位置均为推测。正常关卡的有效主表、地图、敌人外观、掉落及开放状态做前后对比；共享记录不连带替换。', '',
           '## 修复后可用、未开启', '', '| ID | 分类／关卡 | 具体修复方案简报 | 攻略 |','| --- | --- | --- | --- |']
    for row in data['quests']:
        if row['status']!='ready_closed':continue
        source='['+row['section']+'](../../'+row['source'].removeprefix('docs/')+')'
        lines.append('| '+str(row['id'])+' | '+row['category']+'／'+row['name']+' | '+'；'.join(row['repairs']).replace('|','／')+' | '+source+' |')
    lines+=['','## 当前仍无法修复', '', '| ID | 分类／关卡 | 具体原因 |','| --- | --- | --- |']
    for row in data['quests']:
        if row['status']=='blocked':lines.append('| '+str(row['id'])+' | '+row['category']+'／'+row['name']+' | '+'；'.join(row['blockers']).replace('|','／')+' |')
    lines+=['','## 原本正常：保持不变', '', '| ID | 分类／关卡 |','| --- | --- |']
    for row in data['quests']:
        if row['status']=='unchanged':lines.append('| '+str(row['id'])+' | '+row['category']+'／'+row['name']+' |')
    lines+=['','## 本地复现与限制','',
            '使用离线UnityPy==1.25.4运行scripts/prepare_event_reconstruction_resources.py --output resources/reconstructed/events/bundles，输出目录必须不存在。原资源不覆盖；缺失书本1–6用独立内部资源名的兽王标记临时代替，战斗角色本体仍用原包。', '',
            'API和资源进程显式设置RTD_EVENT_RECONSTRUCTION=1才启用该独立重建层；默认关闭。另保留原RTD_SHINGETSU_RECONSTRUCTION开关。本轮未部署生产，未创建或修改真实排期。新增关卡需后续明确排期才开放。', '',
            'JSON附表保留每关源章节、估算掉落单位/权重、视觉替代和阻塞原因；config/event-reconstruction-sources.json保留攻略原行。资源调查见config/event-reconstruction-assets.json。', '']
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    data,candidate=report()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    args.output.with_suffix('.md').write_text(markdown(data))
    if args.candidate:args.candidate.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(data['summary']))
