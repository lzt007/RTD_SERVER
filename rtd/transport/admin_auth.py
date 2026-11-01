"""Password gate shared by the management UI and API."""
import base64
import binascii
import hmac
import os
import secrets
from ..config import path_for


def admin_password():
    password = os.environ.get('RTD_ADMIN_PASSWORD')
    if password:
        return password
    target = path_for('database').parent / 'admin-password.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('x', encoding='utf-8') as output:
            output.write(secrets.token_urlsafe(24) + '\n')
    except FileExistsError:
        pass
    password = target.read_text(encoding='utf-8').strip()
    if not password:
        raise ValueError('Admin password file must not be empty')
    return password


def authorize_admin(handler, password):
    try:
        scheme, value = handler.headers.get('Authorization', '').split(' ', 1)
        credentials = base64.b64decode(value, validate=True).decode('utf-8')
        username, supplied = credentials.split(':', 1)
        if (scheme.lower() == 'basic' and username == 'admin'
                and hmac.compare_digest(supplied.encode('utf-8'), password.encode('utf-8'))):
            return True
    except (ValueError, UnicodeError, binascii.Error):
        pass
    body = b'Administrator password required.'
    handler.send_response(401)
    handler.send_header('WWW-Authenticate', 'Basic realm="RTD Admin", charset="UTF-8"')
    handler.send_header('Content-Type', 'text/plain; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Connection', 'close')
    handler.end_headers()
    if handler.command != 'HEAD':
        handler.wfile.write(body)
    handler.close_connection = True
    return False
