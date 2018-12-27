import sqlite3
import random, re

class MarkovichSQLite:
	def __init__(self, conn_string:str):
		MarkovichSQLite.check_sqlite_version()
		
		self.conn = sqlite3.connect(conn_string)
		self.init_db()
		
		# Alternative to using `ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real)`
		self.conn.create_function('random_real', 0, random.random) 

	@staticmethod
	def check_sqlite_version():
		# ON CONFLICT requires SQLite 3.24.0 or PG 9.5+
		# Windowing clauses require SQLite 3.25
		(v_major, v_minor, _) = sqlite3.sqlite_version_info
		assert v_major > 3 or (v_major == 3 and v_minor >= 25), "SQLite v3.25 or greater required"

	def init_db(self) -> None:
		self.conn.execute("""
		CREATE TABLE IF NOT EXISTS chain (
			link1 text NOT NULL,
			link2 text NOT NULL, -- Space is used as an end-of-sentence sentinel
			n integer NOT NULL,
			PRIMARY KEY (link1, link2), -- Primary Key requires not null anyway
			CHECK (link1 <> ' ') 
		);
		""")
		
		self.conn.execute("CREATE INDEX IF NOT EXISTS chain_link1_idx ON chain (link1);")

	def record_and_generate(self, input_string:str):
		chopped_string = re.split(r'[,\s]+', input_string)
		self.record_words(chopped_string)

		idx = random.randrange(len(chopped_string) - 2)
		return self.generate_from_pair(chopped_string[idx], chopped_string[idx+1])

	def record_words(self, chopped_string:list) -> None:
		c = self.conn.cursor()
		
		placeholders = ['(?)'] * len(chopped_string)
		placeholders_str = ','.join(placeholders)

		c.execute(f"""
		WITH
			words(words) AS (VALUES {placeholders_str}),
			word_chain(link1, link2, n) AS (SELECT words, lead(words, 1) OVER (), 1 AS n FROM words)
		INSERT INTO chain(link1, link2, n)
			-- link2 would normally be null, but PK constraint disallows that
			SELECT link1, COALESCE(link2, ' ') AS link2, SUM(n) AS n FROM word_chain GROUP BY link1, link2
		ON CONFLICT (link1, link2) DO UPDATE SET n = chain.n + EXCLUDED.n -- Requires PG 9.5+ or SQLite 3.24.0
		""", chopped_string)

	def generate_from_pair(self, input1:str, input2:str) -> str:
		c = self.conn.cursor()
		
		c.execute("""
		WITH RECURSIVE markov(last_word, current_word, random_const) AS (
			VALUES(?, ?, random_real())
		UNION ALL
			SELECT markov.current_word, (
				-- Weighted word generation
				-- Loosely based on https://stackoverflow.com/a/13040717
				SELECT link2 FROM (
					SELECT link1, link2, n,
					SUM(n) OVER (PARTITION BY link1 ROWS UNBOUNDED PRECEDING) AS rank,
					SUM(n) OVER (PARTITION BY link1) * markov.random_const AS roll
					FROM chain
					WHERE link1 = markov.current_word
				) t WHERE roll <= rank LIMIT 1
			) AS next_word,
			random_real() AS random_const

			FROM markov
			WHERE current_word <> ' '
		) SELECT last_word FROM markov LIMIT 50;
		""", (input1, input2))
		
		word_tuples = c.fetchall()
		words = [word for (word,) in word_tuples]
		return ' '.join(words)
