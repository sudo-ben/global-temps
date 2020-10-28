import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)


def calc_monthly(city_df: pd.DataFrame):
    city_df_mean = city_df.groupby([city_df.index.year, city_df.index.month]).mean()

    city_df_mean.index = city_df_mean.index.set_names(["Year", "Month"])

    city_df_mean = city_df_mean.unstack()

    return city_df_mean
