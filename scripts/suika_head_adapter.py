"""Bind the one-piece watermelon body to an identity head bone required by old clips."""
import copy,hashlib
from pathlib import Path
import UnityPy

def adapt(source,output):
 env=UnityPy.load(str(source));objects={o.path_id:o for o in env.objects};root=next(o for o in env.objects if o.type.name=='GameObject' and o.read_typetree()['m_Name']=='ast_ms01_suika_01')
 from prepare_monster_recovery import pointers,WS
 reached=set();todo=[root.path_id]
 while todo:
  i=todo.pop()
  if i in reached:continue
  reached.add(i);todo.extend(p['m_PathID'] for p in pointers(objects[i].read_typetree()) if p['m_PathID'] and not p['m_FileID'])
 main=next(o for i,o in objects.items() if i in reached and o.type.name=='Transform' and objects[o.read_typetree()['m_GameObject']['m_PathID']].read_typetree()['m_Name']=='mn_c_main')
 main_tree=main.read_typetree()
 if main_tree['m_Children']:raise ValueError('Expected one-piece source without child bones')
 gid=max(objects)+1;tid=gid+1;go=copy.copy(objects[main_tree['m_GameObject']['m_PathID']]);go.path_id=gid;tree=go.read_typetree();tree['m_Name']='mn_c_head';tree['m_Component']=[(4,{'m_FileID':0,'m_PathID':tid})];go.save_typetree(tree)
 transform=copy.copy(main);transform.path_id=tid;t=copy.deepcopy(main_tree);t.update(m_GameObject={'m_FileID':0,'m_PathID':gid},m_Father={'m_FileID':0,'m_PathID':main.path_id},m_Children=[],m_LocalPosition={'x':0.,'y':0.,'z':0.},m_LocalRotation={'x':0.,'y':0.,'z':0.,'w':1.},m_LocalScale={'x':1.,'y':1.,'z':1.});transform.save_typetree(t)
 main_tree['m_Children']=[{'m_FileID':0,'m_PathID':tid}];main.save_typetree(main_tree);changed=[]
 for i in reached:
  o=objects[i]
  if o.type.name!='SkinnedMeshRenderer':continue
  tree=o.read_typetree()
  if any(p['m_PathID']!=main.path_id for p in tree['m_Bones']):raise ValueError('Unexpected multi-bone renderer')
  for p in tree['m_Bones']:p['m_PathID']=tid
  o.save_typetree(tree);changed.append(i)
 if not changed:raise ValueError('No real renderer bound to added head')
 sf=main.assets_file;sf.objects[gid]=go;sf.objects[tid]=transform
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(env.file.save())
 return dict(kind='suika-real-head-binding-v1',original_source=str(Path(source).relative_to(WS)),original_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),new_head_transform=tid,renderer_ids=changed,rest_bone_world_matrix_unchanged=True,mesh_weights_bindposes_unchanged=True)
