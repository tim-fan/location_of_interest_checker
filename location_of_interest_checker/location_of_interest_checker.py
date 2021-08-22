"""Locations of Interest Checker.

Check current New Zealand COVID locations of interest against exported Google location history.

Input arguments are the path to the exported location history json, and the file underwhich
to save the results of the check.

The output csv contains a list of all locations of interest, along with a column specifying how
far (in km) you were from that location at that time. If any distances are less
than, say 0.1km, you should probably get a test and self isolate!

See https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-health-advice-public/contact-tracing-covid-19/covid-19-contact-tracing-locations-interest
for official list of locations of interest, and instructions on what to do if you have been at one.

Usage:
  location_of_interest_checker <location_history_file> <output_csv>

Options:
  -h --help     Show this screen.

"""

import json
import ijson
from docopt import docopt
from datetime import datetime
from pandas.core.frame import DataFrame
from pandas.core.tools.datetimes import DatetimeScalar
from pytz import timezone
import pandas as pd
import numpy as np
import geopandas
import geopy.distance
from shapely.geometry import Point
import plotly.express as px

def read_location_history_file(filename:str) -> geopandas.GeoDataFrame:

    # use simple time threshold to get rid of old data, for faster processing
    # used https://www.epochconverter.com/ to get the threshold timstamp
    # TODO: support user input of threshold time
    threshold_timestamp_ms = 1624241116000

    print(f"Loading location history from file: {filename}")

    location_list = []
    with open(filename, "r") as f:
        location_json_items = ijson.items(f, "locations.item")
        for location_item in location_json_items:
            if int(location_item['timestampMs']) < threshold_timestamp_ms:
                continue
            else:
                location_list.append(location_item)

    locations = pd.DataFrame(location_list)
    locations.timestampMs = pd.to_numeric(locations.timestampMs)

    # manual caching during development:
    # locations.to_csv("/tmp/locations_cache.csv")
    # locations = pd.read_csv("/tmp/locations_cache.csv", index_col=None)

    # get datetime from timestamps
    locations['time'] = locations.timestampMs.apply(lambda t: datetime.fromtimestamp(t*1e-3))
    locations['lat'] = locations.latitudeE7 * 1e-7
    locations['lon'] = locations.longitudeE7 * 1e-7

    # add location as geopandas geometry series
    geometry = []
    for _, row in locations.iterrows():
        geometry.append(Point(row.lon, row.lat))

    print(f"Location history loaded")

    return geopandas.GeoDataFrame(locations, geometry=geometry)

def create_demo_location_history() -> geopandas.GeoDataFrame: 
    """
    For running the tool without any actual location history data, generate some random lat/lon data
    """
    np.random.seed(123)

    time = pd.date_range(start=datetime.fromtimestamp(1624241116), end=datetime.now(), freq="1min").values

    center_point = (-36.875990410695394, 174.76398830024274)
    lat = np.random.normal(loc=center_point[0], scale=0.01, size=len(time))
    lon = np.random.normal(loc=center_point[1], scale=0.01, size=len(time))

    geometry = [Point(lon, lat) for lon, lat in zip(lon, lat)]
    return geopandas.GeoDataFrame(pd.DataFrame(dict(time=time, lat=lat, lon=lon)), geometry=geometry)
    
def read_locations_of_interest_file(filename:str):
    locations_of_interest = geopandas.read_file(filename)

    # parse time strings
    locations_of_interest.Start = locations_of_interest.Start.apply(parse_locations_of_interest_time_str)
    locations_of_interest.End = locations_of_interest.End.apply(parse_locations_of_interest_time_str)

    locations_of_interest["lat"] = locations_of_interest.geometry.apply(lambda point : point.y)
    locations_of_interest["lon"] = locations_of_interest.geometry.apply(lambda point : point.x)

    return locations_of_interest

def parse_locations_of_interest_time_str(time_str:str) -> datetime:
    """
    e.g.
    "11/08/2021, 9:30 am" -> datetime("2021-08-11 09:30:00")
    """
    return datetime.strptime(time_str, '%d/%m/%Y, %I:%M %p')


def point_to_point_distance(p1:Point, p2: Point) -> float:
    """
    Return distance between two lat/lon points in km
    """
    return round(geopy.distance.distance((p1.y, p1.x), (p2.y, p2.x)).km,2)
    

def get_distance_to_location_of_interest(location_of_interest:pd.Series, location_history:geopandas.GeoDataFrame) -> float:

    locations_in_window_indices = (location_history.time > location_of_interest.Start) & (location_history.time < location_of_interest.End)
    if not locations_in_window_indices.any():
        # if no location data available for the window of interest
        # print a warning and return nan distance

        print("Warning! no records found in location history at time of event - please check manually!")
        print_location_of_interest(location_of_interest)
        print()
        matching_location_history = pd.Series(dict(
            location_history_record_time= pd.to_datetime("nat"),
            distance_to_location_km= float('nan'),
            personal_lat=float('nan'),
            personal_lon=float('nan'),
            comment="No matching records found in location history",
        ))

    else:
        locations_in_window = location_history.loc[locations_in_window_indices,:]

        locations_in_window["distance_to_location_km"] = locations_in_window.apply(lambda location : point_to_point_distance(location.geometry, location_of_interest.geometry), axis=1 )

        matching_location_history = locations_in_window.iloc[np.argmin(locations_in_window.distance_to_location_km), :]
        matching_location_history = matching_location_history[["time", "distance_to_location_km", "lat", "lon"]].rename(dict(
            time="location_history_record_time",
            lat="personal_lat",
            lon="personal_lon",
        ))
        matching_location_history["comment"] = f"{locations_in_window_indices.sum()} matching records found in location history"

    return pd.concat([pd.Series(location_of_interest), pd.Series(matching_location_history)])

def plot_locations(locations_of_interest:geopandas.GeoDataFrame, location_history:geopandas.GeoDataFrame):

    # draw lines from personal location to location of interest
    lats = []
    lons = []
    for i, row in locations_of_interest.sort_values(by="distance_to_location_km").iloc[0:10,:].iterrows():
        lats = np.append(lats, [row.lat, row.personal_lat])
        lons = np.append(lons, [row.lon, row.personal_lon])
        lats = np.append(lats, None)
        lons = np.append(lons, None)
    fig = px.line_mapbox(lat=lats, lon=lons,
                     mapbox_style="carto-positron", zoom=6)            

    fig.add_trace(px.scatter_mapbox(locations_of_interest, lat="lat", lon="lon", hover_name="Event", hover_data=["Location", "Start", "End", "distance_to_location_km"],
                            color_discrete_sequence=["lightsalmon"]).data[0])

    fig.add_trace(
        px.scatter_mapbox(
            locations_of_interest,
            lat="personal_lat",
            lon="personal_lon",
            hover_name="location_history_record_time",
            color_discrete_sequence=["lightseagreen"],
            mapbox_style="carto-positron"
        ).data[0]
    )

    fig.update_layout(mapbox_style="carto-positron")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    # fig.write_html("./locations_of_interest.html")
    fig.show()

def print_location_of_interest(location:pd.Series):
    print(f"Event: {location.Event}\n"
          f"Time frame: {location.Start} to {location.End}")

def print_processing_report(locations_of_interest:geopandas.GeoDataFrame, location_history:geopandas.GeoDataFrame):
    num_matched_locations = (~locations_of_interest.distance_to_location_km.isna()).sum()
    num_unmatched_locations = (locations_of_interest.distance_to_location_km.isna()).sum()
    print()
    print()
    print(f"Matched {num_matched_locations} locations of interest to location history (out of {len(locations_of_interest.index)} total locations).")
    if num_unmatched_locations > 0:
        print(f"Warning: was unable to find personal location data for {num_unmatched_locations} locations of interest - please check these locations manually!")
    print()
    if num_matched_locations > 0:
        closest_location_of_interest = locations_of_interest.loc[np.argmin(locations_of_interest.distance_to_location_km)]
        print("Closest location of interest:")
        print_location_of_interest(closest_location_of_interest)
        print(f"You were {closest_location_of_interest.distance_to_location_km} km away.")
        print()

def main():
    arguments = docopt(__doc__)

    # read input data
    locations_of_interest_url = "https://raw.githubusercontent.com/minhealthnz/nz-covid-data/main/locations-of-interest/august-2021/locations-of-interest.geojson"
    locations_of_interest = read_locations_of_interest_file(locations_of_interest_url)

    demo = False
    if demo:
        location_history = create_demo_location_history()
    else:
        location_history = read_location_history_file(arguments['<location_history_file>'])
    
    # compute distance to locations of interest
    locations_of_interest = locations_of_interest.apply(lambda location: get_distance_to_location_of_interest(location, location_history),axis=1)

    # print a summary
    print_processing_report(locations_of_interest, location_history)

    # write results
    output_csv = arguments['<output_csv>']
    locations_of_interest.sort_values(by="distance_to_location_km").to_csv(output_csv, index=False)
    print(f"Annotated location of interest data writen to file {output_csv}")

    # plot
    plot_locations(locations_of_interest, location_history)




