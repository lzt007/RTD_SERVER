"""Fixed local replacements for the retired notice and common-text service."""
import json
from pathlib import Path
from rtd.config import SETTINGS, path_for

NOTICE_PATH = '/rtd/local-notice'
COMMON_TEXT_PATH = '/rtd/local/common-text4.json'
NOTICE_URL = SETTINGS['resources']['public_base_url'].rstrip('/') + NOTICE_PATH
COMMON_TEXT_URL = SETTINGS['resources']['public_base_url'].rstrip('/') + COMMON_TEXT_PATH
ASSETS = path_for('startup')


def content_for(path):
    if path == NOTICE_PATH:
        return 'text/html; charset=utf-8', (ASSETS / 'local-notice.html').read_bytes()
    if path == COMMON_TEXT_PATH:
        original = json.loads((ASSETS / 'common-text-original.json').read_bytes())
        original['info'] = NOTICE_URL
        return 'application/json; charset=utf-8', json.dumps(original, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return None
