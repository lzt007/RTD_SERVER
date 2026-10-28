"""Legacy form/GZIP envelope. Do not add transport metadata to strict DTOs."""
import gzip
import json
import urllib.parse
from ..common import ProtocolError, compact


def decode_request(body):
    form = urllib.parse.parse_qs(body.decode('utf-8'), strict_parsing=True)
    request = json.loads(form['request'][0])
    if not isinstance(request, dict):
        raise ProtocolError(8194, 'Expected JSON object')
    return request


def encode_response(response):
    return gzip.compress(compact(response).encode('utf-8'), mtime=0)
