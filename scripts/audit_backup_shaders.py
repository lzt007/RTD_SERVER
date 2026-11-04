"""Audit every relevant backup shader against the audited native template."""
import json
from pathlib import Path
import UnityPy
from prepare_monster_recovery import ROOT, WS, TEMPLATE
from backup_shader_compatibility import validate_shader_mapping,render_signature

def audit():
    target=next(o.read_typetree() for o in UnityPy.load(str(TEMPLATE)).objects if o.type.name=='Shader')
    idx=json.loads((ROOT/'docs/resource-audit/new-backup/新备份资源索引.json').read_text())
    source_ids={a['source'] for a in idx['assets'] if a['type']=='GameObject' and a['name'].startswith('ast_')}
    rows=[]
    for sid in sorted(source_ids):
        origin=idx['sources'][sid];path=WS/'resources/unpacked'/origin['path']
        for obj in UnityPy.load(str(path)).objects:
            if obj.type.name!='Shader':continue
            tree=obj.read_typetree();row=dict(source=origin['path'],source_sha256=origin['sha256'],path_id=obj.path_id,shader=tree.get('m_Name'),signature=render_signature(tree))
            try:row.update(validate_shader_mapping(tree,target));row['status']='render_state_compatible'
            except ValueError as exc:row.update(status='blocked',error=str(exc))
            rows.append(row)
    report=dict(native_template=str(TEMPLATE.relative_to(WS)),target_signature=render_signature(target),rows=rows)
    (ROOT/'docs/resource-audit/new-backup/Shader兼容审计.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    from collections import Counter
    print(Counter(r['status'] for r in rows));print(Counter(r['shader'] for r in rows))
if __name__=='__main__':audit()
