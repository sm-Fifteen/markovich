const sqlite3 = require('sqlite3');

function MarkovichSQLiteBackend(namespace_id) {
	this.db = new sqlite3.Database(`./db/${namespace_id}.db`);
	this.db.serialize();
	
	this.db.run(`
		CREATE TABLE IF NOT EXISTS chain (
			link1 text NOT NULL,
			link2 text NOT NULL, -- Space is used as an end-of-sentence sentinel
			n integer NOT NULL,
			PRIMARY KEY (link1, link2), -- Primary Key requires not null anyway
			CHECK (link1 <> ' ') 
		);
	`);

	this.db.run("CREATE INDEX IF NOT EXISTS chain_link1_idx ON chain (link1);");
	
	this.generate_statement = this.db.prepare(generate_sql);
}

const generate_sql = `
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
`;

MarkovichSQLiteBackend.prototype.generate_from_sentence = function(sentence, split_pattern) {
	let words = sentence.split(new RegExp(split_pattern));
	let first_idx = Math.floor(Math.random()*(words.length - 1));
	let seed = [words[first_idx], words[first_idx+1]];
	
	return new Promise((resolve, reject) => this.generate_statement.all(seed, function(err, rows) {
		if (err) reject(err);
		resolve(rows);
	}));
}

MarkovichSQLiteBackend.prototype.record_sentence = function(sentence, split_pattern) {
	let words = sentence.split(new RegExp(split_pattern));
	let sql_param_list = Array.from(words, () => "(?)").join(', ')
	
	let record_sql = `
		WITH
			words(words) AS (VALUES ${sql_param_list}),
			word_chain(link1, link2, n) AS (SELECT words, lead(words, 1) OVER (), 1 AS n FROM words)
		INSERT INTO chain(link1, link2, n)
			-- link2 would normally be null, but PK constraint disallows that
			SELECT link1, COALESCE(link2, ' ') AS link2, SUM(n) AS n FROM word_chain GROUP BY link1, link2
		ON CONFLICT (link1, link2) DO UPDATE SET n = chain.n + EXCLUDED.n -- Requires PG 9.5+ or SQLite 3.24.0`;

	return new Promise((resolve, reject) => this.db.run(record_sql, words, function(err) {
		if (err) reject(err);
		resolve();
	}));
}

let markov = new MarkovichSQLiteBackend('test_db2');
markov.record_sentence("the world is DOOMED!", "[, ]")
.then(() => markov.generate_from_sentence("Hello world", "[, ]"))
.then(console.log)
.catch(console.error);

