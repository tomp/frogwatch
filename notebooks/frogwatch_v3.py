import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Frogwatch
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observations
    """)
    return


@app.cell(hide_code=True)
def _(
    date_hist,
    mo,
    month_hist,
    obs_table,
    observer_table,
    species_table,
    station_chart,
):
    mo.vstack([
        mo.hstack([station_chart, mo.vstack([species_table, observer_table])]),
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
def _():
    import os
    import sys
    import math
    from datetime import date

    import altair as alt
    import altair_tiles
    import pandas as pd
    import sqlalchemy
    import marimo as mo
    import xyzservices

    # Add src/ to path so we can import dashboard.data
    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
    if _src not in sys.path:
        sys.path.insert(0, _src)

    from dashboard.data import load_observations

    return (
        alt,
        altair_tiles,
        date,
        load_observations,
        math,
        mo,
        os,
        pd,
        sqlalchemy,
        xyzservices,
    )


@app.cell
def _(load_observations, os, sqlalchemy):
    _db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://pollard@localhost:5432/frogwatch")
    _engine = sqlalchemy.create_engine(_db_url)
    station_obs, smr_observations = load_observations(_engine)
    # mo.md(f"Loaded **{len(smr_observations)}** observations from **{len(station_obs)}** stations.")
    return smr_observations, station_obs


@app.cell
def _(alt, altair_tiles, math, mo, pd, station_obs, xyzservices):
    _station_data = station_obs.copy()
    _station_data['size'] = _station_data['observations'].apply(
        lambda v: 15 + 5 * math.log(v + 1)
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
        color=alt.condition(_selection, alt.value('violet'), alt.value('lightgray')),
        opacity=alt.condition(_selection, alt.value(0.9), alt.value(0.4)),
        tooltip=['name:N', 'observations:Q'],
    )

    _chart = alt.layer(_padding_layer, _circles).project('mercator').properties(
        title='South Mountain Reservation Stations',
        width=400,
        height=380,
    )

    _tiled = altair_tiles.add_tiles(_chart, xyzservices.providers.CartoDB.Positron).add_params(
        _selection
    )
    station_chart = mo.ui.altair_chart(_tiled, chart_selection='point')
    return (station_chart,)


@app.cell
def _(smr_observations, station_chart):
    import typing

    _selected = station_chart.value
    if isinstance(_selected, typing.Sequence):
        _names = set(_selected['name'])
        obs_by_station = smr_observations[smr_observations['name_station'].isin(_names)]
    else:
        obs_by_station = smr_observations
    return (obs_by_station,)


@app.cell
def _(mo, obs_by_station, pd):
    def _species_summary(obs):
        _by_species = obs.groupby('species')
        _names = list(_by_species.size().sort_values(ascending=False).index)
        _rows = []
        for _sp in _names:
            _grp = _by_species.get_group(_sp)
            _rows.append({
                'species': _sp,
                'observations': len(_grp),
                'observers': _grp['name_observer'].nunique(),
                'sites': _grp['name_station'].nunique(),
            })
        return pd.DataFrame(_rows)

    species_table = mo.ui.table(
        _species_summary(obs_by_station),
        selection='multi',
        label='Species',
    )
    return (species_table,)


@app.cell
def _(obs_by_station, species_table):
    _selected = species_table.value
    if _selected is not None and len(_selected) > 0:
        _species = set(_selected['species'])
        obs_by_station_and_species = obs_by_station[obs_by_station['species'].isin(_species)]
    else:
        obs_by_station_and_species = obs_by_station
    return (obs_by_station_and_species,)


@app.cell
def _(mo, obs_by_station_and_species, pd):
    def _observer_summary(obs):
        _by_observer = obs.groupby('name_observer')
        _names = list(_by_observer.size().sort_values(ascending=False).index)
        _rows = []
        for _ob in _names:
            _grp = _by_observer.get_group(_ob)
            _rows.append({
                'name_observer': _ob,
                'observations': len(_grp),
                'species': _grp['species'].nunique(),
                'sites': _grp['name_station'].nunique(),
            })
        return pd.DataFrame(_rows)

    observer_table = mo.ui.table(
        _observer_summary(obs_by_station_and_species),
        selection='multi',
        label='Observers',
    )
    return (observer_table,)


@app.cell
def _(obs_by_station_and_species, observer_table):
    _selected = observer_table.value
    if _selected is not None and len(_selected) > 0:
        _observers = set(_selected['name_observer'])
        filtered_obs = obs_by_station_and_species[
            obs_by_station_and_species['name_observer'].isin(_observers)
        ]
    else:
        filtered_obs = obs_by_station_and_species
    return (filtered_obs,)


@app.cell
def _(filtered_obs, mo):
    obs_table = mo.ui.table(
        filtered_obs[['obs_datetime', 'name_station', 'name_observer', 'species',
                       'call_intensity', 'temperature', 'beaufort_wind']].rename(columns={
            'obs_datetime': 'observed_at',
            'name_station': 'station',
            'name_observer': 'observer',
            'call_intensity': 'intensity',
            'beaufort_wind': 'wind',
        }),
        selection=None,
        label='Observations',
    )
    return (obs_table,)


@app.cell
def _(alt, filtered_obs):
    _date_summary = (
        filtered_obs.groupby('obs_year_month')
        .size()
        .reset_index(name='count')
        .rename(columns={'obs_year_month': 'month'})
    )

    date_hist = alt.Chart(_date_summary).mark_bar().encode(
        x=alt.X('month:T', title='Month/Year', axis=alt.Axis(format='%b %Y')),
        y=alt.Y('count:Q', title='Observations'),
        tooltip=[
            alt.Tooltip('month:T', title='Month', format='%b %Y'),
            alt.Tooltip('count:Q', title='Observations'),
        ],
    ).properties(
        title='Observations by Year and Month',
        width=800,
        height=160,
    )
    return (date_hist,)


@app.cell
def _(alt, date, filtered_obs, pd):
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
        width=800,
        height=160,
    )
    return (month_hist,)


if __name__ == "__main__":
    app.run()
