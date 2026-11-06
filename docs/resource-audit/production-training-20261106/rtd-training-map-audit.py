import pathlib,json,zipfile,hashlib
import xml.etree.ElementTree as ET
import UnityPy
root=pathlib.Path('/home/workspace');p=root/'RTD_SERVER/docs/resource-audit';d=json.loads((p/'loading-chain/catalog.json').read_text());out=p/'production-training-20261106';objects=d['objects'];files=d['files'];sources=d['sources']
for oid,o in objects.items():
 if o['name']!='MapTable' or o['type']!='TextAsset':continue
 f=files[o['file']];source=sources[f['source']];origin=next((a for a in source['origins'] if '/inputs/original/' in a['path']),source['origins'][0]);path=origin['path']
 if '.apk:' in path:
  apk,member=path.split(':',1)
  with zipfile.ZipFile(root/apk) as z:blob=z.read(member)
 else:blob=(root/path).read_bytes()
 env=UnityPy.load(blob)
 for obj in env.objects:
  if obj.type.name=='TextAsset' and obj.read().m_Name=='MapTable':
   text=obj.read().m_Script
   xml=ET.fromstring(text);selected=[]
   for mid in (4,19,31,38):
    entry=xml.find('MapData')[mid];requirements=[]
    for key,tag in [('ground','GroundTexture'),('object','ObjectPrefab'),('sky','SkyPrefab'),('cliff','CliffPrefab'),('under','UnderPrefab')]:
     index=int(entry.attrib[key]);group=xml.find(tag)
     if index>=0:requirements.append(group.attrib['path']+group[index].text)
    selected.append(dict(map_id=mid,requirements=requirements))
   (out/'map-table-evidence.json').write_text(json.dumps(dict(source=path,source_sha256=hashlib.sha256(blob).hexdigest(),text=text,selected_maps=selected),ensure_ascii=False,indent=2));break
 break
