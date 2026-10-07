# SQL and migrations standard (sources: PostgreSQL docs, OWASP)
- DB-01 Every schema change is a new migration; never edit a committed migration.
- DB-02 Migrations are reversible where the tool supports it, and safe on existing data: add nullable or defaulted columns, backfill, then add constraints.
- DB-03 Never drop or rename a column in the same release that stops using it; deploy code first, then remove.
- DB-04 Index columns used in WHERE, JOIN and ORDER BY on large tables; create indexes concurrently on big Postgres tables.
- DB-05 Foreign keys and NOT NULL/UNIQUE constraints express real rules in the database.
- DB-06 Parameterised queries only; no string-built SQL with user input.
- DB-07 Test the migration on a copy/dev database before applying it anywhere real.
- DB-08 Backup exists before running a migration on real data; rollback steps are known.
- DB-09 Large data changes run in batches, not one long locking transaction.
