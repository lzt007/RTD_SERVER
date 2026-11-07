"""Audit actual deployment point generation without touching player state.

Run with the deployment's reconstruction environment. --database is required:
never silently substitute the development database for the production schedule.
Only runtime_config is read from it; API initialization uses disposable SQLite.
Outputs contain quest IDs and point quantities, not accounts or endpoints.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import random
import sqlite3
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve()))
    from rtd.operations.configuration import is_open
    from rtd.services.api import API
    from rtd.services.battle_generation import generate_enemies
    from rtd.policies.event_points import freeze

    with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        document = json.loads(db.execute('SELECT document FROM runtime_config WHERE id=1').fetchone()[0])
    now = dt.datetime.now(dt.timezone.utc)
    events = [event for event in document['events'] if is_open(event, now.timestamp())]
    results = []
    with tempfile.TemporaryDirectory(prefix='rtd-point-audit-') as folder:
        api = API(Path(folder) / 'audit.sqlite3')
        quests = {q['id']: q for q in api.masters[30]['data_list']}
        tables = {t['id']: t for t in api.masters[21]['data_list']}
        drops = {d['id']: d for d in api.masters[22]['data_list']}
        enemies = {e['id']: e for e in api.masters[20]['data_list']}
        registered = {e['sp_event_id'] for e in api.masters[34]['data_list']}
        for event in events:
            for rule in event['quests']:
                qid = rule['quest_id']
                quest = quests[qid]
                if not (quest.get('sp_event_id') in registered or quest.get('open_sp_event_id') in registered):
                    continue
                row = dict(quest_id=qid, event_id=quest.get('sp_event_id', 0),
                           threshold=quest.get('open_sp_event_point', 0))
                try:
                    generated = generate_enemies(tables[quest['enemy_table_id']], api.levels[qid],
                        drops, rng=random.Random(qid), event_id=quest.get('sp_event_id', 0),
                        drop_overrides={r['drop_data_id']: r for r in rule['drops']},
                        enemy_masters=enemies)
                    snapshot = freeze(quest, generated, registered)
                    row.update(maximum=snapshot['maximum'], positive_enemies=sum(
                        bool(e['flag'] and e['sp_event_point'] > 0) for e in generated),
                        enemy_points=sorted({(e['enemy_set_id'], e['sp_event_point'])
                                             for e in generated if e['flag']}))
                    # A registered point-producing open quest must offer points.
                    row['ok'] = quest.get('sp_event_id') not in registered or snapshot['maximum'] > 0
                except Exception as error:
                    row.update(ok=False, error_type=type(error).__name__)
                results.append(row)
    sources = {eid: any(r['event_id'] == eid and r['threshold'] == 0 and r.get('maximum', 0) > 0 for r in results)
               for eid in sorted({r['event_id'] for r in results if r['event_id']})}
    report = dict(zero_point_entry_in_open_schedule=sources, at=now.isoformat(), revision=document['revision'],
                  open_groups=len(events), open_quests=sum(len(e['quests']) for e in events),
                  point_quests=results, ok=bool(results) and all(r['ok'] for r in results),
                  player_database_modified=False,
                  limitation='Deterministic generation audit, not actual kills or Android acceptance')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write('\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
