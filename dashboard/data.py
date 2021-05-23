"""
Load 'raw' Frogwatch data from a database, and prepare it for display on the dashboard.

The raw data is more or less a copy of the data available through the Fieldscope API,
but normalized into Person, Station, and Observation tables.  For the dashboard, we
pull just the data for a particular project, such as South Mountain Reservation, 
re-lebel duplicate stations and species, and denomalize the station and person data back
into the observations, to produce the observations dataframe that will be displayed.

This code was adapted from the Jupyter notebook in which the dashboard was developed.

Written: May 2021
Author: Tom Pollard
"""
import re
from collections import defaultdict

import numpy as np
import pandas as pd
import psycopg2 as pg


def load_observations():
    """Return dataframes representing the stations and observations to display."""

    db = pg.connect('postgresql://pollard@localhost:5432/frogwatch')

    stations = pd.read_sql('select * from stations', db)
    people = pd.read_sql('select * from persons', db)
    observations = pd.read_sql('select * from observations', db)

    observations['species'] = [re.sub(r" \(.*$", "", name) for name in observations['species']]

    smr_station_ids = list([v for v in stations[stations['name'].str.contains('SMR')].fs_id])

    observations.loc[observations['station_id'] == '593550', 'station_id'] = '100000218'
    observations.loc[observations['station_id'] == '1480244', 'station_id'] = '100000219'
    observations.loc[observations['station_id'] == '605236', 'station_id'] = '100000215'
    observations.loc[observations['station_id'] == '100000202', 'station_id'] = '100000215'
    smr_station_ids = [v for v in smr_station_ids if v != '100000202']

    obs_and_name = pd.merge(
         observations, 
         people[['fs_id', 'name']], 
         how="left", left_on="observer_id", right_on="fs_id", suffixes=[None, "_observer"])
    
    obs_full = pd.merge(
         obs_and_name, 
         stations[['fs_id', 'name', 'lat', 'lon']], 
         how="left", left_on="station_id", right_on="fs_id", suffixes=["_observer", "_station"])

    observations = obs_full[['station_id', 'observer_id', 'start_time', 
                         'species', 'call_intensity', 'temperature', 'beaufort_wind', 
                         'name_observer', 'name_station', 'lat', 'lon']]
    
    observations = observations.assign(
        start_time=pd.to_datetime(observations['start_time'], utc=True))

    smr_observations = observations[
            observations['station_id'].isin(smr_station_ids) & 
            (observations['start_time'].apply(lambda ts: ts.year) >= 2010)
    ].sort_values(by=['start_time'], ascending=False)
    
    station_data = defaultdict(list)

    # create an entry for every station in the given observations
    for station_id, obs_ids in smr_observations.groupby(['station_id']).groups.items():
        obs = smr_observations.loc[obs_ids[0]]
        station_data['station_id'].append(station_id)
        station_data['name'].append(obs["name_station"])
        station_data['lat'].append(obs['lat'])
        station_data['lon'].append(obs["lon"])
        station_data['observations'].append(len(obs_ids))

    # Add stations that are defined, but have no observations
    for station_id in smr_station_ids:
        if station_id not in station_data['station_id']:
            station_data['station_id'].append(station_id)
            station_data['name'].append(stations.loc[stations['fs_id'] == station_id, "name"].iloc[0])
            station_data['lat'].append(stations.loc[stations['fs_id'] == station_id, "lat"].iloc[0])
            station_data['lon'].append(stations.loc[stations['fs_id'] == station_id, "lon"].iloc[0])
            station_data['observations'].append(0)

    station_obs = pd.DataFrame(station_data)

    return station_obs, smr_observations
