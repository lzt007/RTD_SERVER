CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT UNIQUE NOT NULL,
    state TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, player_id INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    FOREIGN KEY(player_id) REFERENCES players(id));


CREATE TABLE quest_runs (
    run_id TEXT PRIMARY KEY, player_id INTEGER NOT NULL REFERENCES players(id),
    quest_id INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','cleared','abandoned')),
    snapshot TEXT NOT NULL, order_result TEXT NOT NULL,
    created_at INTEGER NOT NULL, completed_at INTEGER);
CREATE UNIQUE INDEX one_active_run ON quest_runs(player_id) WHERE status='active';
CREATE TABLE operation_receipts (
    run_id TEXT NOT NULL REFERENCES quest_runs(run_id), operation TEXT NOT NULL,
    fingerprint TEXT NOT NULL, result TEXT NOT NULL,
    PRIMARY KEY(run_id,operation));
