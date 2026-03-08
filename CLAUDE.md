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
jupyter notebook "notebooks/Frogwatch v3.ipynb"
```
The notebook connects to Postgres (`postgresql+psycopg2://pollard@localhost:5432/frogwatch`), loads observations, and renders a Bokeh interactive dashboard inline via `show(update_display)`.

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

### `notebooks/Frogwatch v3.ipynb` — current dashboard (notebook)
Self-contained Jupyter notebook that is the active version of the dashboard. It:
1. Loads `persons`, `stations`, `observations` from Postgres via SQLAlchemy.
2. Normalizes species names (strips parenthetical subspecies) and reassigns a set of duplicate/aliased SMR station IDs to canonical ones.
3. Denormalizes into a flat DataFrame (`smr_observations`) filtered to SMR stations and year ≥ 2010.
4. Defines `update_display(doc)` which builds the full Bokeh app (GMap station map, species/observer/observation tables, year-month and month histograms) with cross-filtering via `ColumnDataSource.selected.on_change` callbacks.
5. Calls `show(update_display)` to embed the Bokeh server inline.

### `src/dashboard/` — Bokeh web dashboard (Heroku/server version)
- `main.py`: Bokeh server app. Builds interactive map + tables + histograms with cross-filtering callbacks.
- `data.py`: `load_observations()` — reads from DB, denormalizes persons/stations/observations into a flat DataFrame, filters to SMR and year ≥ 2010.
- `models.py`, `db_sqlite.py`, `db_postgres.py`: Copies of the shared types/DB code (duplication is a known issue during refactor).

### Data flow
```
Fieldscope API → frogwatch.py → models → DB (SQLite or Postgres)
                                              ↓
                                     dashboard/data.py
                                              ↓
                                     Bokeh server (main.py)
```

### Database
- Configured via `DATABASE_URL` env var (Postgres) or a local `.db` file (SQLite).
- Tables: `persons`, `stations`, `observations`.
- Inserts are idempotent — existing rows are skipped by checking `fs_id`.

### Deployment
- `Procfile` + `runtime.txt` target Heroku.
- Use `heroku pg:pull` / `heroku pg:push` to sync the Postgres database.
- After loading data, prune unrelated persons/stations to stay under Heroku's 10,000-row free tier limit.
