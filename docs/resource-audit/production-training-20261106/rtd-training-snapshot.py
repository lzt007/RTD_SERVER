import sys,os,json,pathlib,sqlite3,tempfile,subprocess
root=pathlib.Path('/home/RTD_SERVER');sys.path.insert(0,str(root))
pid=subprocess.check_output(['systemctl','show','rtd-api.service','-p','MainPID','--value']).decode().strip()
env=dict(x.split(b'=',1) for x in pathlib.Path('/proc/'+pid+'/environ').read_bytes().split(b'\0') if b'=' in x)
flags={k.decode():v.decode() for k,v in env.items() if k.startswith(b'RTD_') and v in (b'0',b'1')};os.environ.update(flags)
from rtd.config import SETTINGS,path_for
from rtd.services.api import API
from rtd.operations.configuration import is_open
with sqlite3.connect(path_for('database').resolve().as_uri()+'?mode=ro',uri=True) as c: cfg=json.loads(c.execute('select document from runtime_config').fetchone()[0])
with tempfile.TemporaryDirectory() as d:
 api=API(pathlib.Path(d)/'audit.sqlite3')
 ids=set(range(25061,25064))|set(range(25073,25082));qs={q['id']:q for q in api.masters[30]['data_list']};ts={t['id']:t for t in api.masters[21]['data_list']};es={e['id']:e for e in api.masters[20]['data_list']}
 rows=[]
 for qid in sorted(ids):
  q=qs[qid];t=ts[q['enemy_table_id']];eids={v for k,v in t.items() if k.endswith('_set_id') and v};rows.append(dict(quest=q,level=api.levels.get(qid),enemies=[es[e] for e in sorted(eids)],open=any(is_open(e) and any(x['quest_id']==qid for x in e['quests']) for e in cfg['events']),blocked=qid in api.blocked_quests))
 pathlib.Path('/tmp/rtd-training-snapshot.json').write_text(json.dumps(dict(revision=cfg['revision'],flags=flags,rows=rows),ensure_ascii=False))
 print('snapshot',cfg['revision'],len(rows),[(r['quest']['id'],r['quest']['name'],len(r['enemies']),bool(r['level'])) for r in rows])
