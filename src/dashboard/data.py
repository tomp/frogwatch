"""
Load 'raw' Frogwatch data from a database, and prepare it for display on the dashboard.

The raw data is more or less a copy of the data available through the Fieldscope API,
but normalized into Person, Station, and Observation tables.  For the dashboard, we
pull just the data for a particular project, such as South Mountain Reservation,
re-label duplicate stations and species, and de-nomalize the station and person data back
into the observations, to produce the observations dataframe that will be displayed.

This code was adapted from the Jupyter notebook in which the dashboard was developed.

Written: May 2021
Author: Tom Pollard
"""
import re
from datetime import datetime, date
from collections import defaultdict
from pprint import pprint

import numpy as np
import pandas as pd

def load_observations(client):
    """Return dataframes representing the stations and observations to display."""

    stations = pd.read_sql('select * from stations', client)
    people = pd.read_sql('select * from persons', client)
    observations = pd.read_sql('select * from observations', client)

    stations.rename(columns={"fs_id":"fs_id_station", "name":"name_station"}, inplace=True)
    people.rename(columns={"fs_id":"fs_id_observer", "name":"name_observer"}, inplace=True)

    # Remove sub-species IDs
    observations['species'] = [re.sub(r" \(.*$", "", name) for name in observations['species']]

    # Replace redundant station IDs
    smr_station_ids = list(
        [v for v in stations[stations['name_station'].str.contains('SMR')].fs_id_station])

    observations.loc[observations['station_id'] == '593550', 'station_id'] = '100000218'
    observations.loc[observations['station_id'] == '1480244', 'station_id'] = '100000219'
    observations.loc[observations['station_id'] == '605236', 'station_id'] = '100000215'
    observations.loc[observations['station_id'] == '100000202', 'station_id'] = '100000215'
    smr_station_ids = [v for v in smr_station_ids if v != '100000202']


    # De-normalize the station and person data into the observations

    obs_and_name = pd.merge(
         observations,
         people[['fs_id_observer', 'name_observer']],
         how="left", left_on="observer_id", right_on="fs_id_observer")

    obs_full = pd.merge(
         obs_and_name,
         stations[['fs_id_station', 'name_station', 'lat', 'lon']],
         how="left", left_on="station_id", right_on="fs_id_station")

    observations = obs_full[['station_id', 'observer_id', 'start_time',
                         'species', 'call_intensity', 'temperature', 'beaufort_wind',
                         'name_observer', 'name_station', 'lat', 'lon']]

    # Convert observation times to datetimes
    observations = observations.assign(
        obs_datetime=pd.to_datetime(observations['start_time'], utc=True))

    # Add additional date-related fields, to support time histograms
    observations['obs_week'] = observations['obs_datetime'].apply(
        lambda dt: dt.date().isocalendar()[1]) # int 0-52
    observations['obs_month'] = observations['obs_datetime'].apply(
        lambda dt: dt.month) # int 1-12
    observations['obs_year_month'] = observations['obs_datetime'].apply(
        lambda dt: f"{dt.year:4d}-{dt.month:02d}") # string

    # Select just the observations from SMR
    smr_observations = observations[
            observations['station_id'].isin(smr_station_ids) &
            (observations['obs_datetime'].apply(lambda ts: ts.year) >= 2010)
    ].sort_values(by=['obs_datetime'], ascending=False)

    station_data = defaultdict(list)

    # Create a dataframe for just the stations found in the SMR observations
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
            station_data['name'].append(stations.loc[stations['fs_id_station'] == station_id, "name_station"].iloc[0])
            station_data['lat'].append(stations.loc[stations['fs_id_station'] == station_id, "lat"].iloc[0])
            station_data['lon'].append(stations.loc[stations['fs_id_station'] == station_id, "lon"].iloc[0])
            station_data['observations'].append(0)

    station_obs = pd.DataFrame(station_data)

    return station_obs, smr_observations

