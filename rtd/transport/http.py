import datetime as dt
import http.cookies
import http.server
import pathlib
import threading
import time
import urllib.parse
import uuid

from ..common import ProtocolError, compact
from ..protocol.wire import decode_request, encode_response
from ..diagnostics.logging import redact
from ..storage.identity import database_path_id
from .admin import handle_admin
from .admin_web import serve_admin_web

def handler_for(api, log_path, run_id=None):
    log_lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def admin(self):
            path=urllib.parse.urlsplit(self.path).path
            if path=='/admin/v1' or path.startswith('/admin/v1/'):
                handle_admin(self,api);return True
            return False

        def do_PUT(self):
            if not self.admin():self.send_error(404)

        do_PATCH=do_PUT
        do_DELETE=do_PUT

        def do_GET(self):
            if serve_admin_web(self):return
            if self.admin():return
            if self.path != '/health':
                self.send_error(404)
                return
            body = compact(dict(status='ok',protocol='RTD-2.4.0',
                                master_types=sorted(api.masters),
                                database_path_id=database_path_id(api.store.path),
                                experimental_content=api.experimental_content)).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self):
            if not serve_admin_web(self):self.send_error(404)

        def do_POST(self):
            if self.admin():return
            path = urllib.parse.urlsplit(self.path)
            if not path.path.startswith('/rtd/2.4.0/api/') or not path.path.endswith('.php'):
                self.send_error(404)
                return
            operation = pathlib.PurePosixPath(path.path).stem
            req, response = None, None
            started = time.monotonic()
            request_id = uuid.uuid4().hex
            api.store.local.trace = {}
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024*1024:
                    raise ProtocolError(8194, 'Invalid request length')
                req = decode_request(self.rfile.read(size))
                cookie = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
                token = cookie['RTDSESSID'].value if 'RTDSESSID' in cookie else ''
                user_id = urllib.parse.parse_qs(path.query).get('user_id', [None])[0]
                response = api.call(operation, req, token, user_id)
            except ProtocolError as exc:
                response = dict(code=exc.code, message=exc.message, result=None)
            except (ValueError, KeyError, TypeError, http.cookies.CookieError):
                response = dict(code=8194, message='Malformed request', result=None)
            except Exception:
                import traceback
                traceback.print_exc()
                response = dict(code=8192, message='Internal emulator error', result=None)
            # Native client explicitly decompresses the body. Do not set HTTP Content-Encoding,
            # which could cause the Java transport to decompress it a second time.
            body = encode_response(response)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True
            # Local diagnostic log excludes UUID/session credentials.
            entry = dict(at=dt.datetime.now(dt.timezone.utc).isoformat(), operation=operation,
                         request=redact(req if isinstance(req,dict) else {}),
                         request_id=request_id, duration_ms=round((time.monotonic()-started)*1000,2),
                         state=api.store.local.trace, run_id=run_id,
                         code=response['code'], message=response.get('message'),
                         user_id=(response.get('result') or {}).get('user_id')
                         if isinstance(response.get('result'), dict) else None)
            with log_lock:
                with log_path.open('a', encoding='utf-8') as out:
                    out.write(compact(entry)+'\n')
            print(operation, response['code'], response.get('message', ''), flush=True)

    return Handler


