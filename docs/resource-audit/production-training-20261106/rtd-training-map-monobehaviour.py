from pathlib import Path
import json,struct
root=Path('/home/workspace/RTD_SERVER');out=root/'docs/resource-audit/production-training-20261106';src=root/'docs/resource-audit/loading-chain/audit.py'
s=src.read_text().split('sys.path.insert(0,str(ROOT))')[0].replace('P=Path(__file__).parent;ROOT=P.parents[2];WS=ROOT.parent',"P=Path('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain');ROOT=P.parents[2];WS=ROOT.parent").replace(" with (P/name).open", " return\n with (P/name).open")
ns={};exec(compile(s,str(src),'exec'),ns)
x=json.loads((out/'map-table-evidence.json').read_text());checks=[]
for row in x['dependency_results']:
 for issue in row['issues']:
  oid=issue['object'];o=ns['O'][oid];reader=ns['object_reader'](oid);raw=reader.get_raw_data();entry=dict(object=oid,type=o['type'],serialized_size=len(raw),raw_hex=raw.hex())
  if o['type']=='MonoBehaviour' and len(raw)>=24:
   # Unity 3.5 base header: PPtr<GameObject>, enabled+alignment,
   # PPtr<MonoScript>, aligned name. Custom fields remain unverified.
   endian=reader.reader.endian
   gofile,gopid,enabled,scriptfile,scriptpid,namelen=struct.unpack(endian+'iiB3xiii',raw[:24])
   refs=[]
   for label,fid,pid in [('GameObject',gofile,gopid),('MonoScript',scriptfile,scriptpid)]:
    found,status=ns['resolve'](o['file'],dict(m_FileID=fid,m_PathID=pid));refs.append(dict(field=label,status=status,targets=[dict(key=i,type=ns['O'][i]['type'],name=ns['O'][i]['name']) for i in found]))
   entry.update(enabled=enabled,name_length=namelen,references=refs,custom_payload_bytes=len(raw)-24,status='base_header_resolved_custom_payload_unverified' if namelen==0 and all(r['status']=='resolved' and all(t['type']==r['field'] for t in r['targets']) for r in refs) else 'review_required')
  checks.append(entry)
x['legacy_monobehaviour_checks']=checks;(out/'map-table-evidence.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print([(r['object'],r.get('status'),r.get('references')) for r in checks])
