"""
Data models for the Frogwatch project.
"""
from datetime import datetime
from dataclasses import dataclass
import sqlite3

# pylint: disable=too-many-instance-attributes

FS_id = str


@dataclass
class Person:
    """A Person is a station owner or an observer."""

    fs_id: FS_id  # the fieldscope id for this person
    first_name: str  # their first name
    last_name: str  # their last name
    email: str  # their email address

    @property
    def name(self):
        """Return the person's full name."""
        return self.first_name + " " + self.last_name


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


# SQL
ENABLE_FOREIGN_KEYS: str = "PRAGMA foreign_keys = ON;"

CREATE_PERSONS_TABLE: str = """
CREATE TABLE IF NOT EXISTS persons (
    fs_id TEXT,
    name TEXT NOT NULL,
    email TEXT,
    PRIMARY KEY (fs_id)
)
""".strip()

CREATE_STATIONS_TABLE: str = """
CREATE TABLE IF NOT EXISTS stations (
    fs_id TEXT,
    name TEXT NOT NULL,
    lon REAL,
    lat REAL,
    city TEXT,
    county TEXT,
    state TEXT,
    owner_id INTEGER,
    PRIMARY KEY (fs_id),
    FOREIGN KEY (owner_id)
        REFERENCES persons (fs_id)
        ON DELETE SET NULL
)
""".strip()

CREATE_OBSERVATIONS_TABLE: str = """
CREATE TABLE IF NOT EXISTS observations (
    fs_id TEXT,
    station_id INTEGER,
    observer_id INTEGER,
    start_time TEXT,
    end_time TEXT,
    species TEXT,
    call_intensity TEXT,
    temperature REAL,
    beaufort_wind TEXT,
    precip_48h TEXT,
    precip TEXT,
    above_freezing_48h TEXT,
    notes TEXT,
    PRIMARY KEY (fs_id),
    FOREIGN KEY (observer_id)
        REFERENCES persons (fs_id)
        ON DELETE SET NULL,
    FOREIGN KEY (station_id)
        REFERENCES stations (fs_id)
        ON DELETE SET NULL
)
""".strip()


def create_tables(db: sqlite3.Connection) -> None:
    """Create the tables needed to store the Frogwatch data we are pulling
    from Fieldscope.
    """
    cur = db.cursor()
    cur.execute(ENABLE_FOREIGN_KEYS)
    cur.execute(CREATE_PERSONS_TABLE)
    cur.execute(CREATE_STATIONS_TABLE)
    cur.execute(CREATE_OBSERVATIONS_TABLE)
    db.commit()


PERSON_IDS_QUERY = """SELECT fs_id from persons"""
STATION_IDS_QUERY = """SELECT fs_id from stations"""
OBSERVATION_IDS_QUERY = """SELECT fs_id from observations"""

INSERT_PERSON_QUERY = """INSERT INTO persons VALUES (?, ?, ?)"""

INSERT_STATION_QUERY = """INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""

INSERT_OBSERVATION_QUERY = """INSERT INTO observations VALUES
                              (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""


def update_persons(db: sqlite3.Connection, people: dict[FS_id, Person]) -> None:
    """Add persons from the given dict to the database, if they're not
    already there.
    """
    cur = db.cursor()
    person_ids = [v[0] for v in cur.execute(PERSON_IDS_QUERY)]
    for v in people.values():
        if v.fs_id not in person_ids:
            cur.execute(INSERT_PERSON_QUERY, (v.fs_id, v.name, v.email))
    db.commit()


def update_stations(db: sqlite3.Connection, stations: dict[FS_id, Station]) -> None:
    """Add stations from the given dict to the database, if they're not
    already there.
    """
    cur = db.cursor()
    station_ids = [v[0] for v in cur.execute(STATION_IDS_QUERY)]
    for v in stations.values():
        if v.fs_id not in station_ids:
            cur.execute(
                INSERT_STATION_QUERY,
                (
                    v.fs_id,
                    v.name,
                    v.lon,
                    v.lat,
                    v.city,
                    v.county,
                    v.state,
                    v.owner.fs_id,
                ),
            )
    db.commit()


def update_observations(
    db: sqlite3.Connection, observations: dict[FS_id, Observation]
) -> None:
    """Add observations from the given dict to the database, if they're not
    already there.
    """
    cur = db.cursor()
    obs_ids = [v[0] for v in cur.execute(OBSERVATION_IDS_QUERY)]
    for v in observations.values():
        if v.fs_id not in obs_ids:
            cur.execute(
                INSERT_OBSERVATION_QUERY,
                (
                    v.fs_id,
                    v.station.fs_id,
                    v.observer.fs_id,
                    v.start_time,
                    v.end_time,
                    v.species,
                    v.call_intensity,
                    v.temperature,
                    v.beaufort_wind,
                    v.precip_48h,
                    v.precip,
                    v.above_freezing_48h,
                    v.notes,
                ),
            )
    db.commit()
