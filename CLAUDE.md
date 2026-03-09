# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                   # Install all dependencies (including dev)
frogwatch --help          # CLI entry point
pylint src/               # Lint
pyright src/              # Type check
black src/                # Format
pytest                    # Run tests
```

**Running the dashboard (notebook — current version):**
```bash
uv run marimo edit notebooks/frogwatch_v3.py
# or as a read-only app:
uv run marimo run notebooks/frogwatch_v3.py
```
The notebook connects to Postgres (`postgresql+psycopg2://pollard@localhost:5432/frogwatch`) via the `DATABASE_URL` env var, loads observations via `dashboard/data.py`, and renders an interactive dashboard using marimo-native reactivity and Altair charts.

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

## Architecture

Two loosely coupled modules live under `src/`:

### `src/frogwatch/` — CLI data downloader
- `frogwatch.py`: Entry point (`main()`). Parses args, fetches from Fieldscope API, inserts into DB or exports CSV.
- `fieldscope.py`: API URL constants, geofence definitions (SMR boundary polygon), and query body builder. Key filter functions: `area_filter()`, `state_filter()`, `chapter_filter()`, `date_filter()`.
- `models.py`: `Person`, `Station`, `Observation` dataclasses.
- `db_sqlite.py` / `db_postgres.py`: Database backends with identical interfaces — `connect()`, `create_tables()`, `update_persons/stations/observations()`.

### `notebooks/frogwatch_v3.py` — current dashboard (marimo notebook)
Marimo notebook that is the active version of the dashboard. It:
1. Loads data via `dashboard/data.py:load_observations()` from Postgres.
2. Displays an Altair scatter map (`mo.ui.altair_chart`) of SMR stations (lat/lon, sized by observation count).
3. Cross-filters a species summary table → observer summary table → observations table using marimo reactive cells (no callbacks needed).
4. Renders year-month and month bar histograms (Altair) that update with each filter step.
5. Assembles everything in a final layout cell with `mo.vstack`/`mo.hstack`.

The old `notebooks/Frogwatch v3.ipynb` (Jupyter/Bokeh) is kept for reference.

### `src/dashboard/` — Bokeh web dashboard (Heroku/server version)
- `main.py`: Bokeh server app. Builds interactive map + tables + histograms with cross-filtering callbacks.
- `data.py`: `load_observations()` — reads from DB, denormalizes persons/stations/observations into a flat DataFrame, filters to SMR and year ≥ 2010. Columns are renamed at load time: `fs_id` → `fs_id_station`/`fs_id_observer`, `name` → `name_station`/`name_observer`.
- `models.py`, `db_sqlite.py`, `db_postgres.py`: Copies of the shared types/DB code (duplication is a known issue during refactor).

### Data flow
```
Fieldscope API → frogwatch.py → models → DB (SQLite or Postgres)
                                              ↓
                                     dashboard/data.py
                                              ↓
                                     marimo notebook (frogwatch_v3.py)
```

### Database
- Configured via `DATABASE_URL` env var (Postgres) or a local `.db` file (SQLite).
- Tables: `persons`, `stations`, `observations`.
- Inserts are idempotent — existing rows are skipped by checking `fs_id`.

### Deployment
- `Procfile` + `runtime.txt` target Heroku.
- Use `heroku pg:pull` / `heroku pg:push` to sync the Postgres database.
- After loading data, prune unrelated persons/stations to stay under Heroku's 10,000-row free tier limit.
