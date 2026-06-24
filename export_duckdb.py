#!/usr/bin/env python3
"""
Export the Frogwatch Postgres database to a single DuckDB file.

The resulting ``.duckdb`` file is self-contained (all tables, with types),
columnar/compressed, and queryable both server-side and in a marimo/molab
notebook via DuckDB's SQL cells -- no separate database server required.

Usage:
    uv run python export_duckdb.py                      # uses $DATABASE_URL
    uv run python export_duckdb.py -o frogwatch.duckdb
    uv run python export_duckdb.py --db-uri postgresql://user@host:5432/frogwatch

Then, in a molab/marimo notebook, host the file at a public URL and read it:

    import duckdb
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs;")
    con.sql("ATTACH 'https://your-host/frogwatch.duckdb' AS fw (READ_ONLY);")
    con.sql("SELECT * FROM fw.observations LIMIT 5")
"""
import argparse
import getpass
import os
import sys

import duckdb

USERNAME = getpass.getuser()
DEFAULT_DB_URI = f"postgresql://{USERNAME}@localhost:5432/frogwatch"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--db-uri",
        default=os.getenv("DATABASE_URL", DEFAULT_DB_URI),
        help="Postgres connection URI (default: $DATABASE_URL or the local frogwatch DB).",
    )
    parser.add_argument(
        "-o", "--output",
        default="frogwatch.duckdb",
        help="Path for the output DuckDB file (default: frogwatch.duckdb).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def normalize_pg_uri(uri: str) -> str:
    """DuckDB's postgres extension wants a plain libpq URI, not a SQLAlchemy
    dialect string like ``postgresql+psycopg2://``."""
    return uri.replace("postgresql+psycopg2://", "postgresql://", 1)


def main():
    args = parse_args()

    if os.path.exists(args.output):
        if not args.overwrite:
            sys.exit(
                f"Refusing to overwrite existing {args.output!r} "
                f"(pass --overwrite to replace it)."
            )
        os.remove(args.output)

    pg_uri = normalize_pg_uri(args.db_uri)

    # ATTACH does not accept bound parameters, so inline the URI (single quotes
    # doubled to escape). The URI is operator-supplied, not untrusted input.
    pg_literal = pg_uri.replace("'", "''")

    con = duckdb.connect(args.output)
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(f"ATTACH '{pg_literal}' AS pg (TYPE postgres, READ_ONLY)")

    # Copy every public table from Postgres into the DuckDB file.
    tables = [row[0] for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = 'pg' AND table_schema = 'public'
        ORDER BY table_name
        """
    ).fetchall()]

    if not tables:
        sys.exit("No tables found in the attached Postgres database.")

    for table in tables:
        con.execute(f'CREATE TABLE "{table}" AS SELECT * FROM pg.public."{table}"')
        row = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
        count = row[0] if row else 0
        print(f"  {table:<16} {count:>8,} rows")

    con.execute("DETACH pg")
    con.close()

    size_mb = os.path.getsize(args.output) / 1_000_000
    print(f"\nWrote {len(tables)} table(s) to {args.output} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
