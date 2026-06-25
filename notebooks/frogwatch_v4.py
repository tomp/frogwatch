import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## South Mountain Reservation Frogwatch

    This dashboard shows all of the observations made by the South Mountain Reservation Frogwatch team, in a way that makes it easy to drill down on specific frog species, or locations, or observers.

    Select rows in the **Stations**, **Species**, or **Observers** tables to see only observations matching those selections.

    Use the **Clear filters** button to reset everything.
    """)
    return


@app.cell(hide_code=True)
def _(
    clear_btn,
    date_hist,
    end_date,
    mo,
    month_hist,
    obs_table,
    observer_table,
    species_table,
    start_date,
    station_chart,
    station_table,
):
    mo.vstack([
        mo.hstack(
            [
                clear_btn,
                mo.center(mo.hstack([start_date, end_date])),
                mo.md(''),
            ],
            widths='equal',
        ),
        mo.hstack([station_chart, station_table]),
        mo.hstack([species_table, observer_table]),
        date_hist,
        month_hist,
        obs_table,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Data loader
    """)
    return


@app.cell
def _(getpass, os):
    data_source = os.getenv(
        "FROGWATCH_DB",
        f"postgresql://{getpass.getuser()}@localhost:5432/frogwatch",
    )    
    print(f"Data loaded from {data_source}")
    return (data_source,)


@app.cell
def _():
    import os
    import sys
    import math
    import getpass
    from datetime import date

    import altair as alt
    import altair_tiles
    import duckdb
    import pandas as pd
    import marimo as mo
    import xyzservices

    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
    if _src not in sys.path:
        sys.path.insert(0, _src)

    from dashboard.data import load_observations

    return (
        alt,
        altair_tiles,
        date,
        duckdb,
        getpass,
        load_observations,
        math,
        mo,
        os,
        pd,
        xyzservices,
    )


@app.cell
def _(data_source, duckdb, load_observations):
    _TABLES = ("persons", "stations", "observations")

    def _connect(source):
        """Open a DuckDB connection exposing the frogwatch tables.

        ``source`` may be a Postgres URI, a SQLite ``.db`` file, or a
        ``.duckdb`` file.  The three tables are exposed as views in the default
        catalog so ``load_observations`` can query them unqualified.
        """
        con = duckdb.connect()
        if source.startswith(("postgresql://", "postgres://", "postgresql+psycopg2://")):
            _uri = source.replace("postgresql+psycopg2://", "postgresql://", 1)
            con.execute("INSTALL postgres; LOAD postgres;")
            con.execute(f"ATTACH '{_uri}' AS src (TYPE postgres, READ_ONLY);")
        elif source.endswith(".duckdb"):
            if source.startswith(("http://", "https://", "s3://", "gs://", "gcs://", "r2://")):
                # Remote .duckdb file (e.g. on S3): httpfs reads it in place via
                # HTTP range requests. A private bucket also needs credentials,
                # e.g. con.execute("CREATE SECRET (TYPE s3, ...)") beforehand.
                con.execute("INSTALL httpfs; LOAD httpfs;")
            con.execute(f"ATTACH '{source}' AS src (READ_ONLY);")
        else:  # a SQLite database file
            con.execute("INSTALL sqlite; LOAD sqlite;")
            con.execute(f"ATTACH '{source}' AS src (TYPE sqlite, READ_ONLY);")
        for _t in _TABLES:
            con.execute(f"CREATE VIEW {_t} AS SELECT * FROM src.{_t}")
        return con

    _con = _connect(data_source)
    station_obs, smr_observations = load_observations(_con)
    return smr_observations, station_obs


@app.cell
def _(mo):
    get_filters, set_filters = mo.state({
        'stations': frozenset(),
        'species': frozenset(),
        'observers': frozenset(),
        'start_date': None,
        'end_date': None,
    })
    return get_filters, set_filters


@app.function
def apply_filters(obs, filters, exclude=()):
    _excl = set(exclude)
    df = obs
    if 'stations' not in _excl and filters['stations']:
        df = df[df['name_station'].isin(filters['stations'])]
    if 'species' not in _excl and filters['species']:
        df = df[df['species'].isin(filters['species'])]
    if 'observers' not in _excl and filters['observers']:
        df = df[df['name_observer'].isin(filters['observers'])]
    if filters.get('start_date'):
        df = df[df['obs_datetime'].dt.date >= filters['start_date']]
    if filters.get('end_date'):
        df = df[df['obs_datetime'].dt.date <= filters['end_date']]
    return df


@app.cell
def _(mo, set_filters):
    clear_btn = mo.ui.button(
        label='Clear filters',
        on_click=lambda _: set_filters({
            'stations': frozenset(),
            'species': frozenset(),
            'observers': frozenset(),
            'start_date': None,
            'end_date': None,
        }),
    )
    return (clear_btn,)


@app.cell
def _(get_filters, mo, set_filters, smr_observations):
    _state = get_filters()
    _min = smr_observations['obs_datetime'].min().date()
    _max = smr_observations['obs_datetime'].max().date()

    if _state['start_date']:
        _start_val = max(_state['start_date'], _min)
    else:
        _start_val = _min

    if _state['end_date']:
        _end_val = min(_state['end_date'], _max)
    else:
        _end_val = _max

    def _on_start(v):
        if v != get_filters()['start_date']:
            set_filters(lambda s: {**s, 'start_date': v})

    def _on_end(v):
        if v != get_filters()['end_date']:
            set_filters(lambda s: {**s, 'end_date': v})

    start_date = mo.ui.date(
        start=_min, stop=_max, value=_start_val,
        label='Start', on_change=_on_start,
    )
    end_date = mo.ui.date(
        start=_min, stop=_max, value=_end_val,
        label='End', on_change=_on_end,
    )
    return end_date, start_date


@app.cell
def _(alt, altair_tiles, get_filters, math, mo, pd, station_obs, xyzservices):
    _filt = get_filters()['stations']
    _station_data = station_obs.copy()
    _station_data['size'] = _station_data['observations'].apply(
        lambda v: 15 + 5 * math.log(v + 1)
    )
    _station_data['selected'] = (
        _station_data['name'].isin(_filt) if _filt else True
    )

    _selection = alt.selection_point(fields=['name'])

    _lon_pad = (_station_data['lon'].max() - _station_data['lon'].min()) * 0.10
    _lat_pad = (_station_data['lat'].max() - _station_data['lat'].min()) * 0.10
    _padding = pd.DataFrame({
        'lon': [_station_data['lon'].min() - _lon_pad, _station_data['lon'].max() + _lon_pad] * 2,
        'lat': [_station_data['lat'].min() - _lat_pad] * 2 + [_station_data['lat'].max() + _lat_pad] * 2,
    })
    _padding_layer = alt.Chart(_padding).mark_point(opacity=0, size=0).encode(
        longitude='lon:Q',
        latitude='lat:Q',
    )

    _circles = alt.Chart(_station_data).mark_circle().encode(
        longitude='lon:Q',
        latitude='lat:Q',
        size=alt.Size('observations:Q', legend=None),
        color=alt.condition('datum.selected', alt.value('violet'), alt.value('lightgray')),
        opacity=alt.condition('datum.selected', alt.value(0.9), alt.value(0.4)),
        tooltip=['name:N', 'observations:Q'],
    )

    _chart = alt.layer(_padding_layer, _circles).project('mercator').properties(
        title='South Mountain Reservation',
        width=400,
        height=380,
    )

    _tile_provider = xyzservices.providers.USGS.USTopo
    _tiled = altair_tiles.add_tiles(_chart, _tile_provider).add_params(_selection)
    station_chart = mo.ui.altair_chart(_tiled, chart_selection='point')
    return (station_chart,)


@app.cell
def _(get_filters, set_filters, station_chart):
    import typing

    _selected = station_chart.value
    if isinstance(_selected, typing.Sequence) and len(_selected) > 0:
        _names = frozenset(
            r['name'] for r in _selected
            if isinstance(r, dict) and 'name' in r
        )
        if _names and _names != get_filters()['stations']:
            set_filters(lambda s: {**s, 'stations': _names})
    return


@app.cell
def _(get_filters, mo, pd, set_filters, smr_observations):
    def _station_summary(obs):
        _by = obs.groupby('name_station')
        _names = list(_by.size().sort_values(ascending=False).index)
        _rows = [
            {
                'site': _s,
                'species': _by.get_group(_s)['species'].nunique(),
                'observations': len(_by.get_group(_s)),
                'observers': _by.get_group(_s)['name_observer'].nunique(),
            }
            for _s in _names
        ]
        return pd.DataFrame(_rows)

    _df = _station_summary(
        apply_filters(smr_observations, get_filters(), exclude={'stations'})
    )
    _sel = get_filters()['stations']
    _initial = (
        [i for i, n in enumerate(_df['site'].tolist()) if n in _sel]
        if _sel else []
    )

    def _on_change(rows):
        if rows is None:
            _new = frozenset()
        elif hasattr(rows, 'columns'):
            _new = (
                frozenset(rows['site'].tolist())
                if 'site' in rows.columns else frozenset()
            )
        else:
            _new = frozenset(
                r['site'] for r in rows if isinstance(r, dict) and 'site' in r
            )
        if _new != get_filters()['stations']:
            set_filters(lambda s: {**s, 'stations': _new})

    station_table = mo.ui.table(
        _df,
        selection='multi',
        initial_selection=_initial,
        on_change=_on_change,
        show_data_types=False,
        show_column_summaries=False,
        label='Stations',
    )
    return (station_table,)


@app.cell
def _(get_filters, mo, pd, set_filters, smr_observations):
    def _species_summary(obs):
        _by = obs.groupby('species')
        _names = list(_by.size().sort_values(ascending=False).index)
        _rows = [
            {
                'species': _s,
                'observations': len(_by.get_group(_s)),
                'observers': _by.get_group(_s)['name_observer'].nunique(),
                'sites': _by.get_group(_s)['name_station'].nunique(),
            }
            for _s in _names
        ]
        return pd.DataFrame(_rows)

    _df = _species_summary(
        apply_filters(smr_observations, get_filters(), exclude={'species'})
    )
    _sel = get_filters()['species']
    _initial = (
        [i for i, n in enumerate(_df['species'].tolist()) if n in _sel]
        if _sel else []
    )

    def _on_change(rows):
        if rows is None:
            _new = frozenset()
        elif hasattr(rows, 'columns'):
            _new = (
                frozenset(rows['species'].tolist())
                if 'species' in rows.columns else frozenset()
            )
        else:
            _new = frozenset(
                r['species'] for r in rows if isinstance(r, dict) and 'species' in r
            )
        if _new != get_filters()['species']:
            set_filters(lambda s: {**s, 'species': _new})

    species_table = mo.ui.table(
        _df,
        selection='multi',
        initial_selection=_initial,
        on_change=_on_change,
        show_data_types=False,
        show_column_summaries=False,
        label='Species',
    )
    return (species_table,)


@app.cell
def _(get_filters, mo, pd, set_filters, smr_observations):
    def _observer_summary(obs):
        _by = obs.groupby('name_observer')
        _names = list(_by.size().sort_values(ascending=False).index)
        _rows = [
            {
                'name_observer': _s,
                'observations': len(_by.get_group(_s)),
                'species': _by.get_group(_s)['species'].nunique(),
                'sites': _by.get_group(_s)['name_station'].nunique(),
            }
            for _s in _names
        ]
        return pd.DataFrame(_rows)

    _df = _observer_summary(
        apply_filters(smr_observations, get_filters(), exclude={'observers'})
    )
    _sel = get_filters()['observers']
    _initial = (
        [i for i, n in enumerate(_df['name_observer'].tolist()) if n in _sel]
        if _sel else []
    )

    def _on_change(rows):
        if rows is None:
            _new = frozenset()
        elif hasattr(rows, 'columns'):
            _new = (
                frozenset(rows['name_observer'].tolist())
                if 'name_observer' in rows.columns else frozenset()
            )
        else:
            _new = frozenset(
                r['name_observer'] for r in rows
                if isinstance(r, dict) and 'name_observer' in r
            )
        if _new != get_filters()['observers']:
            set_filters(lambda s: {**s, 'observers': _new})

    observer_table = mo.ui.table(
        _df,
        selection='multi',
        initial_selection=_initial,
        on_change=_on_change,
        show_data_types=False,
        show_column_summaries=False,
        label='Observers',
    )
    return (observer_table,)


@app.cell
def _(get_filters, smr_observations):
    filtered_obs = apply_filters(smr_observations, get_filters())
    return (filtered_obs,)


@app.cell
def _(filtered_obs, mo):
    obs_table = mo.ui.table(
        filtered_obs[[
            'obs_datetime', 'name_station', 'name_observer', 'species',
            'call_intensity', 'temperature', 'beaufort_wind',
        ]].rename(columns={
            'obs_datetime': 'observed_at',
            'name_station': 'station',
            'name_observer': 'observer',
            'call_intensity': 'intensity',
            'beaufort_wind': 'wind',
        }),
        selection=None,
        show_data_types=False,
        show_column_summaries=False,
        label='Observations',
    )
    return (obs_table,)


@app.cell
def _(alt, filtered_obs, pd):
    # Histogram - Observations by Year and Month
    _date_summary = (
        filtered_obs.groupby('obs_year_month')
        .size()
        .reset_index(name='count')
        .rename(columns={'obs_year_month': 'month'})
    )

    _min_year_month = _date_summary['month'].min()
    _max_year_month = _date_summary['month'].max()
    print(f"range: {_min_year_month} - {_max_year_month}")

    #_obs_year_month = _date_summary['month'].to_list()
    #_obs_count = _date_summary['count'].to_list()
    _obs_count = {ym:count for (idx, (ym, count)) in _date_summary.iterrows()}
    print(_obs_count)

    def year_month_range(first: str, last: str) -> list[str]:
        result = []
        year, month = map(int, first.split('-'))
        year_month = first
        while year_month <= last:
            if month not in (11, 12, 1):
                result.append(year_month)
            month += 1
            if month > 12:
                year += 1
                month = 1
            year_month = f"{year:4d}-{month:02d}"
        return result

    _all_year_month = year_month_range(_min_year_month, _max_year_month)
    _all_obs_count = []
    for _year_month in _all_year_month:
        _all_obs_count.append(_obs_count.get(_year_month, 0))

    _all_obs_count_df = pd.DataFrame({
        "month": _all_year_month,
        "count": _all_obs_count,
    })

    date_hist = alt.Chart(_all_obs_count_df).mark_bar().encode(
        x=alt.X('month:O', title='Month/Year'),
        y=alt.Y('count:Q', title='Observations'),
        tooltip=[
            alt.Tooltip('month:O', title='Month'),
            alt.Tooltip('count:Q', title='Observations'),
        ],
    ).properties(
        title='Observations by Year and Month',
        width=1000,
        height=160,
    )

    _date_summary
    return (date_hist,)


@app.cell
def _(alt, date, filtered_obs, pd):
    # Histogram - Observations by Month
    _MONTH = [''] + [date(2000, v, 1).strftime('%b') for v in range(1, 13)]

    _month_counts = {m: 0 for m in range(1, 13)}
    for _m, _grp in filtered_obs.groupby('obs_month'):
        _month_counts[_m] = len(_grp)

    _month_summary = pd.DataFrame({
        'obs_month': list(_month_counts.keys()),
        'month': [_MONTH[v] for v in _month_counts.keys()],
        'count': list(_month_counts.values()),
    })

    month_hist = alt.Chart(_month_summary).mark_bar().encode(
        x=alt.X('month:N', sort=None, title='Month'),
        y=alt.Y('count:Q', title='Observations'),
        tooltip=[
            alt.Tooltip('month:N', title='Month'),
            alt.Tooltip('count:Q', title='Observations'),
        ],
    ).properties(
        title='Observations by Month',
        width=1000,
        height=160,
    )
    return (month_hist,)


if __name__ == "__main__":
    app.run()
