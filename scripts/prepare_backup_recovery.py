"""Build individually validated compatibility candidates from the unpacked backup.
Failures are recorded, never installed as successful recovery.
"""
import csv
import json
import re
import sys
from pathlib import Path
from prepare_monster_recovery import ROOT, WS, convert_model
from prepare_wolf_closed_bundle import rebuild
sys.path.insert(0,str(ROOT))


def build(only=None):
    index=json.loads((ROOT/'docs/resource-audit/new-backup/新备份资源索引.json').read_text())
    assets=index['assets']; sources=index['sources']; by_name={}
    for a in assets:by_name.setdefault(a['name'],[]).append(a)
    rows=list(csv.DictReader((ROOT/'docs/resource-audit/new-backup/复用决策表.csv').open(encoding='utf-8-sig')))
    gap_textures={r['原引用'] for r in rows if r['类别']=='贴图'}
    output=ROOT/'resources/reconstructed/backup-recovery';output.mkdir(parents=True,exist_ok=True)
    validation=output/'validation.json'
    previous=json.loads(validation.read_text()) if validation.exists() else []
    results=[r for r in previous if only and r['model'] not in only]
    from rtd.masters.catalog import load_catalog
    masters,_=load_catalog()
    active={}
    motion_names={}; action={}
    for line in (ROOT/'docs/resource-audit/loading-chain/loader-definitions.tsv').read_text().splitlines():
        parts=line.split('\t')
        if parts[0]=='M':motion_names[int(parts[1])]=parts[2]
        elif parts[0]=='A':action[(int(parts[1]),int(parts[2]))]=int(parts[3])
    model_motion_prefixes={}
    for enemy in masters[20]['data_list']:
        active.setdefault(enemy['model'],set()).add(enemy['texture'])
        for column in (0,1):
            motion=motion_names.get(action.get((enemy['type']+36,column)),'')
            if motion.endswith(('_wait_01','_atk_01')):
                model_motion_prefixes.setdefault(enemy['model'],set()).add(motion.rsplit('_',2)[0])
    for row in rows:
        if row['类别']!='模型':continue
        name=row['原引用']; model=name.removeprefix('ast_')
        if only and model not in only:continue
        choices=[a for a in by_name.get(name,[]) if a['type']=='GameObject']
        if not choices:
            candidates=row['已有同族候选'].split('；')
            choices=[a for n in candidates for a in by_name.get(n,[]) if a['type']=='GameObject']
        if not choices:continue
        attr_match=re.search(r'_(fire|water|holy|dark|un)(?:_|$)',model)
        attr=attr_match.group(1) if attr_match else model.rsplit('_',1)[-1]
        codes={'fire':['fire','f'],'water':['water','w','u'],'holy':['holy','h'],'dark':['dark','d']}.get(attr,[attr])
        matching=[a for a in choices if any(('_'+code+'_') in a['name'] or a['name'].endswith('_'+code) for code in codes)]
        choices=matching or choices
        selection_proof=None
        if not any(a['name']==name for a in choices) and any(tag in model for tag in ('_four_','_dra_','_fly_')):
            from select_backup_skeleton import select_source
            all_choices=[a for n in row['已有同族候选'].split('；') for a in by_name.get(n,[]) if a['type']=='GameObject']
            # Compatibility first; design prefix and attribute only break ties.
            all_choices.sort(key=lambda a:(not re.sub(r'^\d+_','',a['name'].removeprefix('ast_')).startswith('_'.join(model.split('_')[:2])+'_'),not any(('_'+c+'_') in a['name'] or a['name'].endswith('_'+c) for c in codes)))
            prefixes=model_motion_prefixes.get(model,set())
            prefix=next(iter(prefixes)) if len(prefixes)==1 else re.search(r'(ms\d+_[^_]+)',model).group(1)
            selected,selection_proof=select_source(all_choices,sources,WS/'resources/unpacked',prefix)
            choices=[selected]
        source_asset=choices[0]; source=WS/'resources/unpacked'/sources[source_asset['source']]['path']
        source_model=source_asset['name'].removeprefix('ast_')
        tex=[a for a in assets if a['source']==source_asset['source'] and a['type']=='Texture2D']
        requested=[n for n in active.get(model,[]) if n in gap_textures]
        textures={}
        for n in sorted(requested):
            if n=='na':continue
            exact=[a for a in by_name.get(n,[]) if a['type']=='Texture2D']
            if not exact:
                family_name=re.search(r'ms\d+_([^_]+)',model).group(1)
                attr=n.rsplit('_',1)[-1]
                exact=[a for a in assets if a['type']=='Texture2D' and re.search(r'ms\d+_'+family_name+r'_',a['name']) and a['name'].endswith('_'+attr)]
            textures[n]=WS/'resources/unpacked'/sources[exact[0]['source']]['path'] if exact else source
        family=re.search(r'(ms\d+_[^_]+)',model).group(1)
        if model.startswith('ms04_dra_'):
            family='_'.join(model.split('_')[:3])
        prefixes=model_motion_prefixes.get(model,set())
        if len(prefixes)==1:family=next(iter(prefixes))
        if family=='ms00_death':family='death'
        if family in {'ms00_book','ms00_floor','ms00_kaidan'}:family=family.split('_')[1]
        entry=dict(builder_revision='backup-type-motion-closure-v2',model=model,source_model=source_model,inferred=name!=source_asset['name'],reason='Recovered backup artwork; same-family correspondence inferred.' if name!=source_asset['name'] else 'Recovered exact-name backup artwork; compatibility serialization.')
        if selection_proof is not None:entry['source_selection']=selection_proof
        try:
            info=convert_model(source,output/'raw'/(model+'.unity3d'),model,textures,source_model=source_model,motion_family=family)
            closed=rebuild(output/'raw'/(model+'.unity3d'),output/'bundles'/(model+'.unity3d'),policy='backup-multimaterial-closure-v1')
            entry.update(info);entry.update(closed);entry['status']='validated_candidate'
        except Exception as exc:entry.update(status='blocked',error=str(exc))
        results.append(entry)
        (output/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        print(model,entry['status'],entry.get('error','')[:180],flush=True)
    return results

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+')
    args=parser.parse_args();build(args.only)
