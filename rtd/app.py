import argparse
import json
import http.cookies
import http.server
import pathlib

from .config import ROOT, SETTINGS, path_for
from .services.api import API
from .transport.http import handler_for

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=SETTINGS['api']['port'])
    parser.add_argument('--database', type=pathlib.Path, default=path_for('database'))
    parser.add_argument('--run-id', help='Diagnostic client replay correlation; never sent in DTOs')
    parser.add_argument('--host', default=SETTINGS['api']['host'])
    args = parser.parse_args()
    if not args.database.is_absolute(): args.database=ROOT/args.database
    api = API(args.database)
    log = path_for('request_log')
    log.parent.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer((args.host, args.port), handler_for(api, log, args.run_id))
    print(f'RTD API http://{args.host}:{args.port} database={args.database}', flush=True)
    if api.visual_recovery:
        print('LOCAL VISUAL SUBSTITUTE '+json.dumps(api.visual_recovery, sort_keys=True), flush=True)
    server.serve_forever()


