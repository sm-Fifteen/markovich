const sqlite3 = require('sqlite3');

function MarkovichSQLiteBackend(namespace_id) {
	this.db = new Promise((resolve,reject) => {
		db = new sqlite3.Database(`./db/${namespace_id}.db`, (err) => {
			if (err) reject(err);
			resolve();
		});
	}).then(() => {
		db.serialize();

		db.run(`
			CREATE TABLE IF NOT EXISTS chain (
				link1 text NOT NULL,
				link2 text NOT NULL, -- Space is used as an end-of-sentence sentinel
				n integer NOT NULL,
				PRIMARY KEY (link1, link2), -- Primary Key requires not null anyway
				CHECK (link1 <> ' ') 
			);
		`);

		db.run("CREATE INDEX IF NOT EXISTS chain_link1_idx ON chain (link1);");

		return db;
	});
}

MarkovichSQLiteBackend.prototype.record_and_generate = function(sentence, max_length, split_pattern) {
	if (!split_pattern) split_pattern  = "[,\\s]+";
	if (!sentence) return Promise.resolve([]);
	
	let words = sentence.split(new RegExp(split_pattern));
	
	return this.record_words(words).then((function() {
		// FIXME : I hate having to do this, but SQLite can't split strings itsef
		if (max_length < 1 || words.length < 2) return [];
		
		let seed1_idx = Math.floor(Math.random()*(words.length - 1));
		
		return this.generate_from_pair(words[seed1_idx], words[seed1_idx+1], max_length);
	}).bind(this));
}

MarkovichSQLiteBackend.prototype.generate_from_pair = async function(seed1, seed2, max_length) {
	console.log([seed1, seed2, max_length]);

	let database = await this.db;

	if (!this.generate_statement) this.generate_statement = database.prepare(`
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
		) SELECT last_word FROM markov LIMIT ?;
	`);
	
	if (!seed2) seed2 = ' ';
	if (max_length < 1) return Promise.resolve(null);
	
	return new Promise((resolve, reject) => this.generate_statement.all([seed1, seed2, max_length], function(err, rows) {
		if (err) reject(err);
		console.log(rows);
		resolve(rows.map((row) => row.last_word));
	}));
}

MarkovichSQLiteBackend.prototype.record_words = async function(words) {
	let sql_param_list = Array.from(words, () => "(?)").join(', ');

	let database = await this.db;
	
	let record_sql = `
		WITH
			words(words) AS (VALUES ${sql_param_list}),
			word_chain(link1, link2, n) AS (SELECT words, lead(words, 1) OVER (), 1 AS n FROM words)
		INSERT INTO chain(link1, link2, n)
			-- link2 would normally be null, but PK constraint disallows that
			SELECT link1, COALESCE(link2, ' ') AS link2, SUM(n) AS n FROM word_chain GROUP BY link1, link2
		ON CONFLICT (link1, link2) DO UPDATE SET n = chain.n + EXCLUDED.n -- Requires PG 9.5+ or SQLite 3.24.0`;

	return new Promise((resolve, reject) => database.run(record_sql, words, function(err) {
		if (err) reject(err);
		resolve();
	}));
}

module.exports = MarkovichSQLiteBackend;

/*
let markov = new MarkovichSQLiteBackend('test_db2');
markov.record_and_generate("One", 25)
.then(console.log)
.catch(console.error);
*/
