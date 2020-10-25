from process_data import preprocess, load_data
from render_charts import vis_data


def print_info(df):
    print(df.dtypes)
    print(df.describe(datetime_is_numeric=True))
    # print(df.Date.dt.day.explode().value_counts())
    print(df.drop(columns=["State"]).isnull().sum())

    print(df.drop(columns=["State"])[df["AvgTemperature"].isna()])

    cites_num = len(df["City"].unique())

    print(
        f"This data contains a list of daily average temperatures from {cites_num} cities and {len(df['Country'].unique())} countries."
    )


if __name__ == "__main__":
    df = preprocess(load_data())
    print_info(df)
