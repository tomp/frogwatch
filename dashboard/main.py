"""
This is the code to create the main dashboard display.
"""
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool, PanTool, WheelZoomTool, ResetTool, TapTool
from bokeh.models import DataTable, DateFormatter, TableColumn
from bokeh.models import Circle, Paragraph
from bokeh.layouts import layout

from bokeh.plotting import gmap, curdoc
from bokeh.models import GMapOptions

from datetime import datetime
import math

from .data import load_observations

print("Hello World!")


# Google API key for map display
api_key = "AIzaSyD4IiUSTkgTTe800sjX5LIuVhUsAFsRqG4"


def now():
    return datetime.now().isoformat()


def something_changed(attrname, old, new):
    print(attrname + " " + repr(old))

def obs_selected(attrname, old, new):
    print(f"{now()} - observation selected")
    status.text = f"observations {obs_table.source.selected.indices} selected"


station_obs, smr_observations = load_observations()

all_stations = set(station_obs['name'])
selected_stations = all_stations
print(f"{len(selected_stations)} stations")

all_species = set(smr_observations['species'])
selected_species = all_species
print(f"{len(selected_species)} species")

all_observers = set(smr_observations['name_observer'])
selected_observers = all_observers
print(f"{len(selected_observers)} observers")
    
def stations_selected(attrname, old, new):
    print(f"{now()} - station selected")
    global selected_stations
    selected_stations = list(station_obs['name'][station_source.selected.indices]) or all_stations
    # status.text = f"Selected stations {', '.join(selected_stations)}"
    species_selected = all_species
    update_panels()
    
def species_selected(attrname, old, new):
    print(f"{now()} - species selected")
    global selected_species
    try:
        selected_species = [
            species_table.source.data['species'][idx] for idx in species_table.source.selected.indices
        ] or all_species
    except IndexError:
        selected_species = all_species
    # status.text = f"Selected species {', '.join(selected_species)}"
    update_panels()
    
def observer_selected(attrname, old, new):
    print(f"{now()} - observer selected")
    global selected_observers
    try:
        selected_observers = [
            people_table.source.data['name_observer'][idx] for idx in people_table.source.selected.indices
        ] or all_observers
    except IndexError:
        selected_observers = all_observers
    # status.text = f"Selected observers {', '.join(selected_observers)}"
    update_panels()
    
def update_panels():
    station_filter = smr_observations['name_station'].isin(selected_stations)
    species_filter = smr_observations['species'].isin(selected_species)
    observer_filter = smr_observations['name_observer'].isin(selected_observers)
    filtered_observations = smr_observations[
        station_filter & species_filter & observer_filter
    ]
    print(f"{len(filtered_observations)} filtered observations")
    obs_table.source = obs_source(filtered_observations)
    species_table.source=species_source(filtered_observations)
    people_table.source=people_source(filtered_observations)

# There may be stations that have no observations, so we define this source independently of the observations
station_source = ColumnDataSource(
    data=dict(
        lat=station_obs['lat'],
        lon=station_obs['lon'],
        name=station_obs['name'],
        count=station_obs['observations'],
        size=[10 + 7*math.log(v + 1) for v in station_obs['observations']],
    )
)

station_source.selected.on_change('indices', stations_selected)
    
def obs_source(observations):
    column_source = ColumnDataSource(
        data=dict(
            obs_time=observations['start_time'],
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
                          width=400, height=240, margin=(30, 5, 5, 5), 
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
                          width=400, height=320, margin=(30, 5, 5, 5), 
                          index_position=None)

station_map = create_station_map(station_source, api_key)
obs_table = create_observations_table()
# species_table = create_species_table()
# people_table = create_people_table()
status = Paragraph()

status.text = "all observations"
print(status.text)

curdoc().add_root(layout(
    [[station_map, [species_table, people_table]], [obs_table], [status]])
)

