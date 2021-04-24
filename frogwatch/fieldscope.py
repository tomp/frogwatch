"""
Constants and functions to support Fieldscope API queries for Frogwatch.
"""
from typing import Any, Optional, Union
from datetime import datetime

LonLat = list[float, float]
Geofence = list[LonLat]

# constants
API_PREFIX = "https://frogwatch.next.fieldscope.org/api/v3/"
SCHEMA_URL = API_PREFIX + "schema/frogwatch/"
QUERY_URL = SCHEMA_URL + "query?f=json"
STATIONS_URL = API_PREFIX + "station/?schema=frogwatch&sessionid=&f=pjson"

ALL_FIELDS = [
    "City",
    "County",
    "State",
    "FrogWatch_Chapter",
    "FrogWatch_LandUse",
    "FrogWatch_Habitat",
    "FrogWatch_WetlandOrigin",
    "FrogWatch_WaterPresence",
    "FrogWatch_WaterSource",
    "Description",
    "DirectionsToSite",
    "StartTime",
    "EndTime",
    "AirTemperature",
    "BeaufortWind",
    "FrogWatch_Precipitation",
    "FrogWatch_PrecipitationLast48",
    "FrogWatch_AboveFreezingLast48",
    "FrogWatch_SpeciesId",
    "FrogWatch_CallIntensity",
    "Notes",
]

OBS_FIELDS = [
    "City",
    "County",
    "State",
    "StartTime",
    "EndTime",
    "AirTemperature",
    "BeaufortWind",
    "FrogWatch_Precipitation",
    "FrogWatch_PrecipitationLast48",
    "FrogWatch_AboveFreezingLast48",
    "FrogWatch_SpeciesId",
    "FrogWatch_CallIntensity",
    "Notes",
]


SMR_CIRCLE: Geofence = [
    [-74.29012826552825, 40.791803637617120],
    [-74.28499313592775, 40.791612530497130],
    [-74.27990754836033, 40.791041052884930],
    [-74.27492056435436, 40.790094718141070],
    [-74.27008028918730, 40.788782655767490],
    [-74.26543340560549, 40.787117522877160],
    [-74.26102472161640, 40.785115381480780],
    [-74.25689673680961, 40.782795542803900],
    [-74.25308923146618, 40.780180380172574],
    [-74.24963888247464, 40.777295112313160],
    [-74.24657890979006, 40.774167559201120],
    [-74.24393875685270, 40.770827872859280],
    [-74.24174380803031, 40.767308245747590],
    [-74.24001514576600, 40.763642599600125],
    [-74.23876934970794, 40.759866257749344],
    [-74.23801833967106, 40.756015604131530],
    [-74.23776926384174, 40.752127732288230],
    [-74.23802443318601, 40.748240087767186],
    [-74.23878130256790, 40.744390107380276],
    [-74.24003249863001, 40.740614858797220],
    [-74.24176589403852, 40.736950683940750],
    [-74.24396472725326, 40.733432849602510],
    [-74.24660776655601, 40.730095208621400],
    [-74.24966951665739, 40.726969874855410],
    [-74.25312046581168, 40.724086915039210],
    [-74.25692737099948, 40.721474060451435],
    [-74.26105357839549, 40.719156441121640],
    [-74.26545937602323, 40.717156345087540],
    [-74.27010237521411, 40.715493004972494],
    [-74.27493791723556, 40.714182413891706],
    [-74.27991950123344, 40.713237172417124],
    [-74.28499922944984, 40.712666368036864],
    [-74.29012826552825, 40.712475488239484],
    [-74.29525730160667, 40.712666368036864],
    [-74.30033702982308, 40.713237172417124],
    [-74.30531861382096, 40.714182413891706],
    [-74.31015415584240, 40.715493004972494],
    [-74.31479715503329, 40.717156345087540],
    [-74.31920295266102, 40.719156441121640],
    [-74.32332916005704, 40.721474060451435],
    [-74.32713606524484, 40.724086915039210],
    [-74.33058701439913, 40.726969874855410],
    [-74.33364876450051, 40.730095208621400],
    [-74.33629180380326, 40.733432849602510],
    [-74.33849063701800, 40.736950683940750],
    [-74.34022403242649, 40.740614858797220],
    [-74.34147522848862, 40.744390107380276],
    [-74.34223209787051, 40.748240087767186],
    [-74.34248726721478, 40.752127732288230],
    [-74.34223819138546, 40.756015604131530],
    [-74.34148718134858, 40.759866257749344],
    [-74.34024138529053, 40.763642599600125],
    [-74.33851272302621, 40.767308245747590],
    [-74.33631777420382, 40.770827872859280],
    [-74.33367762126646, 40.774167559201120],
    [-74.33061764858188, 40.777295112313160],
    [-74.32716729959034, 40.780180380172574],
    [-74.32335979424691, 40.782795542803900],
    [-74.31923180944013, 40.785115381480780],
    [-74.31482312545103, 40.787117522877160],
    [-74.31017624186921, 40.788782655767490],
    [-74.30533596670215, 40.790094718141070],
    [-74.30034898269618, 40.791041052884930],
    [-74.29526339512876, 40.791612530497130],
    [-74.29012826552825, 40.791803637617120],
]

SMR_OUTLINE: Geofence = [
    [-74.307884216832463, 40.725040712683722],
    [-74.314407349156681, 40.729203572851702],
    [-74.316467285680119, 40.735967665228145],
    [-74.313034058141056, 40.740129841822124],
    [-74.308914185094181, 40.744291757996670],
    [-74.305137634801213, 40.751574484650860],
    [-74.301361084508244, 40.755995750994934],
    [-74.300674439000431, 40.761196864392325],
    [-74.301361084508244, 40.768477739470100],
    [-74.297241211461369, 40.771077858690852],
    [-74.296554565953556, 40.776537777880144],
    [-74.287284851598088, 40.795254094293441],
    [-74.276298523473088, 40.787196326908393],
    [-74.283164978551213, 40.776537777880144],
    [-74.284194946812931, 40.770817851347168],
    [-74.269432068394963, 40.772377880147765],
    [-74.280349731707247, 40.752536784504741],
    [-74.282238006853731, 40.748375384302832],
    [-74.278633117937716, 40.746294586540046],
    [-74.283096313738483, 40.741612553527524],
    [-74.288761139177950, 40.736539979157769],
    [-74.295284271502169, 40.731206855699071],
    [-74.302665710711153, 40.725483028146499],
    [-74.307884216832463, 40.725040712683722],
]


def area_filter(outline: Geofence) -> dict[str, Any]:
    """Return a Fieldscope area filter, based on the given geofence."""
    return {
        "within": {
            "sourceId": "circle",
            "rings": [outline],
            "spatialReference": {"wkid": 4326},
        },
        "enabled": True,
        "label": "Filter by area",
    }


def state_filter(state: Union[str, list[str]]) -> dict[str, Any]:
    """Return a Fieldscope state filter, based on the given state code, or
    list of state codes.
    """
    if isinstance(state, list):
        state_list = state
    else:
        state_list = [state]
    return {
        "field": "State",
        "in": state_list,
        "enabled": True,
        "label": "Filter by value",
    }


def chapter_filter(chapter: Union[str, list[str]]) -> dict[str, Any]:
    """Return a Fieldscope chapter filter, based on the given group id.
    """
    if isinstance(chapter, list):
        chapter_list = [str(v) for v in chapter]
    else:
        chapter_list = [str(chapter)]
    return {
        "field": "Frogwatch_Chapter",
        "oneof": chapter_list,
        "enabled": True,
        "label": "Filter by group",
    }


def user_filter(user: Union[int, list[int]]) -> dict[str, Any]:
    """Return a Fieldscope user filter, based on the given group id.
    """
    if isinstance(user, list):
        user_list = [int(v) for v in user]
    else:
        user_list = [int(user)]
    return {
        "field": "user",
        "oneof": user_list,
        "enabled": True,
        "label": "Filter by user",
    }


def date_filter(
    start: Optional[datetime] = None, end: Optional[datetime] = None
) -> dict[str, Any]:
    """Return a Fieldscope time range filter, based on the given starting and
    ending dates.
    """
    if not start:
        start = datetime(1990, 1, 1)
    if not end:
        end = datetime.now()
    return {
        "begin": int(start.timestamp()),
        "end": int(end.timestamp()),
        "enabled": True,
        "label": "Filter by date",
    }


def query_body(
    outline: Optional[Geofence] = None,
    state: Optional[str] = None,
    chapter: Optional[int] = None,
    user: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """Return the body to be used in the frogwatch query."""
    filters = ["and"]
    if outline:
        filters.append(area_filter(outline))
    if state:
        filters.append(state_filter(state))
    if chapter:
        filters.append(chapter_filter(chapter))
    if user:
        filters.append(user_filter(user))
    if start_date or end_date:
        filters.append(date_filter(start_date, end_date))
    if len(filters) == 1:
        return {}

    return {
        "fields": ALL_FIELDS,
        "filters": filters,
    }
