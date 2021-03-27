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
from collections import defaultdict
from operator import attrgetter
import argparse
import logging

import requests

from .version import __version__
from .fieldscope import query_body, QUERY_URL, SCHEMA_URL, SMR_OUTLINE

# logging
logging.basicConfig(format="%(message)s", stream=sys.stdout, level="INFO")
logger = logging.getLogger()

# models
# pylint: disable=too-many-instance-attributes

FS_id = str


@dataclass
class Station:
    """A Station is a location from which observations are reported."""

    fs_id: FS_id  # the Fieldscope id for this station
    name: str  # the station name
    lon: float  # longitude in decinmal degrees
    lat: float  # latitude in decimal degrees
    city: str  # the station's city
    county: str  # the station's county
    state: str  # the station's state
    owner: "Person"  # the station "owner"


@dataclass
class Person:
    """A Person is a station owner or an observer."""

    fs_id: FS_id  # the fieldscope id for this person
    first_name: str  # their first name
    last_name: str  # their last name
    email: str  # their email address

    @property
    def name(self):
        return self.first_name + " " + self.last_name


@dataclass
class Observation:
    """An Observation is an observation of a single frog species at a specific
    time and location.
    """

    fs_id: FS_id  # the fieldscope id for this observation
    station: "Station"  # the station where the observation was made
    observer: "Person"  # the person who reported the observation
    start_time: datetime  # the beginning of the observation period
    end_time: datetime  # the end of the observation period
    species: str
    call_intensity: str
    temperature: float
    beaufort_wind: str
    precip_48h: str
    precip: str
    above_freezing_48h: str
    notes: str


def fahrenheit(celsius: float) -> float:
    """Convert celsius temperature to Fahrenheit."""
    return round(18 * celsius + 32)


def load_result(
    item: dict,
    labels: dict[str, dict[str, str]],
    stations: dict[FS_id, Station],
    observations: dict[FS_id, Observation],
    people: dict[FS_id, Person],
) -> None:
    """Extract observations from the given query result item and save information
    about the station, the observations, and the observers in the given maps.
    Each item represents the observations for a single station.
    """

    owner2 = item["owner2"]
    station_owner = Person(
        fs_id=owner2["ownerId"],
        first_name=owner2.get("firstName"),
        last_name=owner2.get("lastName"),
        email=owner2.get("email"),
    )
    people[station_owner.fs_id] = station_owner

    station = Station(
        fs_id=item["stationId"],
        name=item["stationName"],
        lon=float(item["geometry"]["x"]),
        lat=float(item["geometry"]["y"]),
        city=item["attributes"].get("City"),
        county=item["attributes"].get("County"),
        state=item["attributes"].get("State"),
        owner=station_owner,
    )
    stations[station.fs_id] = station

    for obs in item["observations"]:
        try:
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
                time=time(int(f["hour"]), int(f["minute"]), int(f["second"])),
            )
            f = attrs["EndTime"]
            end_time = datetime.combine(
                date=obs_date,
                time=time(int(f["hour"]), int(f["minute"]), int(f["second"])),
            )

            species_id = attrs["FrogWatch_SpeciesId"]

            observation = Observation(
                fs_id=obs["observationId"],
                station=station,
                observer=observer,
                start_time=start_time,
                end_time=end_time,
                species=labels["FrogWatch_SpeciesId"][species_id],
                call_intensity=attrs["FrogWatch_CallIntensity"],
                temperature=fahrenheit(float(attrs.get("AirTemperature", "0.0"))),
                beaufort_wind=int(attrs["BeaufortWind"]),
                precip_48h=attrs["FrogWatch_PrecipitationLast48"],
                precip=attrs["FrogWatch_Precipitation"],
                above_freezing_48h=attrs["FrogWatch_AboveFreezingLast48"],
                notes=attrs.get("Notes"),
            )
            observations[observation.fs_id] = observation
        except KeyError as exc:
            logger.error(f"KeyError: {exc}\nobservation = {json.dumps(obs, indent=4)}")


def load_schema(body: dict) -> dict[str, dict[str, str]]:
    """Load the mappings from the codes used in the database to the labels
    people are used to seeing, for the coded fields in the schema.
    Returns a dict mapping the field name to a dict mapping each db value to
    its label.
    """
    labels = defaultdict(dict)
    for result in body["result"].values():
        if not "folders" in result:
            continue

        for folder in result["folders"]:
            for field in folder["fields"]:
                if not field["values"]:
                    continue
                name = field["name"]
                for item in field["values"]:
                    labels[name][item["value"]] = item["label"]
    return labels


def parse_args():
    """Parse the commandline arguments.  A Namespace object is returned."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nj", action="store_true", help="Limit results to New Jersey sites"
    )
    parser.add_argument(
        "--smr",
        action="store_true",
        help="Limit results to South Mountain Reservation sites",
    )
    parser.add_argument("--start-date", help="Start date for observations (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Ending date for observations (YYYY-MM-DD)")
    parser.add_argument("--debug", action="store_true", help="Produce debugging output")
    opt = parser.parse_args()

    if opt.start_date:
        opt.start_date = datetime.strptime(opt.start_date, "%Y-%m-%d")
    if opt.end_date:
        opt.end_date = datetime.strptime(opt.end_date, "%Y-%m-%d")

    return opt


def main() -> int:
    """The toplevel function.  An exitcode is returned."""
    opt = parse_args()
    if opt.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("[debug mode]")

    resp = requests.get(SCHEMA_URL)
    labels = load_schema(resp.json())

    outline, states = None, None
    if opt.smr:
        outline = SMR_OUTLINE
    if opt.nj:
        states = "NJ"

    query = query_body(
        outline=outline, state=states, start_date=opt.start_date, end_date=opt.end_date
    )
    logger.debug(json.dumps(query, indent=4))
    resp = requests.post(QUERY_URL, json=query)
    logger.debug(f"query returned status {resp.status_code}")
    resp.raise_for_status()

    stations: dict[FS_id, Station] = {}
    observations: dict[FS_id, Observation] = {}
    people: dict[FS_id, Person] = {}

    for item in resp.json()["result"]:
        load_result(item, labels, stations, observations, people)
    logger.info(f"{len(observations)} observations from {len(stations)} stations")

    for obs in sorted(
        observations.values(), key=attrgetter("start_time"), reverse=True
    ):
        logger.info(
            f"{obs.start_time.strftime('%Y-%m-%d  %H:%M')} : "
            f"{obs.station.name.replace('South Mountain Reservation', 'SMR'):40s}  "
            f"{obs.observer.name:20s}  "
            f"{obs.species}"
        )


if __name__ == "__main__":
    sys.exit(main())
