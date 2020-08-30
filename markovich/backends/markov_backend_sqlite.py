import aiosqlite
import random
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Pattern, List, AsyncIterator
from .markov_backend import MarkovBackend

sqlite_db_directory = Path("./db")

@asynccontextmanager
async def open_markov_backend_sqlite(database_path: Path) -> AsyncIterator["MarkovBackendSQLite"]:
	MarkovBackendSQLite.check_sqlite_version()

	file_check = database_path.is_file() or (database_path.parent.is_dir() and not database_path.exists())
	assert file_check, "Cannot open or create {}".format(database_path)

	async with aiosqlite.connect(database_path.__fspath__()) as conn:
		await MarkovBackendSQLite.init_db(conn)

		# Alternative to using `ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real)`
		await conn.create_function('random_real', 0, random.random)

		yield MarkovBackendSQLite(conn)

class MarkovBackendSQLite(MarkovBackend):
	conn: aiosqlite.Connection

	def __init__(self, conn: aiosqlite.Connection):
		self.conn = conn

	@staticmethod
	def check_sqlite_version():
		# ON CONFLICT requires SQLite 3.24.0
		# Windowing clauses require SQLite 3.25
		# Windowing clauses inside correlated subqueries cause segfaults in SQLite 3.25 and 3.26.0
		# Requires the json1 extension, but currently no way to check for that
		current_version = aiosqlite.sqlite_version_info
		minimum_version = (3,27,0)

		assert current_version >= minimum_version, "SQLite {}.{}.{} or greater required (Running on SQLite {}.{}.{})".format(*minimum_version, *current_version)

	@staticmethod
	async def init_db(conn: aiosqlite.Connection) -> None:
		await conn.execute("""
		PRAGMA foreign_keys = true;
		""")

		await conn.execute("""
		CREATE TABLE IF NOT EXISTS words_v2(
			word_id INTEGER PRIMARY KEY, -- Implicit ROWID
			word TEXT UNIQUE NOT NULL -- Nulls are never unique
		);
		""")

		await conn.execute("""
		CREATE TABLE IF NOT EXISTS chain_v2(
			word_id1 INTEGER NOT NULL,
			word_id2 INTEGER NOT NULL,
			n INTEGER NOT NULL,
			PRIMARY KEY(word_id1,word_id2),
			FOREIGN KEY(word_id1) REFERENCES words_v2(word_id),
			FOREIGN KEY(word_id2) REFERENCES words_v2(word_id)
		);
		""")

		await conn.execute("""
		-- End/start of sentence sentinel, the "null word"
		-- SQLite will never insert a ROWID of zero on its own, so this is safe
		INSERT INTO words_v2(word_id, word) VALUES(0, '') ON CONFLICT DO NOTHING;
		""")

		await conn.execute("CREATE INDEX IF NOT EXISTS chain_word_id1_idx ON chain_v2 (word_id1);")
		await conn.commit()

	async def record_and_generate(self, input_string:str, split_pattern: Pattern, word_limit: int) -> Optional[str]:
		chopped_string = split_pattern.split(input_string)
		await self.record_words(chopped_string)

		try:
			starting_word = random.choice(chopped_string)
			return await self.generate_sentence(starting_word, word_limit)
		except IndexError:
			return None

	async def record_words(self, chopped_string:List[str]) -> None:
		# Passing a json text array instead of creating a query with an arbitrary amount of parmeters each time
		# SQLite, unlike pgSQL, doesn't have a function to split strings into tables
		json_encoded = json.dumps(chopped_string)

		async with self.conn.cursor() as c:
			# Insert words
			await c.execute("""
			INSERT INTO words_v2(word)
				SELECT DISTINCT value FROM json_each(?)
				WHERE TRUE -- Avoids parsing ambiguity
			ON CONFLICT(word) DO NOTHING;
			""", (json_encoded,))

			# Update chain
			await c.execute("""
			WITH
				word_list(word) AS (SELECT value FROM json_each(?)),
				word_id_list(word_id) AS (SELECT words_v2.word_id FROM word_list INNER JOIN words_v2 ON (word_list.word = words_v2.word)),
				-- Use ROWID 0 as a sentinel value for the end of chain.
				word_id_chain(link1, link2, n) AS (SELECT word_id, lead(word_id, 1, 0) OVER (), 1 AS n FROM word_id_list)
			INSERT INTO chain_v2(word_id1, word_id2, n)
				SELECT link1, link2, SUM(n) AS n FROM word_id_chain GROUP BY link1, link2
			ON CONFLICT (word_id1, word_id2) DO UPDATE SET n = chain_v2.n + EXCLUDED.n
			""", (json_encoded,))

			# FIXME(sm15): aiosqlite has trouble with concurrent transactions on shared connections.
			# Global commits are acceptable here, but connection pooling would be better.
			# https://github.com/omnilib/aiosqlite/issues/19
			await self.conn.commit()

	async def generate_sentence(self, starting_word:str, word_limit: int) -> Optional[str]:
		if word_limit < 0: return None

		async with self.conn.cursor() as c:
			await c.execute("""
			WITH RECURSIVE markov(prev_id, curr_id, random_const) AS (
				-- Correlated subquery in a VALUES expression
				-- I'm going to hell for this :)
				VALUES(0, (SELECT word_id FROM words_v2 WHERE word = ?), random_real())
			UNION ALL
				SELECT markov.curr_id, (
					SELECT word_id2 FROM (
						SELECT word_id1, word_id2, n,
						SUM(n) OVER (PARTITION BY word_id1 ROWS UNBOUNDED PRECEDING) AS rank,
						SUM(n) OVER (PARTITION BY word_id1) * markov.random_const AS roll
						FROM chain_v2
						WHERE word_id1 = markov.curr_id
					) t WHERE roll <= rank LIMIT 1
				) AS next_id,
				random_real() AS random_const

				FROM markov
				WHERE curr_id <> 0
			)
			
			SELECT words_v2.word FROM markov
			INNER JOIN words_v2 ON prev_id = word_id
			-- Initial pair (0, start_id) needs to be removed
			WHERE prev_id <> 0 LIMIT ?;
			""", (starting_word, word_limit))

			# FIXME(sm15): Use conn pools instead of shared conns for transaction support?
			await self.conn.commit()
			
			word_tuples = await c.fetchall()
			words = [word for (word,) in word_tuples]
			return ' '.join(words)

	def bulk_learn(self, sentences):
		raise NotImplementedError()
