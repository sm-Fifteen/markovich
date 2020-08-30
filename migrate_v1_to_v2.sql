-- sqlite3 -echo test_db2.db ".read migrate_v1_to_v2.sql"
PRAGMA foreign_keys = true;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS words_v2(
	word_id INTEGER PRIMARY KEY, -- Implicit ROWID
	word TEXT UNIQUE NOT NULL -- Nulls are never unique
);

CREATE TABLE IF NOT EXISTS chain_v2(
	word_id1 INTEGER NOT NULL,
	word_id2 INTEGER NOT NULL,
	n INTEGER NOT NULL,
	PRIMARY KEY(word_id1,word_id2),
	FOREIGN KEY(word_id1) REFERENCES words_v2(word_id),
	FOREIGN KEY(word_id2) REFERENCES words_v2(word_id)
);

-- End/start of sentence sentinel, the "null word"
-- SQLite will never insert a ROWID of zero on its own, so this is safe
INSERT INTO words_v2(word_id, word) VALUES(0, '') ON CONFLICT DO NOTHING;

INSERT INTO words_v2(word)
	SELECT DISTINCT link1 FROM chain WHERE TRUE
	UNION
	SELECT DISTINCT link2 FROM chain WHERE TRUE
ON CONFLICT(word) DO NOTHING;

INSERT INTO chain_v2(word_id1, word_id2, n)
	SELECT
		(SELECT word_id FROM main.words_v2 WHERE chain.link1 = words_v2.word OR (words_v2.word_id = 0 AND chain.link1 IS ' ')) AS wid1,
		(SELECT word_id FROM main.words_v2 WHERE chain.link2 = words_v2.word OR (words_v2.word_id = 0 AND chain.link2 IS ' ')) AS wid2,
		n
	FROM chain
	WHERE TRUE
ON CONFLICT (word_id1, word_id2) DO UPDATE SET n = chain_v2.n + EXCLUDED.n;

CREATE INDEX IF NOT EXISTS chain_word_id1_idx ON chain_v2 (word_id1);

--DROP TABLE chain;

COMMIT;
VACUUM;
