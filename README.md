Markovich
=========

An all-SQL (but not pure SQL), multi-tenant Markov chain implementation using SQLite.

Quick-start
-----------

*Note that this requires you to have SQLite 3.27 or later.*

Run in command-line mode, in a test database :
```
python -m markovich
```

Run as a Discord/IRC chatbot :
```
pip install -r requirements.txt
cp ./config.def.json ./config.json
python -m markovich ./config.json
```

An all-SQL Markov chain? Is it really a good idea?
--------------------------------------------------
If you're going to rely on a database in the first place, this
eleminates all round-trip time you would normally have to deal
with. It's certainly not as fast as a Markov chain could be,
since doing weighted word selection through windowing functions
is much slower than precalculating the probabilities on insertion
and operations occuring on disk add a certain amount of latency,
but the response times are acceptable for a chatbot like this.

The worst cases I've observed were around 3 seconds on a 500MB
database file generated from 10 years of forum archive data.

Why use SQLite and not PostgreSQL/MariaDB/MySQL?
------------------------------------------------
SQLite had all of the features I needed to make this work
and had the advantage of making it seamless to create and
connect to multiple databases at the same time, which
was a huge plus to make this multi-tenant. I tried with
PostgreSQL at first and ran into a wall when attempting
to keep separate instaces of word tables per
IRC channel/Discord server (partial indexes on a discriminating
column, declarative partitions with one partitions per domain
being attached on the fly, creating schemas for each tenant;
all of these proved tricky to implement).

What do you mean when you say "Not pure SQL?"
---------------------------------------------
The two big SQL queries used for learning and sentence building
respectively make use of a number of tricks that aren't part of
ISO/CEI 9075 (the standard for SQL), which means this most likely
wouldn't be seamlessly portable to other DBMS. Namely :

* Sentence generation
	* ISO 9075 has no `random()` function as part of the spec and
	SQLite's `random()` generates random int64, not floats between
	0.0 and 1.0 as is the case elsewhere. I use SQLite's FFI to
	make Python's `random()` function directly available in SQL
	as `random_real()` instead.

* Learning
	* String splitting isn't easy to do with most DBMS
	(PostgresSQL is an exception, though), so sentences are
	split in Python and passed as a list of words to the database.
	* While ISO 9075 does have support for array-like objects
	(which they call "collection types"), SQLite does not, so
	the `JSON1` extension is used instead to pass lists of
	words as JSON arrays, which can then be split into rows.
	* `INSERT ... ON CONFLICT` and `SELECT ... LIMIT n` are
	actually Postgres-specific constructs that ended up being
	adopted by SQLite, but the SQL standard favors `MERGE INTO`
	and	`SELECT ... FETCH FIRST n`.
