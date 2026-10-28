"""Verify local ignored resources against the tracked distribution inventory."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rtd.config import path_for
inventory=json.loads((ROOT/'config/resource-inventory.json').read_text(encoding='utf-8'))
errors=[]
for row in inventory['files']:
    area,relative=row['path'].split('/',1)
    key={'master-data':'master_data','level-data':'level_data','bundles':'bundles','startup':'startup','unit-icons':'unit_icons','icon-sources':'icon_sources','cache':'cache'}[area]
    if area=='cache':relative=relative.removeprefix('Shared/')
    file=path_for(key)/relative
    if not file.is_file():errors.append('Missing: '+str(file));continue
    if file.stat().st_size!=row['bytes'] or hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:errors.append('Mismatch: '+str(file))
if errors:
    print('\n'.join(errors));raise SystemExit(1)
print(f"Verified {len(inventory['files'])} files, {sum(row['bytes'] for row in inventory['files'])} bytes")
