#!/usr/bin/env python3
"""
Retrieve Frogwatch data using the Fieldscope API.

Author: Tom Pollard
Created: March 2021
"""
import sys
import json
from datetime import datetime, time
from dataclasses import dataclass
import argparse
import logging

import requests

from .version import __version__
from .fieldscope import (query_body, OBS_FIELDS, QUERY_URL)

# logging
logging.basicConfig(format="%(message)s", stream=sys.stdout, level="INFO")
logger = logging.getLogger()

# models
#pylint: disable=too-many-instance-attributes

FS_id = str

@dataclass
class Station():
    """A Station is a location from which observations are reported."""
    fs_id: FS_id    # the Fieldscope id for this station
    name: str       # the station name
    lon: float      # longitude in decinmal degrees
    lat: float      # latitude in decimal degrees
    city: str       # the station's city
    county: str     # the station's county
    state: str      # the station's state
    owner: "Person" # the station "owner"


@dataclass
class Person():
    """A Person is a station owner or an observer."""
    fs_id: FS_id    # the fieldscope id for this person
    first_name: str # their first name
    last_name: str  # their last name
    email: str      # their email address


@dataclass
class Observation():
    """An Observation is an observation of a single frog species at a specific
    time and location.
    """
    fs_id: FS_id          # the fieldscope id for this observation
    station: "Station"    # the station where the observation was made
    observer: "Person"    # the person who reported the observation
    start_time: datetime  # the beginning of the observation period
    end_time: datetime    # the end of the observation period
    species_id: str
    call_intensity: int
    temperature: float
    beaufort_wind: int
    precip_48h: int
    precip: int
    above_freezing_48h: bool
    notes: str


def load_result(
        item: dict,
        stations: dict[FS_id, Station],
        observations: dict[FS_id, Observation],
        people: dict[FS_id, Person]
) -> None:
    """Extract observations from the given query result item and save information
    about the station, the observations, and the observers in the given maps.
    Each item represents the observations for a single station.
    """
    station_owner = Person(
        fs_id=item["owner2"]["ownerId"],
        first_name=item["owner2"]["firstName"],
        last_name=item["owner2"]["lastName"],
        email=item["owner2"]["email"],
    )
    people[station_owner.fs_id] = station_owner

    station = Station(
        fs_id=item["stationId"],
        name=item["stationName"],
        lon=float(item["geometry"]["x"]),
        lat=float(item["geometry"]["y"]),
        city=item["attributes"]["City"],
        county=item["attributes"]["County"],
        state=item["attributes"]["State"],
        owner=station_owner,
    )
    stations[station.fs_id] = station

    for obs in item["observations"]:
        attrs = obs["attributes"]

        observer = Person(
            fs_id=obs["owner"]["ownerId"],
            first_name=obs["owner"]["firstName"],
            last_name=obs["owner"]["lastName"],
            email=obs["owner"]["email"],
        )
        people[observer.fs_id] = observer

        obs_date = datetime.fromisoformat(obs["collectionDate"]).date()
        f = attrs["StartTime"]
        start_time = datetime.combine(
                date=obs_date,
                time=time(int(f["hour"]), int(f["minute"]), int(f["second"]))
        )
        f = attrs["EndTime"]
        end_time = datetime.combine(
                date=obs_date,
                time=time(int(f["hour"]), int(f["minute"]), int(f["second"]))
        )

        observation = Observation(
            fs_id=obs["observationId"],
            station=station,
            observer=observer,
            start_time=start_time,
            end_time=end_time,
            species_id=attrs["FrogWatch_SpeciesId"],
            call_intensity=int(attrs["FrogWatch_CallIntensity"]),
            temperature=int(attrs["AirTemperature"]),
            beaufort_wind=int(attrs["BeaufortWind"]),
            precip_48h=int(attrs["FrogWatch_PrecipitationLast48"]),
            precip=int(attrs["FrogWatch_Precipitation"]),
            above_freezing_48h=int(attrs["FrogWatch_AboveFreezingLast48"]),
            notes=attrs["FrogWatch_SpeciesId"],
        )
        observations[observation.fs_id] = observation


def parse_args():
    """Parse the commandline arguments.  A Namespace object is returned."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Produce debugging output")
    opt = parser.parse_args()
    return opt


def main() -> int:
    """The toplevel function.  An exitcode is returned."""
    opt = parse_args()
    if opt.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("[debug mode]")

    query = query_body(fields=OBS_FIELDS)
    resp = requests.post(QUERY_URL, json=query)
    logger.debug(json.dumps(resp.json(), indent=4))

    stations: dict[FS_id, Station] = {}
    observations: dict[FS_id, Observation] = {}
    people: dict[FS_id, Person] = {}

    for item in resp.json()["result"]:
        load_result(item, stations, observations, people)
    logger.info(f"{len(observations)} observations from {len(stations)} stations")


if __name__ == "__main__":
    sys.exit(main())
