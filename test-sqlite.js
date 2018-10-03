const sqlite3 = require('sqlite3').verbose();

let db = new sqlite3.Database('./test_db.db', (err) => console.log(err));

db.run(`
CREATE TABLE IF NOT EXISTS chain (
	link1 text NOT NULL,
	link2 text NOT NULL, -- Space is used as an end-of-sentence sentinel
	n integer NOT NULL,
	PRIMARY KEY (link1, link2), -- Primary Key requires not null anyway
	CHECK (link1 <> ' ') 
);
`)

db.run("CREATE INDEX IF NOT EXISTS chain_link1_idx ON chain (link1);")

let generate_statement = db.prepare(`
WITH RECURSIVE markov(last_word, current_word, random_const) AS (
	-- Can't use subquery CTEs for random constants, since, in SQLite,
	-- they end up being evaluated once for the entire markov chain
	VALUES(?, ?, ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real))
UNION ALL
	-- Can't do correlated subqueries/lateral joins in sqlite, but...
	-- ...I guess a one-row, one-col subquery inside a SELECT works! ¯\_(ツ)_/¯
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
	ABS(random()) / CAST(0x7FFFFFFFFFFFFFFF AS real) AS random_const
	
	FROM markov
	WHERE current_word <> ' '
) SELECT * FROM markov LIMIT 25;
`);

generate_statement.all(["hello", "world"], function(err, rows) {
		if(err) console.error(err);
		console.log(rows);
});
