# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                   # Install all dependencies (including dev)
frogwatch --help          # CLI entry point
pylint src/               # Lint
pyright src/              # Type check
black src/                # Format
pytest                    # Run tests (no test suite exists yet)
```

**Running the dashboard (notebook — current version):**
```bash
uv run marimo edit notebooks/frogwatch_v4.py
# or as a read-only app:
uv run marimo run notebooks/frogwatch_v4.py
```
The notebook reads its data source from the `FROGWATCH_DB` env var (default: `postgresql://username@localhost:5432/frogwatch`). It uses a single DuckDB connection that `ATTACH`es the source — a Postgres URI, a SQLite `.db` file, or a `.duckdb` file — and exposes the `persons`/`stations`/`observations` tables as views. Observations are loaded via `dashboard/data.py`, and the dashboard is rendered with marimo-native reactivity and Altair charts.

**Running the dashboard (Heroku server):**
```bash
export BOKEH_ALLOW_WS_ORIGIN=0.0.0.0:5000
heroku local
# Visit http://localhost:5000/
```

**Loading data from Fieldscope:**
```bash
frogwatch --hartshorne --db       # Download Hartshorne chapter data into DB
frogwatch --smr --outfile out.csv # Download SMR observations as CSV
```

**Exporting the database to a single file:**
```bash
uv run python export_duckdb.py    # Postgres ($DATABASE_URL) → frogwatch.duckdb
```
`export_duckdb.py` copies all public tables into one self-contained `.duckdb` file, suitable for serving to a marimo/molab notebook (point `FROGWATCH_DB` at it) without a separate database server.

**Key CLI flags:** `--nj`, `--smr`, `--hartshorne` (geo filters), `--db` / `--db-uri` (database output), `--outfile` (CSV output), `--stations` (download stations separately), `--start-date` / `--end-date` (date range).

## Architecture

Uses `uv` with `uv_build` backend (not setuptools). Python ≥3.9. Two loosely coupled modules live under `src/`:

### `src/frogwatch/` — CLI data downloader
- `frogwatch.py`: Entry point (`main()`). Parses args via `configargparse`, fetches from Fieldscope API, inserts into DB or exports CSV.
- `fieldscope.py`: API URL constants, geofence definitions (SMR boundary polygon), and query body builder. Key filter functions: `area_filter()`, `state_filter()`, `chapter_filter()`, `date_filter()`.
- `models.py`: `Person`, `Station`, `Observation` dataclasses.
- `db_sqlite.py` / `db_postgres.py`: Database backends with identical interfaces — `connect()`, `create_tables()`, `update_persons/stations/observations()`.

### `notebooks/frogwatch_v4.py` — current dashboard (marimo notebook)
Marimo notebook that is the active version of the dashboard. It:
1. Loads data via `dashboard/data.py:load_observations()`, using a DuckDB connection that can `ATTACH` a Postgres URI, a SQLite `.db`, or a `.duckdb` file (selected by the `FROGWATCH_DB` env var).
2. Displays an Altair scatter map (`mo.ui.altair_chart`) of SMR stations (lat/lon, sized by observation count).
3. Cross-filters a species summary table → observer summary table → observations table using marimo reactive cells (no callbacks needed).
4. Renders year-month and month bar histograms (Altair) that update with each filter step.
5. Assembles everything in a final layout cell with `mo.vstack`/`mo.hstack`.

The earlier `notebooks/frogwatch_v3.py` (marimo, Postgres-only via SQLAlchemy/`DATABASE_URL`) and `notebooks/Frogwatch v3.ipynb` (Jupyter/Bokeh) are kept for reference.

### `src/dashboard/` — Bokeh web dashboard (Heroku/server version)
- `main.py`: Bokeh server app. Builds interactive map + tables + histograms with cross-filtering callbacks.
- `data.py`: `load_observations()` — reads from DB, denormalizes persons/stations/observations into a flat DataFrame, filters to SMR and year ≥ 2010. Columns are renamed at load time: `fs_id` → `fs_id_station`/`fs_id_observer`, `name` → `name_station`/`name_observer`. The `client` arg may be a SQLAlchemy engine, a connection-string (Bokeh server passes the URL directly), or a DuckDB connection — DuckDB connections use the native `.df()` reader (the `duckdb` import is optional/guarded so the Heroku deploy works without it).
- `models.py`, `db_sqlite.py`, `db_postgres.py`: Copies of the shared types/DB code (duplication is a known issue during refactor).

### Data flow
```
Fieldscope API → frogwatch.py → models → DB (SQLite or Postgres)
                                              ↓
                          export_duckdb.py (optional: → frogwatch.duckdb)
                                              ↓
                                     dashboard/data.py
                                              ↓
                                     marimo notebook (frogwatch_v4.py)
```

### Database
- The CLI downloader and Bokeh server use `DATABASE_URL` (Postgres) or a local `.db` file (SQLite).
- The `frogwatch_v4.py` notebook uses `FROGWATCH_DB`, which accepts a Postgres URI, a SQLite `.db` file, or a `.duckdb` file (all read through DuckDB).
- Tables: `persons`, `stations`, `observations`.
- Inserts are idempotent — existing rows are skipped by checking `fs_id`.

### Linting
`.pylintrc` disables: `invalid-name`, `bad-continuation`, `bad-indentation`, `bad-whitespace`, `too-few-public-methods`, `logging-fstring-interpolation`, `logging-not-lazy`, `R0801` (duplicate-code).

### Deployment
- `Procfile` + `runtime.txt` target Heroku.
- Use `heroku pg:pull` / `heroku pg:push` to sync the Postgres database.
- After loading data, prune unrelated persons/stations to stay under Heroku's 10,000-row free tier limit.
