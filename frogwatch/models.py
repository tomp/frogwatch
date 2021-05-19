"""
Data models for the Frogwatch project.
"""
from datetime import datetime
from dataclasses import dataclass

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
