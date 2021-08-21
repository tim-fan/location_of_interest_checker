"""Locations of Interest Checker.

Usage:
  location_of_interest_checker <locations_of_interest_file> <location_history_file> <output_csv>

Options:
  -h --help     Show this screen.

"""

import json
from docopt import docopt
from datetime import datetime
from pandas.core.tools.datetimes import DatetimeScalar
from pytz import timezone
import pandas as pd
import numpy as np
import geopandas
import geopy.distance
from shapely.geometry import Point
import plotly.express as px

def read_location_history_file(filename:str):

    # saving locations in a temp file for faster loading
    # during development
    from_cache = True

    if not from_cache:
        with open(filename, "r") as f:
            json_data = json.load(f)
        
        locations = pd.DataFrame(json_data['locations'])
        locations.timestampMs = pd.to_numeric(locations.timestampMs)

        # use simple time threshold to get rid of old data, for faster processing
        # used https://www.epochconverter.com/ to get the threshold timstamp
        # TODO: support user input of threshold time
        treshold_timestamp_ms = 1624241116000
        locations = locations.loc[locations.timestampMs > 1624241116000, :]

        # manual caching during development:
        locations.to_csv("/tmp/locations_cache.csv")

    else:
        locations = pd.read_csv("/tmp/locations_cache.csv", index_col=None)

    # get datetime from timestamps
    locations['time'] = locations.timestampMs.apply(lambda t: datetime.fromtimestamp(t*1e-3))

    # add location as geopandas geometry series
    geometry = []
    for _, row in locations.iterrows():
        geometry.append(Point(row.longitudeE7 * 1e-7, row.latitudeE7 * 1e-7))

    return geopandas.GeoDataFrame(locations, geometry=geometry)

def read_locations_of_interest_file(filename:str):
    locations_of_interest = geopandas.read_file(filename)

    # parse time strings
    locations_of_interest.Start = locations_of_interest.Start.apply(parse_locations_of_interest_time_str)
    locations_of_interest.End = locations_of_interest.End.apply(parse_locations_of_interest_time_str)

    # locations_of_interest["lat"] = locations_of_interest.geometry

    return locations_of_interest

def parse_locations_of_interest_time_str(time_str:str) -> datetime:
    """
    e.g.
    "11/08/2021, 9:30 am" -> datetime("2021-08-11 09:30:00")
    """
    return datetime.strptime(time_str, '%d/%m/%Y, %I:%M %p')

def get_location_at_time(time: datetime, location_history:geopandas.GeoDataFrame):
    """
    Return current location at the given time
    """
    nearest_time_in_history_index = np.argmin(np.abs(location_history.time - time))
    return location_history.geometry[nearest_time_in_history_index]

def point_to_point_distance(p1:Point, p2: Point) -> float:
    """
    Return distance between two lat/lon points in km
    """
    return geopy.distance.distance((p1.y, p1.x), (p2.y, p2.x)).km
    

def get_distance_to_location_of_interest(location_of_interest:pd.Series, location_history:geopandas.GeoDataFrame) -> float:

    location_at_start = get_location_at_time(location_of_interest.Start, location_history)
    location_at_end = get_location_at_time(location_of_interest.End, location_history)
    return min([
        point_to_point_distance(location_at_start, location_of_interest.geometry),
        point_to_point_distance(location_at_end, location_of_interest.geometry)
    ])


def main():
    arguments = docopt(__doc__)

    locations_of_interest_url = "https://raw.githubusercontent.com/minhealthnz/nz-covid-data/main/locations-of-interest/august-2021/locations-of-interest.geojson"

    # read input data
    location_history = read_location_history_file(arguments['<location_history_file>'])
    locations_of_interest = read_locations_of_interest_file(locations_of_interest_url)

    # compute distance to locations of interest
    locations_of_interest["distance_to_location_km"] = locations_of_interest.apply(lambda location: get_distance_to_location_of_interest(location, location_history),axis=1)

    # write results
    locations_of_interest.sort_values(by="distance_to_location_km").to_csv(arguments['<output_csv>'], index=False)

    fig = px.scatter(locations_of_interest, x="Start", y="distance_to_location_km", hover_data=["Event", "Location",])
    fig.show()
    # fig.write_html("./distance_to_location.html")


