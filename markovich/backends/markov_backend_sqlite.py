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

		# aiosqlite does not support FFI functions
		# # Alternative to using `ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real)`
		# self.conn.create_function('random_real', 0, random.random)

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
		CREATE TABLE IF NOT EXISTS chain (
			link1 text NOT NULL,
			link2 text NOT NULL, -- Space is used as an end-of-sentence sentinel
			n integer NOT NULL,
			PRIMARY KEY (link1, link2), -- Primary Key requires not null anyway
			CHECK (link1 <> ' ') 
		);
		""")
		
		await conn.execute("CREATE INDEX IF NOT EXISTS chain_link1_idx ON chain (link1);")

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
			await c.execute("""
			WITH
				words(words) AS (SELECT value FROM json_each(?)),
				word_chain(link1, link2, n) AS (SELECT words, lead(words, 1) OVER (), 1 AS n FROM words)
			INSERT INTO chain(link1, link2, n)
				-- link2 would normally be null, but PK constraint disallows that
				SELECT link1, COALESCE(link2, ' ') AS link2, SUM(n) AS n FROM word_chain GROUP BY link1, link2
			ON CONFLICT (link1, link2) DO UPDATE SET n = chain.n + EXCLUDED.n
			""", (json_encoded,))

	async def generate_sentence(self, starting_word:str, word_limit: int) -> Optional[str]:
		if word_limit < 0: return None

		async with self.conn.cursor() as c:
			await c.execute("""
			WITH RECURSIVE markov(last_word, current_word, random_const) AS (
				VALUES(NULL, ?, ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real))
			UNION ALL
				SELECT markov.current_word, (
					SELECT link2 FROM (
						SELECT link1, link2, n,
						SUM(n) OVER (PARTITION BY link1 ROWS UNBOUNDED PRECEDING) AS rank,
						SUM(n) OVER (PARTITION BY link1) * markov.random_const AS roll
						FROM chain
						WHERE link1 = markov.current_word
					) t WHERE roll <= rank LIMIT 1
				) AS next_word,
				ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real) AS random_const

				FROM markov
				WHERE current_word <> ' '
			)
			-- Initial pair (NULL, starting_word) needs to be removed
			SELECT last_word FROM markov WHERE last_word IS NOT NULL LIMIT ?;
			""", (starting_word, word_limit))
			
			word_tuples = await c.fetchall()
			words = [word for (word,) in word_tuples]
			return ' '.join(words)

	def bulk_learn(self, sentences):
		raise NotImplementedError()
