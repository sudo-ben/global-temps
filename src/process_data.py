import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import decimal, os
from typing import List
import json
import urllib.request, json
import time
import urllib
import json

all_filenames = [
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "data",
        "daily_temperature_1000_cities_1980_2020.csv",
    ),
]


def build_city_lookup():
    """
    First 12 rows contain information about cities and no temperture data.
    Extract the rows and transform into useful lookup table
    """
    city_lookup = pd.read_csv(all_filenames[0], nrows=12).T
    city_lookup.columns = city_lookup.iloc[0]
    city_lookup = city_lookup.iloc[1:, :]
    city_lookup["lat"] = city_lookup["lat"].astype(np.float)
    city_lookup["lng"] = city_lookup["lng"].astype(np.float)
    return city_lookup


def build_reduced_city_lookup():
    """
    Convert city_lookup types and assert data is valid
    """
    city_lookup = build_city_lookup()

    # First 12 rows are information about the cities
    city_lookup = build_city_lookup()
    city_lookup = city_lookup[["city", "country", "lat", "lng", "population"]]
    city_lookup.loc[:, "population"] = (
        city_lookup["population"].fillna(0).astype(float).astype(np.uint)
    )

    assert len(city_lookup) == len(city_lookup.drop_duplicates())
    non_null = city_lookup[["city", "country", "lat", "lng"]]
    assert len(non_null[non_null.isnull().T.any()]) == 0, non_null[
        non_null.isnull().T.any()
    ]

    assert (
        city_lookup.loc[
            (city_lookup["lat"] < -90) | (city_lookup["lat"] > 90), "lat"
        ].count()
        == 0
    )
    assert (
        city_lookup.loc[
            (city_lookup["lng"] < -180) | (city_lookup["lng"] > 180), "lng"
        ].count()
        == 0
    )

    return city_lookup


def city_by_name(city_lookup, city_name: str):
    """Lookup col of city and call city_by_index"""
    city_col = city_lookup[city_lookup["city"] == city_name]
    city_index = int(city_col.index[0])

    return city_by_index(city_index), city_col


def city_by_index(city_col: int):
    """Read only one col from the csv that contains the city we are interested in"""
    city_data = pd.read_csv(
        all_filenames[0],
        skiprows=12,
        usecols=[0, city_col + 1],
        index_col=0,
        parse_dates=True,
        cache_dates=False,
    ).iloc[:, 0]

    return city_data


def build_reduced_city_lookup():
    """
    Convert city_lookup types and assert data is valid
    """
    city_lookup = build_city_lookup()

    # First 12 rows are information about the cities
    city_lookup = build_city_lookup()
    city_lookup = city_lookup[["city", "country", "lat", "lng", "population"]]
    city_lookup.loc[:, "population"] = (
        city_lookup.population.fillna(0).astype(float).astype(np.uint)
    )

    assert len(city_lookup) == len(city_lookup.drop_duplicates())
    non_null = city_lookup[["city", "country", "lat", "lng"]]
    assert len(non_null[non_null.isnull().T.any()]) == 0, non_null[
        non_null.isnull().T.any()
    ]

    assert (
        city_lookup.loc[
            (city_lookup["lat"] < -90) | (city_lookup["lat"] > 90), "lat"
        ].count()
        == 0
    )
    assert (
        city_lookup.loc[
            (city_lookup["lng"] < -180) | (city_lookup["lng"] > 180), "lng"
        ].count()
        == 0
    )

    return city_lookup


def data_summary(city_lookup, sample_city):
    sample_city = city_by_index(0)
    return f"""#### Data
This data contains daily temperatures for {len(city_lookup)} cities coving a population of at least {city_lookup["population"].sum():,} and {len(city_lookup["country"].unique())} countries. The first recorded day is {sample_city.index.min().strftime('%d %B, %Y')} and the last {sample_city.index.max().strftime('%d %B, %Y')}.
    
The website uses air temperature data made available by the Copernicus Climate Service.

* Raw temperature data from [https://cds.climate.copernicus.eu](https://cds.climate.copernicus.eu)
* City data from [https://simplemaps.com/](https://simplemaps.com/data/world-cities)
* Time-series extracted via [https://oikolab.com](https://oikolab.com)
[Data license](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode)

The goal of this project is to make apparent any trends in the city temperature data. Each year is rendered on the charts in a different color
"""