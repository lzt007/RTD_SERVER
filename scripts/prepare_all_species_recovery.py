"""Resume per-family reconstruction without touching production or original bundles.
Run the independent candidate tests before using install_species_recovery.py.
"""
import argparse,json
from prepare_species_recovery import ROOT,build,family

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--family',action='append');parser.add_argument('--rebuild',action='store_true');args=parser.parse_args()
 raw=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list']
 audit=json.loads((ROOT/'docs/resource-audit/全种族APK内置扫描.json').read_text())
 native={o['name'].removeprefix('ast_') for o in audit[0]['objects'] if o['type']=='GameObject'}
 families=args.family or sorted({family(r['model']) for r in raw}-{'' ,'ms00_floor','ms00_wall','ms00_kaidan','ms01_squ'})
 for species in families:
  directory=ROOT/'resources/reconstructed/species-recovery'/species
  valid=set() if args.rebuild else {r['model'] for r in json.loads((directory/'validation.json').read_text())} if (directory/'validation.json').exists() else set()
  missing={r['model'] for r in raw if family(r['model'])==species}-native-valid
  missing={m for m in missing if not (ROOT/'resources/bundles'/(m+'.unity3d')).exists()}
  if not missing:continue
  if species=='ms01_sla':
   from prepare_slime_species_recovery import build_slimes
   build_slimes()
   valid={r['model'] for r in json.loads((directory/'validation.json').read_text())}
   missing-=valid
  if missing:build(species,sorted(missing))
if __name__=='__main__':main()
