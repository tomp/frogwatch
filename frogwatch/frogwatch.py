#!/usr/bin/env python3
"""
Retrieve Frogwatch data using the Fieldscope API.

Author: Tom Pollard
Created: March 2021
"""
from typing import Optional
import sys
import json
from datetime import datetime, time
from collections import defaultdict
from operator import attrgetter
import sqlite3
import argparse
import logging

import requests

from .version import __version__
from .fieldscope import query_body, QUERY_URL, SCHEMA_URL, STATIONS_URL, SMR_OUTLINE
from .models import (
    Station,
    Person,
    Observation,
    FS_id,
    create_tables,
    update_persons,
    update_stations,
    update_observations,
)


DEFAULT_DB_FILE = "frogwatch.db"


# logging
logging.basicConfig(format="%(message)s", stream=sys.stdout, level="INFO")
logger = logging.getLogger()


def fahrenheit(celsius: float) -> Optional[float]:
    """Convert above-freezing Celsius temperature to Fahrenheit."""
    if not celsius:
        return None
    return round((1.8 * celsius) + 32)


def load_station(
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
    # pylint: disable=too-many-locals

    owner2 = item["owner2"]
    station_owner = Person(
        fs_id=str(owner2["ownerId"]),
        first_name=owner2.get("firstName"),
        last_name=owner2.get("lastName"),
        email=owner2.get("email"),
    )
    people[station_owner.fs_id] = station_owner

    station = Station(
        fs_id=str(item["stationId"]),
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
                fs_id=str(obs["owner"]["ownerId"]),
                first_name=obs["owner"]["firstName"],
                last_name=obs["owner"]["lastName"],
                email=obs["owner"]["email"],
            )
            people[observer.fs_id] = observer

            obs_date = datetime.fromisoformat(obs["collectionDate"]).replace(tzinfo=None)
            if "StartTime" in attrs:
                f = attrs["StartTime"]
                start_time = datetime.combine(
                    date=obs_date.date(),
                    time=time(int(f["hour"]), int(f["minute"]), int(f["second"])),
                )
            else:
                start_time = obs_date

            if "EndTime" in attrs:
                f = attrs["EndTime"]
                end_time = datetime.combine(
                    date=obs_date,
                    time=time(int(f["hour"]), int(f["minute"]), int(f["second"])),
                )
            else:
                end_time = None

            species_id = attrs["FrogWatch_SpeciesId"]
            if "BeaufortWind" in attrs:
                wind = int(attrs["BeaufortWind"])
            else:
                wind = None

            observation = Observation(
                fs_id=str(obs["observationId"]),
                station=station,
                observer=observer,
                start_time=start_time,
                end_time=end_time,
                species=labels["FrogWatch_SpeciesId"][species_id],
                call_intensity=attrs.get("FrogWatch_CallIntensity"),
                temperature=fahrenheit(float(attrs.get("AirTemperature", "0.0"))),
                beaufort_wind=wind,
                precip_48h=attrs.get("FrogWatch_PrecipitationLast48"),
                precip=attrs.get("FrogWatch_Precipitation"),
                above_freezing_48h=attrs.get("FrogWatch_AboveFreezingLast48"),
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
        "--db", action="store_true", help="Write downloaded data to the database."
    )
    parser.add_argument(
        "--db-file", default=DEFAULT_DB_FILE, help="The name of the SQLite DB to use."
    )
    parser.add_argument(
        "--nj", action="store_true", help="Return only observations from New Jersey"
    )
    parser.add_argument(
        "--smr",
        action="store_true",
        help="Return only observations from South Mountain Reservation",
    )
    parser.add_argument(
        "--hartshorne",
        action="store_true",
        help="Return only observations for the Cora Hartshorne Frogwatch chapter",
    )
    parser.add_argument("--start-date", help="Start date for observations (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Ending date for observations (YYYY-MM-DD)")
    parser.add_argument("--stations", action="store_true", help="Download station data separately")
    parser.add_argument("--quiet", action="store_true", help="Don't summarize all observations in the output")
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

    db = sqlite3.connect(opt.db_file)
    create_tables(db)

    resp = requests.get(SCHEMA_URL)
    labels = load_schema(resp.json())

    outline, state, chapter = None, None, []
    if opt.smr:
        outline = SMR_OUTLINE
    if opt.nj:
        state = "NJ"
    if opt.hartshorne:
        chapter = "138"

    stations: dict[FS_id, Station] = {}
    observations: dict[FS_id, Observation] = {}
    people: dict[FS_id, Person] = {}

    # Stations query
    if opt.stations:
        logger.debug(STATIONS_URL)
        resp = requests.get(STATIONS_URL)
        logger.debug(f"stations request returned status {resp.status_code}")
        resp.raise_for_status()

        for item in resp.json()["result"]:
            load_station(item, labels, stations, observations, people)
        logger.info(f"Loaded {len(stations)} stations")

    # Observations query
    query = query_body(
        outline=outline, state=state, chapter=chapter, start_date=opt.start_date, end_date=opt.end_date
    )
    logger.debug(QUERY_URL)
    logger.debug(json.dumps(query, indent=4))
    resp = requests.post(QUERY_URL, json=query)
    logger.debug(f"query returned status {resp.status_code}")
    resp.raise_for_status()

    if not "result" in resp.json():
        logger.error(json.dumps(resp.json(), indent=4))
        return 1

    for item in resp.json()["result"]:
        load_station(item, labels, stations, observations, people)
    logger.info(f"{len(observations)} observations from {len(stations)} stations")

    update_persons(db, people)
    update_stations(db, stations)
    update_observations(db, observations)

    for obs in sorted(
        observations.values(), key=attrgetter("start_time"), reverse=True
    ):
        if not opt.quiet:
            logger.info(
                f"{obs.start_time.strftime('%Y-%m-%d  %H:%M')} : "
                f"{obs.station.name.replace('South Mountain Reservation', 'SMR'):40s}  "
                f"{obs.observer.name:20s}  "
                f"{obs.species}"
            )


if __name__ == "__main__":
    sys.exit(main())
