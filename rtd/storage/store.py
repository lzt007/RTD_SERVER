import contextlib
import json
import pathlib
import secrets
import sqlite3
import threading
import time
import uuid

from ..config import ROOT, STARTERS
from ..common import ProtocolError, compact

class Store:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.local = threading.local()
        from .migration import migrate
        with self.connect() as db:
            migrate(db)
            db.execute('PRAGMA journal_mode=WAL')

    @contextlib.contextmanager
    def connect(self):
        current = getattr(self.local, 'connection', None)
        if current is not None:
            yield current
            return
        db = sqlite3.connect(self.path)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        finally:
            db.close()

    @contextlib.contextmanager
    def transaction(self):
        """One database transaction covers validation, state, costs and receipts."""
        with self.lock:
            if getattr(self.local, 'connection', None) is not None:
                raise RuntimeError('Nested request transaction')
            db = sqlite3.connect(self.path, timeout=30)
            try:
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('BEGIN IMMEDIATE')
                self.local.connection = db
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                self.local.connection = None
                db.close()

    def active_run(self, player_id):
        with self.connect() as db:
            row = db.execute("SELECT run_id FROM quest_runs WHERE player_id=? AND status='active'",
                             (player_id,)).fetchone()
            return row[0] if row else None

    def begin_run(self, state, order_result):
        player_id = state['player']['user_id']
        existing = self.active_run(player_id)
        if existing:
            return existing
        run_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO quest_runs VALUES(?,?,?,?,?,?,?,NULL)',
                       (run_id, player_id, state['battle']['quest_id'], 'active',
                        compact(state['battle']), compact(order_result), int(time.time())))
        return run_id

    def previous_receipt(self, player_id, operation, fingerprint):
        with self.connect() as db:
            row = db.execute('SELECT r.result FROM operation_receipts r JOIN quest_runs q USING(run_id) '
                             'WHERE q.player_id=? AND r.operation=? AND r.fingerprint=? '
                             'ORDER BY q.completed_at DESC,q.rowid DESC LIMIT 1',
                             (player_id, operation, fingerprint)).fetchone()
            return json.loads(row[0]) if row else None

    def previous_order(self, player_id, quest_id):
        with self.connect() as db:
            row = db.execute('SELECT order_result FROM quest_runs WHERE player_id=? AND quest_id=? '
                             'ORDER BY rowid DESC LIMIT 1', (player_id, quest_id)).fetchone()
            return json.loads(row[0]) if row else None

    def finish_run(self, run_id, operation, fingerprint, result):
        with self.connect() as db:
            db.execute('INSERT INTO operation_receipts VALUES(?,?,?,?)',
                       (run_id, operation, fingerprint, compact(result)))
            changed = db.execute("UPDATE quest_runs SET status='cleared',completed_at=? "
                                 "WHERE run_id=? AND status='active'", (int(time.time()), run_id)).rowcount
            if changed != 1:
                raise RuntimeError('Quest run is not active')

    def abandon_run(self, run_id):
        with self.connect() as db:
            changed = db.execute("UPDATE quest_runs SET status='abandoned',completed_at=? "
                                 "WHERE run_id=? AND status='active'", (int(time.time()),run_id)).rowcount
            if changed != 1:
                raise RuntimeError('Quest run is not active')

    def create(self, req):
        try:
            key = str(uuid.UUID(req['uuid']))
            choice = int(req['unit_no'])
        except (KeyError, ValueError, TypeError):
            raise ProtocolError(8194, 'Invalid uuid or starter')
        name = req.get('user_name')
        if not isinstance(name, str) or not name.strip() or len(name) > 32:
            raise ProtocolError(8448, 'Invalid player name')
        if choice not in range(4):
            raise ProtocolError(8194, 'Unknown starter index')
        with self.lock, self.connect() as db:
            row = db.execute('SELECT id,state FROM players WHERE uuid=?', (key,)).fetchone()
            if row:
                # Retry the same registration without resetting its saved progress.
                state = json.loads(row[1])
                if state['starter'] != choice or state['player']['user_name'] != name:
                    raise ProtocolError(37122, 'UUID already registered differently')
                return state
            now = int(time.time())
            cur = db.execute('INSERT INTO players(uuid,state,created_at) VALUES(?,?,?)', (key, '{}', now))
            uid = cur.lastrowid
            player = dict(user_id=uid, user_name=name, action_point=20, max_action_point=20,
                          action_point_recover=now, game_money=0, total_paid_point=0,
                          paid_point=0, free_paid_point=0, friend_point=0, rank=1, exp=0,
                          max_unit=20, max_cost=200, max_friend=10, login_days=0,
                          sequence_login_days=0, system_flag=0, payment_total=0,
                          tutorial_flags=[0]*256, quest_clear_flags=[0]*256,
                          quest_new_flags=[0]*256, quest_challenge_state=[],
                          quest_challenge_reward_state=[])
            units = [dict(instance_id=uid*1000+i+1, user_id=uid, unit_id=unit,
                          member_id=i+1, leader=int(i == 0), level=level, exp=0,
                          bonus_life=0, bonus_attack=0, bonus_heal=0, bonus_limit=0,
                          attribute_exp=0, favorite=0)
                     for i, (unit, level) in enumerate(STARTERS[choice])]
            slots = [u['instance_id'] for u in units] + [0, 0]
            state = dict(starter=choice, player=player, units=units,
                         party=dict(active=0, party=[dict(instanceIds=slots[:]) for _ in range(5)]),
                         unit_collection_flags=[], last_login=None)
            db.execute('UPDATE players SET state=? WHERE id=?', (compact(state), uid))
            return state

    def authenticate(self, key):
        try:
            key = str(uuid.UUID(key))
        except (ValueError, TypeError, AttributeError):
            raise ProtocolError(8195, 'Unknown UUID')
        with self.lock, self.connect() as db:
            row = db.execute('SELECT id,state FROM players WHERE uuid=?', (key,)).fetchone()
            if not row:
                raise ProtocolError(8195, 'Unknown UUID')
            if 'npc_helper_key' in json.loads(row[1]):
                raise ProtocolError(8195, 'Helper accounts cannot authenticate')
            token = secrets.token_hex(24)
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (token, row[0], int(time.time())+86400*30))
            return json.loads(row[1]), token

    def session(self, token, user_id=None):
        with self.connect() as db:
            row = db.execute('SELECT p.id,p.state FROM sessions s JOIN players p ON p.id=s.player_id '
                             'WHERE s.token=? AND s.expires_at>?', (token, int(time.time()))).fetchone()
        if not row:
            raise ProtocolError(8196, 'Authentication required')
        if user_id is not None and str(row[0]) != str(user_id):
            raise ProtocolError(8198, 'Session/player mismatch')
        return json.loads(row[1])

    def save(self, state):
        with self.connect() as db:
            db.execute('UPDATE players SET state=? WHERE id=?',
                       (compact(state), state['player']['user_id']))

    def by_id(self, user_id):
        """Read a local peer inside the current request transaction."""
        with self.connect() as db:
            row=db.execute('SELECT state,created_at FROM players WHERE id=?',(user_id,)).fetchone()
        if row is None:return None
        state=json.loads(row[0]);state.setdefault('created_at',row[1])
        return state


