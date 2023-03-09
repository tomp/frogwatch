"""
Data models for the Frogwatch project.
"""
import psycopg2 as pg

from .models import FS_id, Person, Station, Observation


# Constants
DEFAULT_DB_URI = "postgresql://pollard@localhost:5432/frogwatch"

# SQL
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
    lon DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    city TEXT,
    county TEXT,
    state TEXT,
    owner_id TEXT,
    PRIMARY KEY (fs_id),
    FOREIGN KEY (owner_id)
        REFERENCES persons (fs_id)
        ON DELETE SET NULL
)
""".strip()

CREATE_OBSERVATIONS_TABLE: str = """
CREATE TABLE IF NOT EXISTS observations (
    fs_id TEXT,
    station_id TEXT,
    observer_id TEXT,
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


def connect(pg_uri):
    """Open a connection to the Postgers database using the given connection URI."""
    return pg.connect(pg_uri)

def create_tables(conn) -> None:
    """Create the tables needed to store the Frogwatch data we are pulling
    from Fieldscope.
    """
    with conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_PERSONS_TABLE)
            cur.execute(CREATE_STATIONS_TABLE)
            cur.execute(CREATE_OBSERVATIONS_TABLE)


PERSON_IDS_QUERY = """SELECT fs_id from persons"""
STATION_IDS_QUERY = """SELECT fs_id from stations"""
OBSERVATION_IDS_QUERY = """SELECT fs_id from observations"""

INSERT_PERSON_QUERY = """INSERT INTO persons VALUES (%s, %s, %s)"""

INSERT_STATION_QUERY = """INSERT INTO stations VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

INSERT_OBSERVATION_QUERY = """INSERT INTO observations VALUES
                              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""


def update_persons(conn, people: dict[FS_id, Person]) -> None:
    """Add persons from the given dict to the database, if they're not
    already there.
    """
    with conn:
        with conn.cursor() as cur:
            cur.execute(PERSON_IDS_QUERY)
            person_ids = [v[0] for v in cur.fetchall()]
            for v in people.values():
                if v.fs_id not in person_ids:
                    cur.execute(INSERT_PERSON_QUERY, (v.fs_id, v.name, v.email))


def update_stations(conn, stations: dict[FS_id, Station]) -> None:
    """Add stations from the given dict to the database, if they're not
    already there.
    """
    with conn:
        with conn.cursor() as cur:
            cur.execute(STATION_IDS_QUERY)
            station_ids = [v[0] for v in cur.fetchall()]
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


def update_observations(
    conn, observations: dict[FS_id, Observation]
) -> None:
    """Add observations from the given dict to the database, if they're not
    already there.
    """
    with conn:
        with conn.cursor() as cur:
            cur.execute(OBSERVATION_IDS_QUERY)
            obs_ids = [v[0] for v in cur.fetchall()]
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
