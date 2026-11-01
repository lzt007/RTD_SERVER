-- For verified legacy schema user_version=2 only. Back up before executing.
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS schema_history (version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, installed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO schema_history(version,name,checksum) VALUES(1,'V001__initial_schema.sql','1c0d21c83298c131d04b05ef9b0e2126d7a4b98e866204741bb76424e8b6a173');
INSERT INTO schema_history(version,name,checksum) VALUES(2,'V002__runtime_config.sql','a8d0c631532efc1d04f6e20cfb166caa018a3812ab3651a018e709af93780980');
COMMIT;
