import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import decimal, os
from typing import List
import json
import urllib.request, json
import time
import urllib
import json


def column_dtypes() -> dict:
    return {
        "Date": "datetime64[ns]",
        "AvgTemperature": decimal.Decimal,
        "CityCountry": "string",
        "Region": "category",
        "Country": "category",
        "State": "category",
        "City": "category",
    }


def days_since_first_measure(df: pd.DataFrame) -> pd.Series:
    """Returns: pd.Series with days before first date in data"""
    return (df["Date"] - df["Date"].min()).dt.days


def city_country_key(df: pd.DataFrame) -> pd.Series:
    """
    Return: a unquie key for a city. Some cities with the same name so
    City column cannot be a key
    """

    return (
        df["City"].astype("string")
        + ", "
        + np.where(df["State"].isnull(), "", df["State"].astype("string") + ", ")
        + df["Country"].astype("string")
    )


def load_city_lat_long() -> pd.DataFrame:
    """
    Load lat long city json
    """

    with open(os.path.join("data", "cities_lat_long.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_data() -> pd.DataFrame:
    """
    Load temperature data and return as Panda DataFrame
    """
    # if missing download from https://www.kaggle.com/sudalairajkumar/daily-temperature-of-major-cities
    return pd.read_csv(
        os.path.join("data", "city_temperature.csv"),
        dtype={
            "Year": "Int16",
            "Month": "Int8",
            "Day": "Int8",
            "Region": "category",
            "Country": "category",
            "State": "category",
            "City": "category",
        },
        converters={"AvgTemperature": decimal.Decimal},
    )


def preprocess(load_data) -> pd.DataFrame:
    """Format the data for processing"""
    pickle_file = os.path.join("data", "city_temperature.pkl")
    if os.path.isfile(pickle_file):
        df = pd.read_pickle(pickle_file)
        return df
    else:
        df = load_data()

        # "Occasionally, problems with weather station metering equipment result
        # in missing average daily temperatures.  We denote missing data using a “–99” flag."
        # http://academic.udayton.edu/kissock/http/Weather/missingdata.htm
        df.loc[df["AvgTemperature"] == decimal.Decimal(-99), "AvgTemperature"] = np.nan

        # fahrenheit to celsius
        df.loc[:, "AvgTemperature"] = (
            df["AvgTemperature"] - decimal.Decimal(32)
        ) * decimal.Decimal(5 / 9)

        df.drop_duplicates(inplace=True)

        #  & (df["Year"] < 2020) remove incomplete year 2020
        # remove invalid years and day
        df = df.loc[(df["Year"] > 1990) & (df["Day"] != 0)]

        assert df["Day"].min() >= 1
        assert df["Day"].min() <= 31
        assert df["Month"].min() >= 1
        assert df["Month"].min() <= 12
        assert df["Year"].min() > 1990
        assert df["Year"].min() <= 2020

        df.loc[:, "Date"] = pd.to_datetime(df[["Year", "Month", "Day"]], utc=True)
        df.loc[:, "CityCountry"] = city_country_key(df)

        df = df[column_dtypes().keys()]

        df.to_pickle(pickle_file)

        return df


def build_city_df(df: pd.DataFrame, city_country: str, is_fahrenheit: bool):
    """
    Extract city DataFrame from data using key city_country
    """
    city_df = df[df.CityCountry == city_country].copy()
    if len(city_df) == 0:
        err_str = f"City not found {city_country}"
        raise LookupError(err_str)

    city_df = city_df.set_index(pd.DatetimeIndex(city_df.Date))
    city_df.drop(
        columns=["CityCountry", "Region", "Country", "State", "City", "Date"],
        inplace=True,
    )

    if is_fahrenheit:
        city_df["AvgTemperature"] = (
            city_df["AvgTemperature"] / decimal.Decimal(5 / 9)
        ) + decimal.Decimal(32)

    return city_df


def data_summary(df):
    regions_covered = ", ".join(df.Region.unique())
    cites_num = len(df.City.unique())

    return f"""This website displays daily temperatures from {cites_num} cities, covering {len(df.Country.unique())} countries and the following regions of {regions_covered}.
The first recorded day is {df.Date.min().strftime('%b, %Y')} and the last {df.Date.max().strftime('%b, %Y')}.

The website uses air temperature data made available by University of Dayton [link](http://academic.udayton.edu/kissock/http/Weather/default.htm).

The goal of this project is to make apparent any trends in the city temperature data. Each year is rendered on the charts in a different color"""
