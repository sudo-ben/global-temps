import unittest
import snapshottest
import numpy as np

from process_data import (
    preprocess,
    load_data,
    column_dtypes,
    build_city_df,
    calc_monthly,
)


class TestStringMethods(unittest.TestCase):
    def test_load_data(self):
        df = preprocess(load_data)

        # check temperature values
        self.assertEqual(df.loc[df.AvgTemperature < -100, "AvgTemperature"].count(), 0)
        self.assertEqual(df.loc[df.AvgTemperature > 200, "AvgTemperature"].count(), 0)

        non_null_cols = df.drop(columns=["State", "AvgTemperature"])
        nan_rows = non_null_cols[non_null_cols.isnull().T.any()]
        # check for nan, nulls, empty str
        self.assertEqual(
            len(nan_rows),
            0,
            nan_rows,
        )
        city_country = df["CityCountry"]
        self.assertFalse(city_country.isnull().any().any())

        self.assertEqual(
            len(np.where(city_country == "")[0]),
            0,
            np.where(city_country == "")[0],
        )

    def test_build_city_df(self):
        df = preprocess(load_data)

        # check columns
        self.assertRaises(LookupError, build_city_df, df, "test", False)
        build_city_df(df, "Abilene, Texas, US", False)

    def test_calc_monthly(self):
        df = preprocess(load_data)

        # check columns
        calc_monthly(build_city_df(df, "Abilene, Texas, US", False))


class TestSnapshot(snapshottest.TestCase):
    def test_snapshot_match(self):
        df = preprocess(load_data)
        self.assertMatchSnapshot(df.info(), "df_info")
        self.assertMatchSnapshot(df.describe(datetime_is_numeric=True), "df_describe")


if __name__ == "__main__":
    unittest.main()