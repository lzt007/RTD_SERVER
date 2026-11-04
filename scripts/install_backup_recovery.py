"""Install audited backup candidates locally; never installs blocked candidates.
Defaults to dry-run. Originals and old entries without new candidates are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]


def validate_candidate(path, expected_hash):
    scripts=str(Path(__file__).resolve().parent)
    if scripts not in sys.path:sys.path.insert(0,scripts)
    from validate_backup_recovery import validate
    return validate(path,expected_hash)


def install(candidate,root=ROOT,dry_run=False):
    candidate=Path(candidate);root=Path(root)
    rows=json.loads((candidate/'validation.json').read_text())
    config=root/'config/monster-recovery.json'
    policy=json.loads(config.read_text());by_model={r['model']:r for r in policy['bundles']}
    selected=[];skipped=[];identities=set()
    for row in rows:
        if row.get('status')!='validated_candidate':continue
        if row.get('source_model') and (not row.get('embedded_motion_roundtrip') or not row.get('shader_mapping')):
            raise ValueError('Missing embedded motion or shader evidence: '+row['model'])
        name=row['bundle']
        if Path(name).name!=name or '\\' in name or not name.endswith('.unity3d'):
            raise ValueError('Unsafe bundle name')
        if row['model']+'.unity3d'!=name:raise ValueError('Model/bundle mismatch')
        if any(row.get(k) for k in ('missing_pointers','missing_motion_paths')):
            raise ValueError('Unresolved candidate dependencies: '+name)
        if not all(row.get(k) for k in ('mesh_roundtrip','texture_roundtrip','retained_object_bytes_unchanged')):
            raise ValueError('Incomplete candidate validation: '+name)
        path=candidate/'bundles'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Candidate hash mismatch: '+name)
        if (root/'resources/bundles'/name).is_file():
            skipped.append(dict(model=row['model'],reason='canonical original exists'));continue
        proof=validate_candidate(path,row['sha256'])
        if proof['internal_file'] in identities:raise ValueError('Duplicate CAB identity')
        identities.add(proof['internal_file'])
        selected.append((row,path));by_model[row['model']]=row
    policy['bundles']=[by_model[k] for k in sorted(by_model)]
    policy['previous_policy']=policy.get('previous_policy',policy.get('policy'))
    policy['policy']='backup-resource-compatibility-v2'
    policy['scope']='Audited original resource gaps: exact-name backup artwork first, same-family inferred artwork second; originals retain priority.'
    policy['backup_revision']='backup-type-motion-closure-v2'
    if not dry_run:
        destination=root/'resources/reconstructed/monsters';(destination/'bundles').mkdir(parents=True,exist_ok=True)
        backup=destination/'before-backup-recovery-manifest.json'
        if not backup.exists():shutil.copy2(config,backup)
        for row,path in selected:
            target=destination/'bundles'/row['bundle']
            prior=destination/'before-backup-recovery-bundles'/row['bundle']
            if target.exists() and not prior.exists():prior.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,prior)
            shutil.copy2(path,target)
        payload=json.dumps(policy,ensure_ascii=False,indent=2)+'\n'
        (destination/'manifest.json').write_text(payload)
        config.write_text(payload)
    return {'dry_run':dry_run,'skipped':skipped,'installed_models':[r['model'] for r,_ in selected],'preserved_models':sorted(set(by_model)-{r['model'] for r,_ in selected})}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=ROOT/'resources/reconstructed/backup-recovery')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(install(args.candidate,dry_run=not args.apply),ensure_ascii=False,indent=2))
