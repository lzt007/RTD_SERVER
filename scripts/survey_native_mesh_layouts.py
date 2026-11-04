"""Read-only survey of catalogued original preloads/local bundles; excludes APK data meshes."""
import json,zipfile,collections,struct
from pathlib import Path
import UnityPy
ws=Path(__file__).resolve().parents[2];c=json.loads((ws/'RTD_SERVER/docs/resource-audit/loading-chain/catalog.json').read_text());sids={c['files'][o['file']]['source'] for o in c['objects'].values() if o['type']=='Mesh'}
counts=collections.Counter();layouts=collections.Counter();rows=[];errors=[]
with zipfile.ZipFile(ws/'RTD_CLIENT/inputs/original/game.apk') as z:
 for sid in sorted(sids):
  source=c['sources'][sid];orig=next((a for a in source['origins'] if a['category'] in ['preload90','local_resource','apk_preload']),None)
  if not orig:continue
  p=orig['path']
  try:
   data=z.read(p.split(':',1)[1]) if 'game.apk:' in p else (ws/p).read_bytes();env=UnityPy.load(data)
   for o in env.objects:
    if o.type.name!='Mesh' or o.assets_file.header.version!=9:continue
    t=o.read_typetree();vd=t['m_VertexData'];layouts[str((vd['m_CurrentChannels'],vd['m_Streams[0]']['stride']))]+=1
    for sub in t['m_SubMeshes']:
     counts[sub['isTriStrip']]+=1
     if sub['isTriStrip']!=2:rows.append(dict(name=t['m_Name'],source=p,topology=sub['isTriStrip'],indices=sub['indexCount'],triangles=sub['triangleCount']))
  except Exception as e:errors.append(dict(source=p,error=type(e).__name__))
print(json.dumps(dict(topology_counts=dict(counts),vertex_layouts=dict(layouts),non_strip=rows,errors=errors),indent=2))
