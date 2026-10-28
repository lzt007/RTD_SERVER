"""Relocated process-level smoke test; only creates build/smoke-* and ephemeral services."""
import datetime,hashlib,json,shutil,socket,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    target=ROOT/'build'/('smoke-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    target.mkdir(parents=True)
    shutil.copytree(ROOT/'rtd',target/'rtd',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'config',target/'config')
    for name in ('master-data','level-data','startup'):
        shutil.copytree(ROOT/'resources'/name,target/'resources'/name)
    for name,source in [('bundles',next((ROOT/'resources/bundles').glob('*.unity3d'))),('unit-icons',ROOT/'resources/unit-icons/13.png')]:
        destination=target/'resources'/name/source.name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    cache=next((ROOT/'resources/cache/Shared').glob('*/CustomAssetBundle-*'))
    destination=target/'resources/cache/Shared'/cache.parent.name/cache.name;destination.parent.mkdir(parents=True);shutil.copy2(cache,destination)
    settings=json.loads((ROOT/'rtd.config.json').read_text(encoding='utf-8'))
    api_port,resource_port=port(),port()
    while resource_port==api_port:resource_port=port()
    assert api_port not in (18765,18766,18767) and resource_port not in (18765,18766,18767)
    settings['api'].update(host='127.0.0.1',port=api_port)
    settings['resources'].update(host='127.0.0.1',port=resource_port,public_base_url=f'http://127.0.0.1:{resource_port}')
    settings['paths']['database']='data/smoke.sqlite3'
    (target/'rtd.config.json').write_text(json.dumps(settings),encoding='utf-8')
    processes=[];files=[];results=[]
    try:
        for module in ('rtd','rtd.resources'):
            output=(target/(module.replace('.','-')+'.log')).open('w',encoding='utf-8');files.append(output)
            processes.append(subprocess.Popen([sys.executable,'-m',module],cwd=target,stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
        def fetch(port,path):
            with urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=3) as r:
                assert r.status==200
                return r.read()
        for service_port,path in ((api_port,'/health'),(resource_port,'/rtd/local-notice')):
            deadline=time.monotonic()+30
            while True:
                try:fetch(service_port,path);break
                except (OSError,TimeoutError):
                    if any(p.poll() is not None for p in processes) or time.monotonic()>deadline:raise
                    time.sleep(.1)
        health=json.loads(fetch(api_port,'/health'));assert health['status']=='ok'
        assert b'admin.js' in fetch(api_port,'/admin/')
        assert json.loads(fetch(api_port,'/admin/v1/config'))
        assert fetch(api_port,'/admin/assets/unit-icons/13.png')==(target/'resources/unit-icons/13.png').read_bytes()
        common=json.loads(fetch(resource_port,'/rtd/local/common-text4.json'))
        assert common['info']==f'http://127.0.0.1:{resource_port}/rtd/local-notice'
        bundle=next((target/'resources/bundles').glob('*.unity3d'))
        assert fetch(resource_port,'/Android/V1/'+bundle.name)==bundle.read_bytes()
        assert fetch(resource_port,'/cache/Shared/'+cache.parent.name+'/'+cache.name)==cache.read_bytes()
        assert (target/'data/smoke.sqlite3').is_file()
        results=['health','admin page','admin API','unit icon','configured common-text notice URL','bundle bytes','original raw cache bytes','configured new database']
        summary={'status':'passed','checks':results,'api_port':api_port,'resource_port':resource_port,'database':str(target/'data/smoke.sqlite3'),'project':str(target)}
        (target/'result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps(summary,indent=2))
    finally:
        for process in processes:
            if process.poll() is None:process.terminate()
        for process in processes:process.wait(timeout=10)
        for output in files:output.close()
if __name__=='__main__':main()
