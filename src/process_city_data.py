import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)


def calc_monthly(city_df: pd.DataFrame):
    city_df["AvgTemperature"] = city_df["AvgTemperature"].astype(float)
    city_df_mean = city_df.groupby([city_df.index.year, city_df.index.month])[
        "AvgTemperature"
    ].mean()

    city_df_mean.index = city_df_mean.index.set_names(["Year", "Month"])

    city_df_mean = city_df_mean.unstack()

    return city_df_mean


def calc_yearly(city_df: pd.DataFrame):
    city_df["AvgTemperature"] = city_df["AvgTemperature"].astype(float)
    city_df_years = city_df.groupby([city_df.index.year])

    return city_df_years


def day_of_year_pivot(city_df: pd.DataFrame, city_country: str):
    city_df["Day of year"] = city_df.index.dayofyear
    city_df["Year"] = city_df.index.year
    city_df["AvgTemperature"] = city_df["AvgTemperature"].astype(float)

    return (
        pd.pivot_table(
            city_df,
            values="AvgTemperature",
            index=["Day of year"],
            columns=["Year"],
        )
        .bfill()
        .ffill()
    )
