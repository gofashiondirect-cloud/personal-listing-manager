# SQL and migrations standard (sources: PostgreSQL docs, OWASP)
- Every schema change is a new migration; never edit a committed migration.
- Migrations are reversible where the tool supports it, and safe on existing data: add nullable or defaulted columns, backfill, then add constraints.
- Never drop or rename a column in the same release that stops using it; deploy code first, then remove.
- Index columns used in WHERE, JOIN and ORDER BY on large tables; create indexes concurrently on big Postgres tables.
- Foreign keys and NOT NULL/UNIQUE constraints express real rules in the database.
- Parameterised queries only; no string-built SQL with user input.
- Test the migration on a copy/dev database before applying it anywhere real.
