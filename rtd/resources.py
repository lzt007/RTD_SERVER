"""Serve recovered original bundles on loopback for adb reverse experiments."""
import pathlib,urllib.parse,http.server,json,datetime,argparse,re,socket,time
from .startup_content import COMMON_TEXT_PATH, content_for
from rtd.config import SETTINGS, path_for
bundle_root=path_for('bundles')
cache_root=path_for('cache')
version_root=bundle_root.parent/'resource-versions'
from .resource_catalog import load_snapshot, resolve_snapshot
import threading
_snapshot_lock=threading.Lock()
_snapshot_cache={}

def current_snapshot():
    path=version_root/'active.json'
    stat=path.stat()
    key=(str(path),stat.st_ino,stat.st_mtime_ns,stat.st_size)
    with _snapshot_lock:
        if _snapshot_cache.get('key')!=key:
            value=load_snapshot(version_root)
            _snapshot_cache.clear();_snapshot_cache.update(key=key,value=value)
        return _snapshot_cache['value']
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    post_read_timeout=5
    def send_local_content(self,content):
        content_type,body=content
        self.send_response(200)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Connection','close')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection=True
    def do_POST(self):
        self.close_connection=True
        path=urllib.parse.urlsplit(self.path).path
        if path == '/resources/v1/resolve':
            self.resolve_resources();return
        if path != COMMON_TEXT_PATH:
            self.send_error(404);return
        lengths=self.headers.get_all('Content-Length',[])
        if self.headers.get_all('Transfer-Encoding',[]):
            self.send_error(400);return
        if not lengths:
            self.send_error(411);return
        if len(lengths)!=1 or not re.fullmatch(r'[0-9]+',lengths[0]):
            self.send_error(400);return
        # Compare bounded strings first; arbitrary large integers need no parsing.
        digits=lengths[0].lstrip('0') or '0'
        if len(digits)>4 or int(digits)>4096:
            self.send_error(413);return
        size=int(digits)
        deadline=time.monotonic()+self.post_read_timeout
        received=0
        try:
            while received<size:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self.send_error(408);return
                self.connection.settimeout(remaining)
                # read1 returns after one underlying receive, so progress cannot
                # reset the total monotonic budget as buffered read(size) did.
                chunk=self.rfile.read1(size-received)
                if not chunk:
                    self.send_error(400);return
                received+=len(chunk)
        except (socket.timeout,TimeoutError):
            self.send_error(408);return
        self.send_local_content(content_for(path))
    def resolve_resources(self):
        lengths=self.headers.get_all('Content-Length',[])
        if self.headers.get_all('Transfer-Encoding',[]) or len(lengths)!=1 or not re.fullmatch(r'[0-9]{1,7}',lengths[0]):
            self.send_error(400);return
        size=int(lengths[0])
        if size>1048576:
            self.send_error(413);return
        deadline=time.monotonic()+self.post_read_timeout
        body=bytearray()
        try:
            while len(body)<size:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError()
                self.connection.settimeout(remaining)
                chunk=self.rfile.read1(size-len(body))
                if not chunk:raise ValueError('Incomplete request')
                body.extend(chunk)
            request=json.loads(body)
            if not isinstance(request,dict) or type(request.get('protocol')) is not int or request['protocol']!=1:
                raise ValueError('Unsupported protocol')
            result=resolve_snapshot(current_snapshot(),request.get('roots'))
        except (socket.timeout,TimeoutError):
            self.send_error(408);return
        except (ValueError,UnicodeError,TypeError,RecursionError):
            self.send_error(400);return
        except (OSError,KeyError):
            self.send_error(503);return
        self.send_local_content(('application/json',json.dumps(result,separators=(',',':')).encode()))

    def do_GET(self):
        content=content_for(urllib.parse.urlsplit(self.path).path)
        if content is not None:
            self.send_local_content(content);return
        path=urllib.parse.urlsplit(self.path).path
        if path.startswith('/resources/v1/'):
            match=re.fullmatch(r'/resources/v1/blobs/([0-9a-f]{64})/([A-Za-z0-9_.-]+[.]unity3d)',path)
            file=version_root/'blobs'/match[1]/match[2] if match else None
            if file is None or not file.is_file():
                self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Length',str(file.stat().st_size))
            self.send_header('Cache-Control','public, max-age=31536000, immutable')
            self.send_header('Connection','close')
            self.end_headers()
            with file.open('rb') as source:
                while chunk:=source.read(256*1024):self.wfile.write(chunk)
            self.close_connection=True;return
        cache=re.fullmatch(r'/cache/Shared/([0-9a-f]{40})/(__info|CustomAssetBundle-[A-Za-z0-9-]+)',path)
        if path.startswith('/cache/Shared/'):
            file=cache_root/cache[1]/cache[2] if cache else None
        else:
            name=pathlib.PurePosixPath(path).name
            file=bundle_root/name if name.endswith('.unity3d') else None
            if file is not None and not file.is_file():
                from .policies.monster_recovery import bundle_file as monster_bundle_file
                file=monster_bundle_file(name)
                if file is None:
                    from .policies.reconstructed_resources import bundle_file
                    file=bundle_file(name)
        if file is None or not file.is_file():
            self.send_error(404);return
        self.send_response(200)
        self.send_header('Content-Type','application/octet-stream')
        self.send_header('Content-Length', str(file.stat().st_size))
        self.send_header('Connection','keep-alive')
        self.end_headers()
        with file.open('rb') as source:
            while chunk:=source.read(256*1024): self.wfile.write(chunk)
        self.wfile.flush()
        self.close_connection=False
    def log_message(self,fmt,*args):
        print(datetime.datetime.now().isoformat(),fmt%args,flush=True)
if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=SETTINGS['resources']['port'])
    parser.add_argument('--host',default=SETTINGS['resources']['host'])
    args=parser.parse_args()
    print(f'Serving original backup bundles on {args.host}:{args.port}',flush=True)
    http.server.ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
