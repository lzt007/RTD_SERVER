"""Opt-in, missing-file-only resource overlay for prepared event reconstructions."""
import hashlib
import json
import os
from ..config import ROOT


def bundle_file(name):
    if os.environ.get('RTD_EVENT_RECONSTRUCTION','0')!='1':return None
    assets=json.loads((ROOT/'config/event-reconstruction-assets.json').read_text())
    allowed=set(assets['bundle_sources'])|{f'ms00_book_el_0{i}.unity3d' for i in range(1,7)}
    if name not in allowed:return None
    path=ROOT/'resources/reconstructed/events/bundles'/name
    return path if path.is_file() else None


def resource_issues(masters,levels,quest_ids,assets):
    quests={q['id']:q for q in masters[30]['data_list']}
    tables={t['id']:t for t in masters[21]['data_list']}
    enemies={e['id']:e for e in masters[20]['data_list']}
    characters={e['enemy_id']:e for e in assets['character_dependencies']}
    local={'ms00_tresure_unit_01','ms01_sla_lv1','ms01_squ_lv1','ms02_four_un_01','ms02_dra_un_01'}
    issues={}
    markers=json.loads((ROOT/'config/event-reconstruction-book-markers.json').read_text())['bundles']
    marker_hashes={r['generated_bundle']:r['generated_sha256'] for r in markers}
    checked={}
    def exists(name):
        if name in checked:return checked[name]
        original=ROOT/'resources/bundles'/name
        path=original if original.is_file() else ROOT/'resources/reconstructed/events/bundles'/name
        expected=assets['source_hashes'].get('resources/bundles/'+name)
        if not original.is_file():expected=assets['bundle_sources'].get(name,{}).get('sha256') or marker_hashes.get(name)
        checked[name]=path.is_file() and bool(expected) and hashlib.sha256(path.read_bytes()).hexdigest()==expected
        return checked[name]
    for id in quest_ids:
        table=tables[quests[id]['enemy_table_id']]
        slots={b&31 for b in bytes.fromhex(levels[id]['map_data']) if 1<=b&31<=18}
        reasons=[]
        for prefix in ['boss','death']+[f'enemy{i}' for i in slots]:
            enemy=enemies[table[prefix+'_set_id']]
            if prefix in ('boss','death') and enemy['type']==25:
                reasons.append('fish Boss original run motion ms01_fish_run_01 absent; null guarded but animation continuity unverified')
            if enemy['type'] in (22,24,30,31,33,37):
                dep=characters.get(enemy['id'])
                if not dep or not dep['model_present']:reasons.append('missing original character model '+enemy['model']);continue
                if enemy['model']!=dep['model']:reasons.append('character model cannot be resolved in original group bundle');continue
                if not exists(dep['bundle']):reasons.append('missing character group bundle '+dep['bundle'])
                book=f"ms00_book_el_0{dep['book_color']}.unity3d"
                if not exists(book):reasons.append('unprepared book marker '+book)
            elif enemy['model'] not in local and not exists(enemy['model']+'.unity3d'):
                reasons.append('unavailable model download '+enemy['model'])
        if reasons:issues[str(id)]=sorted(set(reasons))
    return issues
