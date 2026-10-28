"""Real isolated loopback HTTP contracts; never touches the running resource service."""
import contextlib,hashlib,http.client,json,pathlib,socket,tempfile,threading,time,unittest
from html.parser import HTMLParser
from unittest.mock import patch
from rtd import resources as bundles
ROOT=pathlib.Path(__file__).resolve().parents[1]
NOTICE='/rtd/local-notice';COMMON='/rtd/local/common-text4.json';NOTICE_URL=bundles.content_for.__globals__['NOTICE_URL']
FIXTURE=ROOT/'resources/startup/common-text-original.json'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.tags=[];self.attrs=[]
    def handle_starttag(self,tag,attrs):self.tags.append(tag);self.attrs.extend(attrs)
class StartupContentHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='rtd local content ');cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=pathlib.Path(cls.temp.name);cls.payload=b'original-bundle\x00'*40000;(cls.folder/'sample.unity3d').write_bytes(cls.payload)
        cls.patcher=patch.object(bundles,'bundle_root',cls.folder);cls.patcher.start();cls.addClassCleanup(cls.patcher.stop)
        class Handler(bundles.Handler):
            post_read_timeout=.1
            def log_message(self,*args):pass
        cls.server=bundles.http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.port=cls.server.server_port;assert cls.port not in (18765,18766)
        cls.thread=threading.Thread(target=lambda:cls.server.serve_forever(poll_interval=.01),daemon=True);cls.thread.start()
        def close():cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
        cls.addClassCleanup(close)
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        try:c.request(method,path,body=body,headers=headers or {});r=c.getresponse();return r.status,dict(r.getheaders()),r.read()
        finally:c.close()
    def raw_post(self,headers,body=b'',half_close=False):
        with socket.create_connection(('127.0.0.1',self.port),timeout=3) as s:
            s.sendall(('POST '+COMMON+' HTTP/1.1\r\nHost: localhost\r\n'+headers+'\r\n\r\n').encode('ascii')+body)
            if half_close:s.shutdown(socket.SHUT_WR)
            r=http.client.HTTPResponse(s);r.begin();return r.status,dict(r.getheaders()),r.read()
    def test_original_fixture_is_byte_exact_four_fields(self):
        p=json.loads(FIXTURE.with_name('common-text-original.provenance.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),p['payload_sha256']);self.assertEqual(p['fixture_sha256'],p['payload_sha256'])
        self.assertEqual(set(json.loads(FIXTURE.read_bytes())),{'app','review','info','home'})
    def test_notice_is_utf8_self_contained_page(self):
        status,h,body=self.request('GET',NOTICE);self.assertEqual(status,200)
        self.assertEqual(h['Content-Type'],'text/html; charset=utf-8');self.assertEqual(int(h['Content-Length']),len(body));self.assertEqual(h['Cache-Control'],'no-store')
        text=body.decode('utf-8');self.assertIn('お知らせ',text);self.assertNotIn('Webpage not available',text)
        page=Page();page.feed(text);self.assertIn('html',page.tags);self.assertNotIn('script',page.tags);self.assertNotIn('iframe',page.tags);self.assertNotIn('base',page.tags)
        self.assertFalse(any(k.lower().startswith('on') or k in ('src','href') for k,v in page.attrs))
    def assert_common(self,method,body=None):
        status,h,result=self.request(method,COMMON,body,{'Content-Type':'application/x-www-form-urlencoded'} if body else None)
        self.assertEqual(status,200);self.assertEqual(h['Content-Type'],'application/json; charset=utf-8');self.assertEqual(int(h['Content-Length']),len(result));self.assertEqual(h['Cache-Control'],'no-store')
        expected=json.loads(FIXTURE.read_bytes());expected['info']=NOTICE_URL;self.assertEqual(json.loads(result),expected)
    def test_get_original_common_text_overrides_only_info(self):self.assert_common('GET')
    def test_original_form_post_returns_same_common_text(self):self.assert_common('POST',b'g=g')
    def test_bad_post_framing_refuses_promptly_and_closes(self):
        for headers,status in [('Content-Length: 4097',413),('Content-Length: -1',400),('Content-Length: nope',400),('Content-Length: 3,3',400),('Content-Length: 3\r\nContent-Length: 3',400),('Transfer-Encoding: chunked\r\nContent-Length: 3',400),('',411)]:
            with self.subTest(headers=headers):
                started=time.monotonic();code,h,body=self.raw_post(headers);self.assertEqual(code,status);self.assertEqual(h.get('Connection'),'close');self.assertLess(time.monotonic()-started,2)
    def test_stalled_short_body_has_finite_timeout(self):
        started=time.monotonic();code,h,body=self.raw_post('Content-Length: 5',b'g')
        self.assertEqual(code,408);self.assertEqual(h.get('Connection'),'close');self.assertLess(time.monotonic()-started,2)
    def test_trickle_body_has_overall_deadline(self):
        with socket.create_connection(('127.0.0.1',self.port),timeout=3) as s:
            s.sendall(('POST '+COMMON+' HTTP/1.1\r\nHost: localhost\r\nContent-Length: 8\r\n\r\na').encode('ascii'))
            stop=threading.Event()
            def trickle():
                for _ in range(7):
                    if stop.wait(.06):return
                    try:s.sendall(b'a')
                    except OSError:return
            thread=threading.Thread(target=trickle,daemon=True);thread.start();started=time.monotonic()
            try:
                response=http.client.HTTPResponse(s);response.begin();response.read()
                self.assertEqual(response.status,408);self.assertEqual(response.getheader('Connection'),'close');self.assertLess(time.monotonic()-started,.3)
            finally:stop.set();thread.join(timeout=1)
    def test_eof_short_body_is_rejected(self):
        code,h,body=self.raw_post('Content-Length: 5',b'g',half_close=True);self.assertEqual(code,400);self.assertEqual(h.get('Connection'),'close')
    def test_existing_original_bundle_stream_unchanged(self):
        code,h,body=self.request('GET','/cache/sample.unity3d?v=1');self.assertEqual(code,200);self.assertEqual(h['Content-Type'],'application/octet-stream');self.assertEqual(body,self.payload)
    def test_unknown_routes_remain_refused(self):
        self.assertEqual(self.request('GET','/not-a-page')[0],404);self.assertEqual(self.request('POST','/not-a-page',b'g=g')[0],404)
if __name__=='__main__':unittest.main()
