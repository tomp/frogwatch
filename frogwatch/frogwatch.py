#!/usr/bin/env python3
"""
Retrieve Frogwatch data using the Fieldscope API.

Author: Tom Pollard
Created: March 2021
"""
from typing import Optional
from pathlib import Path
import sys
import json
import csv
from datetime import datetime, time
from collections import defaultdict
from operator import attrgetter
from pprint import pformat
import logging

import configargparse
import requests
import jsonpath_rw as jsonpath

from .version import __version__
from .fieldscope import (
    query_body, QUERY_URL, SCHEMA_URL, USER_URL, STATIONS_URL, SMR_OUTLINE
)
from .models import Station, Person, Observation, FS_id
from . import db_sqlite as db


CSV_TYPE = ".csv"
TEXT_TYPE = ".txt"
SUPPORTED_FILETYPES = (TEXT_TYPE, CSV_TYPE)

# Debugging files
SCHEMA_REQUEST_PATH = "frogwatch_schema_request.json"
SCHEMA_RESULT_PATH = "frogwatch_schema_reponse.json"

STATIONS_REQUEST_PATH = "frogwatch_stations_request.json"
STATIONS_RESULT_PATH = "frogwatch_stations_reponse.json"

QUERY_REQUEST_PATH = "frogwatch_query_request.json"
QUERY_RESULT_PATH = "frogwatch_query_reponse.json"

USER_AGENT="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0"


# logging
logging.basicConfig(format="%(message)s", stream=sys.stdout, level="INFO")
logger = logging.getLogger()


class UsageError(Exception):
    """A UsageError is raised when there's a problem with the commandline arguments."""


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

    station_owner = Person(fs_id=str(item["ownerId"]))
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
    if 'hartshorne' in station.name.lower():
        logger.debug(f"{station.fs_id:5s}:  '{station.name}")

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

            obs_date = datetime.fromisoformat(obs["collectionDate"]).replace(
                tzinfo=None
            )
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


ALL_FOLDERS_EXPR = jsonpath.parse("$..folders[*]")
ALL_FIELDS_EXPR = jsonpath.parse("$..folders[*].fields[*]")

def load_schema(schema: dict) -> dict[str, dict[str, str]]:
    """Load the mappings from the codes used in the database to the labels
    people are used to seeing, for the coded fields in the schema.
    Returns a dict mapping the field name to a dict mapping each db value to
    its label.
    """
    labels = defaultdict(dict)
    for match in ALL_FIELDS_EXPR.find(schema):
        field = match.value
        field_name = field["name"]
        logger.debug(f"{match.full_path}:\t{field_name} \t--> {field['label']}")
        if field.get('values'):
            for item in field['values']:
                field_value, value_label = item['value'], item['label']
                labels[field_name][field_value] = value_label
    return labels


def observations_as_text(observations: list[Observation], reverse: bool = True) -> str:
    lines = []
    for obs in sorted(
        observations.values(), key=attrgetter("start_time"), reverse=reverse
    ):
        lines.append(
            f"{obs.start_time.strftime('%Y-%m-%d  %H:%M')} : "
            f"{obs.station.name.replace('South Mountain Reservation', 'SMR'):40s}  "
            f"{obs.observer.name:20s}  "
            f"{obs.species}"
        )
    return "\n".join(lines)


def write_csv(observations: list[Observation], fp, reverse: bool = True) -> None:
    wtr = csv.writer(fp)
    wtr.writerow(("Date", "Station", "Observer", "Species", "Intensity"))
    for obs in sorted(
        observations.values(), key=attrgetter("start_time"), reverse=reverse
    ):
        wtr.writerow((
            obs.start_time.strftime('%Y-%m-%d %H:%M:00+0400'),
            obs.station.name.replace('South Mountain Reservation', 'SMR'),
            obs.observer.name,
            obs.species,
            obs.call_intensity
        ))


def parse_args():
    """Parse the commandline arguments.  A Namespace object is returned."""
    parser = configargparse.ArgumentParser()
    parser.add_argument("--outfile", help="An output file for the selected observations")
    parser.add_argument(
        "--db", action="store_true", help="Write downloaded data to the database."
    )
    parser.add_argument(
        "--db-uri",
        default=db.DEFAULT_DB_URI,
        env_var="DATABASE_URL",
        help="A Postgres connection URI specifying the DB to use.",
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
    parser.add_argument(
        "--stations", action="store_true", help="Download station data separately"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't summarize all observations in the output",
    )
    parser.add_argument("--debug", action="store_true", help="Produce debugging output")
    opt = parser.parse_args()

    if opt.start_date:
        opt.start_date = datetime.strptime(opt.start_date, "%Y-%m-%d")
    if opt.end_date:
        opt.end_date = datetime.strptime(opt.end_date, "%Y-%m-%d")

    if opt.outfile:
        opt.file_type = Path(opt.outfile).suffix.lower()
        if not opt.file_type:
            opt.file_type = "txt"
        elif not opt.file_type in SUPPORTED_FILETYPES:
            raise UsageError(f"unsupported file type '{opt.file_type}'")

    return opt


def store_response(resp: requests.Request, request_file: str = None, response_file: str = None):
    """Store the request and/or response for an API request.  The 'resp' is the
    requests.Request object, after the request has completed.
    """
    if request_file:
        req = resp.request
        req_parts = {
            "url": req.url,
            "method": req.method,
            "headers": req.headers,
            "body": req.body,
        }
        Path(request_file).write_text(pformat(req_parts, indent=4, width=240))
        logger.info(f"Wrote {request_file}")
    if response_file:
        Path(response_file).write_text(pformat(resp.json(), indent=4, width=240))
        logger.info(f"Wrote {response_file}")


def main() -> int:
    """The toplevel function.  An exitcode is returned."""
    opt = parse_args()
    if opt.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("[debug mode]")

    client = db.connect(opt.db_uri)
    db.create_tables(client)

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT, 
        "csrftoken": "chQ4Ft5MQDn6bVHCA29SI7MJcTUfh2R9Lsd4Rt2XaVaLvSw4XlWp01CIyS6bPg5m",
        "sessionid": "iby34pnw93l1o62403y39xvno421r6tn",
     })

    logger.debug(f"FROGWATCH_SCHEMA_URL: \t{SCHEMA_URL}")
    resp = session.get(SCHEMA_URL)

    if opt.debug:
        store_response(resp, SCHEMA_REQUEST_PATH, SCHEMA_RESULT_PATH)

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
        logger.debug(f"FROGWATCH_STATIONS_URL: \t{STATIONS_URL}")
        resp = session.get(STATIONS_URL)
        logger.debug(f"stations request returned status {resp.status_code}")
        if opt.debug:
            store_response(resp, STATIONS_REQUEST_PATH, STATIONS_RESULT_PATH)
        resp.raise_for_status()

        for item in resp.json()["result"]:
            load_station(item, labels, stations, observations, people)
        logger.info(f"Loaded {len(stations)} stations")

    # Observations query
    query = query_body(
        outline=outline,
        state=state,
        chapter=chapter,
        start_date=opt.start_date,
        end_date=opt.end_date,
    )
    logger.debug(f"FROGWATCH_QUERY_URL: \t{QUERY_URL}")
    resp = session.post(QUERY_URL, json=query)
    logger.debug(f"query returned status {resp.status_code}")
    if opt.debug:
        store_response(resp, QUERY_REQUEST_PATH, QUERY_RESULT_PATH)
    resp.raise_for_status()

    if not "result" in resp.json():
        logger.error(json.dumps(resp.json(), indent=4))
        return 1

    for item in resp.json()["result"]:
        load_station(item, labels, stations, observations, people)
    logger.info(f"{len(observations)} observations from {len(stations)} stations")

    db.update_persons(client, people)
    db.update_stations(client, stations)
    db.update_observations(client, observations)

    if opt.outfile:
        with Path(opt.outfile).open('w') as fp:
            if opt.file_type == CSV_TYPE:
                    write_csv(observations, fp)
            elif opt.file_type == TEXT_TYPE:
                fp.write(observations_as_text(observations))
                fp.write()
        logger.info(f"Wrote {opt.outfile}")
    elif not opt.quiet:
        logger.info(observations_as_text(observations))

    return 0


if __name__ == "__main__":
    sys.exit(main())
