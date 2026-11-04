import sys
sys.path.insert(0,'scripts')
from validate_wolf_cpu_skin import matrix
import prepare_monster_recovery as p
import numpy as np,UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
for path in [p.TEMPLATE,p.WOLF_SOURCE,p.BACKUP/'550_ms01_wolf_f_01.unity3d']:
 env=UnityPy.load(str(path));objs={o.path_id:o for o in env.objects};ts={i:o.read_typetree() for i,o in objs.items() if o.type.name=='Transform'};cache={}
 def world(i):
  if not i:return np.eye(4)
  if i not in cache:cache[i]=world(ts[i]['m_Father']['m_PathID'])@matrix(ts[i])
  return cache[i]
 for i,o in objs.items():
  if o.type.name!='SkinnedMeshRenderer':continue
  r=o.read_typetree();mo=objs[r['m_Mesh']['m_PathID']];m=mo.read_typetree()
  if mo.assets_file.header.version>9:
   handler=MeshHandler(mo.read());handler.process();vs=np.array(handler.m_Vertices)
  else:
   import struct
   vd=m['m_VertexData'];vs=np.array([struct.unpack_from('<3f',bytes(vd['m_DataSize']),j*vd['m_Streams[0]']['stride']) for j in range(vd['m_VertexCount'])])
  vs=np.column_stack((vs,np.ones(len(vs))));rt=next(j for j,t in ts.items() if t['m_GameObject']==r['m_GameObject']);ms=[]
  for b,bp in zip(r['m_Bones'],m['m_BindPose']):ms.append(np.linalg.inv(world(rt))@world(b['m_PathID'])@np.array([[bp[f'e{a}{c}'] for c in range(4)] for a in range(4)]))
  result=np.zeros_like(vs)
  for j,ws in enumerate(m['m_Skin']):
   for k in range(4):result[j]+=ws[f'weight[{k}]']*(ms[ws[f'boneIndex[{k}]']]@vs[j])
  print(path.name,i,'maxerr',np.linalg.norm(result[:,:3]-vs[:,:3],axis=1).max(),'renderer transform',ts[rt]['m_LocalPosition'],ts[rt]['m_LocalRotation'])
