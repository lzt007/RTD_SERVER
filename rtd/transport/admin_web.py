"""Serve only the operations UI's explicitly named, packaged static files."""
from pathlib import Path
from ..config import path_for
import re
from urllib.parse import urlsplit

WEB = Path(__file__).resolve().parents[1] / 'web'
ASSETS = {
    '/admin': ('admin.html', 'text/html'),
    '/admin/': ('admin.html', 'text/html'),
    '/admin/assets/admin.css': ('admin.css', 'text/css'),
    '/admin/assets/admin.js': ('admin.js', 'text/javascript'),
    '/admin/assets/admin-model.mjs': ('admin-model.mjs', 'text/javascript'),
}


def serve_admin_web(handler):
    asset = ASSETS.get(urlsplit(handler.path).path)
    icon = re.fullmatch(r'/admin/assets/unit-icons/([1-9][0-9]{0,7})\.png', urlsplit(handler.path).path)
    if asset is None and icon and (path_for('unit_icons') / (icon[1]+'.png')).is_file():
        asset = ('unit-icons/'+icon[1]+'.png', 'image/png')
    if asset is None:
        return False
    filename, content_type = asset
    body = ((path_for('unit_icons') / (icon[1]+'.png')) if icon else WEB / filename).read_bytes()
    handler.send_response(200)
    handler.send_header('Content-Type', content_type if content_type=='image/png' else content_type + '; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('X-Content-Type-Options', 'nosniff')
    handler.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; "
                        "connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    handler.end_headers()
    if handler.command != 'HEAD':
        handler.wfile.write(body)
    return True
