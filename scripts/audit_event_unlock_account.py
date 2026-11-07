"""Read-only, sanitized settlement evidence for the observed test account.

Only the userId from private ADB observations selects the account. Account IDs,
credentials, sessions and other players are never included in the output.
"""
import argparse
import datetime as dt
import json
import hashlib
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--quest', type=int, default=20710)
    parser.add_argument('--event', type=int, default=100001)
    parser.add_argument('--http-log', type=Path, help='Optional actual API request log, filtered to this observed account')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observed = json.loads(args.observations.read_text())
    user = observed.get('userId')
    if type(user) is not int or user <= 0:
        raise ValueError('An observed logged-in test account is required')
    config = json.loads((args.project / 'rtd.config.json').read_text())
    master_root = args.project / config['paths']['master_data']
    master = json.loads((master_root / 'QUEST_MASTER.json').read_text())
    quest = next(q for q in master['result'][0]['data_list'] if q['id'] == args.quest)
    with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT state FROM players WHERE id=?', (user,)).fetchone()
        if row is None:
            raise ValueError('Observed account does not belong to selected database')
        state = json.loads(row[0])
        runs = db.execute('SELECT status FROM quest_runs WHERE player_id=? AND quest_id=? ORDER BY rowid DESC LIMIT 1',
                          (user, args.quest)).fetchone()
        receipt = db.execute('SELECT r.operation,r.result FROM operation_receipts r JOIN quest_runs q USING(run_id) '
                             'WHERE q.player_id=? AND q.quest_id=? ORDER BY q.rowid DESC LIMIT 1',
                             (user, args.quest)).fetchone()
    flag = quest['flag_no']
    flags = state['player']['quest_clear_flags']
    report = dict(at=dt.datetime.now(dt.timezone.utc).isoformat(), quest_id=args.quest,
                  event_id=args.event, stored_points=state.get('sp_event_points', {}).get(str(args.event), 0),
                  cleared=bool(flags[flag // 8] & (1 << (flag % 8))),
                  latest_run_status=runs[0] if runs else None,
                  active_battle=bool(state.get('battle')), frozen_points='battle_event_points' in state,
                  receipt_operation=receipt[0] if receipt else None,
                  receipt_present=receipt is not None,
                  receipt_result_type=type(json.loads(receipt[1])).__name__ if receipt else None,
                  player_database_modified=False)
    if args.http_log:
        label = hashlib.sha256(('local-player:' + str(user)).encode()).hexdigest()[:12]
        latest = None
        with args.http_log.open(encoding='utf-8') as source:
            for line in source:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get('operation') != 'clear_quest2' or entry.get('state', {}).get('account') != label:
                    continue
                own = [r for r in entry.get('request', {}).get('list', []) if r.get('quest_id') == args.quest]
                if own:
                    latest = dict(at=entry.get('at'), code=entry.get('code'),
                                  reported_points=own[0].get('sp_event_point'))
        report['last_matching_http_clear'] = latest
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
