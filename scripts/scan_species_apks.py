import UnityPy,zipfile,json,hashlib,pathlib
root=pathlib.Path('/home/workspace');out=[]
for rel in ['RTD_CLIENT/inputs/original/game.apk','resources/ロードラ_7.0.1.0.apk']:
 p=root/rel;result=dict(apk=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),entries=0,objects=[],containers=[],errors=[])
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if n.endswith('/') or not (n.startswith('assets/bin/Data/') or n.endswith('.unity3d')):continue
   if '/Managed/' in n:continue
   b=z.read(n)
   if not (b.startswith((b'UnityFS',b'UnityRaw',b'UnityWeb')) or (len(n.rsplit('/',1)[-1])==32 and all(c in '0123456789abcdef' for c in n.rsplit('/',1)[-1])) or n.rsplit('/',1)[-1] in ('mainData','resources.assets') or 'sharedassets' in n or n.rsplit('/',1)[-1].startswith('level')):continue
   result['entries']+=1
   try:env=UnityPy.load(b)
   except Exception as e:result['errors'].append([n,str(e)[:150]]);continue
   for o in env.objects:
    if o.type.name not in ('GameObject','Mesh','Texture2D','Material'):continue
    try:name=o.read().m_Name
    except:continue
    if 'ms' in name.lower():result['objects'].append(dict(entry=n,name=name,type=o.type.name,path_id=o.path_id))
   for name,obj in env.container.items():
    if 'ms' in name.lower():result['containers'].append(dict(entry=n,name=name,type=obj.type.name,path_id=obj.path_id))
 out.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
(root/'RTD_SERVER/docs/resource-audit/全种族APK内置扫描.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
