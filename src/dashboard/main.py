"""
This is the code to create the main dashboard display.
"""
import os
import math
from datetime import datetime, date

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool, PanTool, WheelZoomTool, BoxZoomTool, ResetTool, TapTool
from bokeh.models import DataTable, DateFormatter, TableColumn
from bokeh.models import DatetimeTickFormatter
from bokeh.models import Circle, Paragraph
from bokeh.layouts import layout

from bokeh.plotting import gmap, curdoc
from bokeh.models import GMapOptions

# import psycopg2 as pg

# from . import db_postgres as db
from . import db_sqlite as db
from .data import load_observations

print("Peep, peep, peep!")


# Google API key for map display
GMAP_API_KEY = "AIzaSyD4IiUSTkgTTe800sjX5LIuVhUsAFsRqG4"

# local database connection string.  On Heroku we'll get this from $DATABASE_URL
# DEFAULT_DATABASE_URL = "postgresql://pollard@localhost:5432/frogwatch"
DEFAULT_DATABASE_URL = "frogwatch.db"

MONTH = [""] + [date(2000, v, 1).strftime('%b') for v in range(1, 13)]
MONTH_MILLIS = 30 * 24 * 60 * 60 * 1000


db_url = os.getenv("DATABASE_URL", default=DEFAULT_DATABASE_URL)
print(f"DATABASE_URL: {db_url}")

station_obs, smr_observations = load_observations(db_url)

all_stations = set(station_obs['name'])
selected_stations = all_stations
print(f"{len(selected_stations)} stations")

all_species = set(smr_observations['species'])
selected_species = all_species
print(f"{len(selected_species)} species")

all_observers = set(smr_observations['name_observer'])
selected_observers = all_observers
print(f"{len(selected_observers)} observers")


def now():
    return datetime.now().isoformat()

def year_start(dt):
    return dt.replace(month=1, day=1, hour=0, minute=0, second=0)

def year_end(dt):
    return dt.replace(month=12, day=31, hour=0, minute=0, second=0)
    
min_obs_time = year_start(min(smr_observations['obs_datetime']))
max_obs_time = year_end(max(smr_observations['obs_datetime']))
max_year_month_count = max(smr_observations.groupby('obs_year_month').size())
max_week_count = max(smr_observations.groupby('obs_week').size())
max_month_count = max(smr_observations.groupby('obs_month').size())

full_date_range = [min_obs_time, max_obs_time]
selected_date_range = list(full_date_range)


def something_changed(attrname, old, new):
    print(attrname + " " + repr(old))

def obs_selected(attrname, old, new):
    print(f"{now()} - observation selected")
    status.text = f"observations {obs_table.source.selected.indices} selected"


# If updating is true, we're in the middle of a data source update, 
# and the usual selection callbacks should be suppressed.
updating = False
    
def stations_selected(attrname, old, new):
    global selected_stations
    if not updating:
        print(f"{now()} - station selected")
        selected_stations = list(
            station_obs['name'][station_source.selected.indices]
        ) or all_stations
        update_panels()
    
def species_selected(attrname, old, new):
    global selected_species
    if not updating:
        print(f"{now()} - species selected")
        try:
            selection = species_table.source.selected.indices
            selected_species = [
                species_table.source.data['species'][idx] for idx in selection
            ] or all_species
        except IndexError:
            selected_species = all_species
        update_panels()

def observer_selected(attrname, old, new):
    global selected_observers
    if not updating:
        print(f"{now()} - observer selected")
        try:
            selection = people_table.source.selected.indices
            selected_observers = [
                people_table.source.data['name_observer'][idx] for idx in selection
            ] or all_observers
        except IndexError:
            selected_observers = all_observers
        update_panels()
        
def select_stations_by_name(stations):
    station_source.selected.indices = list(
        station_obs[station_obs['name'].isin(stations)].index
    )
    print(f"set station indices to {station_source.selected.indices}")

def unselect_stations():
    station_source.selected.indices = []
    print(f"reset station indices to {station_source.selected.indices}")

def update_panels():
    global updating
    if not updating:
        updating = True
        station_filter = smr_observations['name_station'].isin(selected_stations)
        species_filter = smr_observations['species'].isin(selected_species)
        observer_filter = smr_observations['name_observer'].isin(selected_observers)
        filtered_observations = smr_observations[
            station_filter & species_filter & observer_filter
        ]

        # if observations have been filtered, highlight the stations where they were made.
        if len(filtered_observations) == len(smr_observations):
            unselect_stations()
        elif len(selected_stations) == len(all_stations):
            select_stations_by_name(filtered_observations['name_station'].unique())
        
        obs_table.source = obs_source(filtered_observations)
        species_table.source=species_source(filtered_observations)
        people_table.source=people_source(filtered_observations)

        obs_date_histogram.renderers[0].data_source.data = dict(obs_time_source(filtered_observations).data)
        obs_date_histogram.y_range.end = 1.1 * max(obs_date_histogram.renderers[0].data_source.data['count'])

        obs_month_histogram.renderers[0].data_source.data = dict(obs_month_source(filtered_observations).data)
        obs_month_histogram.y_range.end = 1.1 * max(obs_month_histogram.renderers[0].data_source.data['count'])

        updating = False


# There may be stations that have no observations, so we define this source independently of the observations
station_source = ColumnDataSource(
    data=dict(
        lat=station_obs['lat'],
        lon=station_obs['lon'],
        name=station_obs['name'],
        count=station_obs['observations'],
        size=[15 + 5*math.log(v + 1) for v in station_obs['observations']],
    )
)

station_source.selected.on_change('indices', stations_selected)
    
def obs_source(observations):
    column_source = ColumnDataSource(
        data=dict(
            obs_time=observations['obs_datetime'],
            station=observations['name_station'],
            observer=observations['name_observer'],
            species=observations['species'],
            intensity=observations['call_intensity'],
            temperature=observations['temperature'],
            wind=observations['beaufort_wind'],
        )
    )
    column_source.selected.on_change('indices', obs_selected)
    return column_source

def species_source(observations):
    by_species = observations.groupby('species')
    names = list(by_species.size().sort_values(ascending=False).keys())
    groups = dict(list(by_species))
    
    count, observers, sites = list(), list(), list()
    for species in names:
        group = groups[species]
        count.append(len(group))
        observers.append(len(group['name_observer'].unique()))
        sites.append(len(group['name_station'].unique()))
    column_source = ColumnDataSource(
        data=dict(
            species=names,
            observations=count,
            observers=observers,
            stations=sites
        )
    )
    column_source.selected.on_change('indices', species_selected)
    return column_source

def people_source(observations):
    by_observer = observations.groupby('name_observer')
    names = list(by_observer.size().sort_values(ascending=False).keys())
    groups = dict(list(by_observer))
    
    count, species, sites = list(), list(), list()
    for observer in names:
        group = groups[observer]
        count.append(len(group))
        species.append(len(group['species'].unique()))
        sites.append(len(group['name_station'].unique()))
    column_source = ColumnDataSource(
        data=dict(
            name_observer=names,
            observations=count,
            species=species,
            stations=sites
        )
    )
    column_source.selected.on_change('indices', observer_selected)
    return column_source

       
def obs_time_source(observations):
    by_year_month = observations.groupby('obs_year_month')
    months = list(by_year_month.groups.keys())
    column_source = ColumnDataSource(
        data=dict(
            obs_year_month=months,
            date=[v.strftime('%b %Y') for v in months],
            count=list(by_year_month.size().values)
        )
    )
    # print(column_source.__dict__)
    return column_source
     
def obs_month_source(observations):
    by_month = {month: 0 for month in range(1,13)}
    for month, obs in observations.groupby('obs_month'):
        by_month[month] = len(obs)
    column_source = ColumnDataSource(
        data=dict(
            obs_month=list(by_month.keys()),
            month=[MONTH[v] for v in by_month.keys()],
            count=list(by_month.values())
        )
    )
    return column_source

def create_date_histogram(observations):
    date_hover = HoverTool(tooltips=[
        ("month", "@date"),
        ("obs", "@count"),
    ])
    date_zoom = BoxZoomTool(dimensions="width")

    histogram = figure(x_range=(min_obs_time, max_obs_time), y_range=(0, max_year_month_count*1.1), 
             width=810, height=160, x_axis_type="datetime", 
             tools=[date_hover, date_zoom, PanTool(dimensions="width"), ResetTool()],
             active_drag=date_zoom,
             title="Observations by Year and Month")

    histogram.vbar(x='obs_year_month', top='count', bottom=0, width=MONTH_MILLIS * 0.8, 
         source=obs_time_source(observations))
    histogram.xaxis[0].formatter = DatetimeTickFormatter(months="%b %Y")
    return histogram


def create_month_histogram(observations):
    month_hover = HoverTool(tooltips=[
        ("month", "@month"),
        ("obs", "@count"),
    ])

    histogram = figure(x_range=(1, 12), y_range=(0, max_month_count*1.1), 
                      width=810, height=160, 
                      tools=[month_hover],
                      title="Observations by Month")
    histogram.vbar(x='obs_month', top='count', bottom=0, width=0.8, 
                  source=obs_month_source(observations))
    # print(obs_date_histogram.y_range)
    return histogram


def create_station_map(station_source, api_key):
    """ SMR station map."""
    map_options = GMapOptions(lat=40.752, lng=-74.294, map_type="terrain", zoom=14)

    hover = HoverTool(tooltips=[
        ("site", "@name"),
    ])

    station_map = gmap(api_key, map_options,
                       tools=[hover, WheelZoomTool(), PanTool(), ResetTool(), TapTool()],
                       width=400,
                       title="South Mountain Reservation")

    renderer = station_map.circle(x="lon", y="lat", size="size", 
                       fill_color="violet", fill_alpha=0.5,
                       hover_fill_alpha=1.0,
                       source=station_source)

    selected_circle = Circle(fill_alpha=1.0, fill_color="violet")
    nonselected_circle = Circle(fill_alpha=0.0, fill_color="violet")

    renderer.selection_glyph = selected_circle
    renderer.nonselection_glyph = nonselected_circle

    return station_map


def create_observations_table():
    """ Observations table """
    obs_columns = [
        TableColumn(field="obs_time", title="Observed at", formatter=DateFormatter()),
        TableColumn(field="station", title="Station"),
        TableColumn(field="observer", title="Observer"),
        TableColumn(field="species", title="Species"),
        TableColumn(field="intensity", title="Intensity"),
    ]

    obs_table = DataTable(source=obs_source(smr_observations), columns=obs_columns, 
                          width=810, height=320, index_position=None)

    return obs_table

# Species table
species_columns = [
    TableColumn(field="species", title="Species"),
    TableColumn(field="observations", title="Observed"),
    TableColumn(field="observers", title="Observers"),
    TableColumn(field="stations", title="Sites"),
]

species_table = DataTable(source=species_source(smr_observations), 
                          columns=species_columns, 
                          width=400, height=280, margin=(30, 5, 5, 5), 
                          index_position=None)
# Observers table
people_columns = [
    TableColumn(field="name_observer", title="Observer"),
    TableColumn(field="observations", title="Observed"),
    TableColumn(field="species", title="Species"),
    TableColumn(field="stations", title="Sites"),
]

people_table = DataTable(source=people_source(smr_observations), 
                          columns=people_columns, 
                          width=400, height=240, margin=(30, 5, 5, 5), 
                          index_position=None)

station_map = create_station_map(station_source, GMAP_API_KEY)
obs_date_histogram = create_date_histogram(smr_observations)
obs_month_histogram = create_month_histogram(smr_observations)
obs_table = create_observations_table()
# species_table = create_species_table()
# people_table = create_people_table()
status = Paragraph()

status.text = "all observations"
print(status.text)

curdoc().add_root(layout(
    [[station_map, [species_table, people_table]], [obs_date_histogram],
        [obs_month_histogram], [obs_table], [status]])
)

