# Daily average temperature values recorded in major cities of the world

import pandas as pd
from matplotlib import cm
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import datetime
import urllib
import functools
import dash_leaflet as dl
import numpy as np
import dash_daq as daq
from joblib import Memory

from datetime import datetime as dt
from process_data import (
    preprocess,
    load_data,
    build_city_df,
    calc_monthly,
    calc_yearly,
    day_of_year_pivot,
    data_summary,
    load_city_lat_long,
)

DEBUG = False
memory = Memory(None) if DEBUG else Memory("cache", verbose=0)


title = f"⛅ Cities of the world temperatures from {df.Date.min().strftime('%Y')} to {df.Date.max().strftime('%Y')}"

app = dash.Dash(name=title, suppress_callback_exceptions=True)
server = app.server

starting_cities = [
    "Los Angeles, California, US",
    "New York City, New York, US",
    "Tokyo, Japan",
    "Shanghai, China",
    "Delhi, India",
    "London, United Kingdom",
    "Abu Dhabi, United Arab Emirates",
]
city_lat_long = load_city_lat_long()

starting_position = (
    float(city_lat_long["Denver, Colorado, US"]["latt"]),
    float(city_lat_long["Denver, Colorado, US"]["longt"]),
)


df = preprocess(load_data)
all_city_ids = list(df.CityCountry.unique())

markers = [
    dl.Marker(
        dl.Tooltip(city_id),
        position=(
            float(city_lat_long[city_id]["latt"]),
            float(city_lat_long[city_id]["longt"]),
        ),
        id=city_id.replace(".", ""),
    )
    for city_id in all_city_ids
]
cluster = dl.MarkerClusterGroup(
    id="markers", children=markers, options={"polygonOptions": {"color": "red"}}
)

app.layout = html.Div(
    [
        # represents the URL bar, doesn't render anything
        dcc.Location(id="url", refresh=False),
        # dcc.Link(html.H2(children=title), href="/"),
        html.H2(children=title),
        html.Div("Select a city on the map to load temperature history"),
        html.Div(
            [
                html.Div(
                    dl.Map(
                        [dl.TileLayer(), cluster],
                        center=starting_position,
                        zoom=5,
                        id="map",
                        style={
                            "width": "100%",
                            "height": "50vh",
                            "margin": "auto",
                            "display": "block",
                            "filter": "hue-rotate(180deg) contrast(100%)",
                        },
                    )
                )
            ]
        ),
        html.Div(
            [
                html.H1(id="intermediate-value", children=""),
                daq.ToggleSwitch(
                    id="my-daq-toggleswitch",
                    label="Celsius °C   - Fahrenheit °F",
                    labelPosition="bottom",
                ),
                dcc.Graph(id="all-graph"),
                dcc.Graph(id="yearly-average-graph"),
                dcc.Graph(id="yearly-graph"),
            ],
        ),
        dcc.Markdown(
            f"""
---

{data_summary(df)}

[GitHub link and code](https://github.com/benjaminmcdonald/global-temps)

---

### Author

[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/BenMcDonald___.svg?style=social&label=Follow%20%40BenMcDonald___)](https://twitter.com/BenMcDonald___)
"""
        ),
    ]
)


@app.callback(
    Output("intermediate-value", "children"),
    [Input(marker.id, "n_clicks") for marker in markers],
)
def marker_click(*args):
    marker_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    return marker_id if marker_id else starting_cities[0]


viridis = cm.get_cmap("viridis", 12)
year_colors = list(reversed(viridis(np.linspace(0, 1, 2021 - int(df.Date.min().year)))))


def get_symbol(is_fahrenheit):
    return "°F" if is_fahrenheit else "°C"


@app.callback(
    Output("all-graph", "figure"),
    [
        Input("intermediate-value", "children"),
        Input("my-daq-toggleswitch", "value"),
    ],
)
def _build_city_all_with_mean(city_country, is_fahrenheit):
    return build_city_all_with_mean(city_country, is_fahrenheit)


@memory.cache
def build_city_all_with_mean(city_country, is_fahrenheit):
    city_df = build_city_df(df, city_country, is_fahrenheit)

    fig = go.Figure()

    yearly_data = calc_yearly(city_df)

    fig = go.Figure()

    for y in yearly_data:
        chosen_color = year_colors[(2021 - y[0]) - 1]
        rgb_color = f"rgb({int(chosen_color[1] * 256)},{int(chosen_color[2] * 256)},{int(chosen_color[3] * 256)})"

        fig.add_trace(
            go.Scatter(
                x=y[1].index,
                y=y[1]["AvgTemperature"],
                name=y[0],
                mode="markers",
                marker={"color": rgb_color, "size": 3},
            )
        )

    yearly_mean = (
        city_df[city_df.index.year < city_df.index.max().year]["AvgTemperature"]
        .astype(float)
        .resample("Y")
        .mean()
    )

    yearly_mean.index = yearly_mean.index.map(lambda dt: dt.replace(day=15, month=6))

    fig.add_trace(
        go.Scatter(
            x=yearly_mean.index,
            y=yearly_mean,
            name="Yearly average",
            line={"color": "rgb(255, 127, 14)"},
        )
    )

    fig.update_layout(
        legend={"traceorder": "reversed"},
        template="plotly_dark",
        title=f"⛅ Daily temperatures",
        xaxis_title="Year",
        yaxis_title=f"Air temperature 🌡 {get_symbol(is_fahrenheit)}",
    )
    return fig


@app.callback(
    Output("yearly-average-graph", "figure"),
    [
        Input("intermediate-value", "children"),
        Input("my-daq-toggleswitch", "value"),
    ],
)
def _get_yearly_avg_fig(city_country, is_fahrenheit):
    print(city_country)
    return get_yearly_avg_fig(city_country, is_fahrenheit)


@memory.cache
def get_yearly_avg_fig(city_country, is_fahrenheit):
    city_df = build_city_df(df, city_country, is_fahrenheit)

    fig = go.Figure()

    fig = go.Figure()

    yearly_data = calc_yearly(city_df)

    yearly_mean = city_df["AvgTemperature"].astype(float).resample("Y").mean()
    for y in yearly_data:
        chosen_color = year_colors[(2021 - y[0]) - 1]
        rgb_color = f"rgb({int(chosen_color[1] * 256)},{int(chosen_color[2] * 256)},{int(chosen_color[3] * 256)})"

        single_year = yearly_mean[
            (yearly_mean.index.year == int(y[0]))
            | (yearly_mean.index.year == (int(y[0]) - 1))
        ]
        single_year.index = single_year.index.map(
            lambda dt: dt.replace(day=15, month=6)
        )

        num_points = len(city_df[city_df.index.year == int(y[0])].dropna())

        if num_points > 350:
            fig.add_trace(
                go.Scatter(
                    x=single_year.index,
                    y=single_year,
                    name=y[0],
                    line={"color": rgb_color, "width": 0.7},
                    marker={"color": rgb_color, "size": 12},
                )
            )

    fig.update_layout(
        legend={"traceorder": "reversed"},
        template="plotly_dark",
        title=f"⛅ Yearly average from {city_df.index.min().year} to {city_df.index.max().year}",
        xaxis=dict(
            tickformat="%Y",
        ),
        xaxis_title="Year",
        yaxis_title=f"Yearly average air temperature 🌡 {get_symbol(is_fahrenheit)}",
    )
    return fig


@app.callback(
    Output("yearly-graph", "figure"),
    [
        Input("intermediate-value", "children"),
        Input("my-daq-toggleswitch", "value"),
    ],
)
def _update_month_each_year_graph(city_country, is_fahrenheit):
    return update_month_each_year_graph(city_country, is_fahrenheit)


@memory.cache
def update_month_each_year_graph(city_country, is_fahrenheit):
    city_df = build_city_df(df, city_country, is_fahrenheit)

    yearly_data = calc_yearly(city_df)

    fig = go.Figure()

    for y in yearly_data:
        y[1].index = y[1].index.map(lambda dt: dt.replace(year=2020))
        chosen_color = year_colors[(2021 - y[0]) - 1]
        rgb_color = f"rgb({int(chosen_color[1] * 256)},{int(chosen_color[2] * 256)},{int(chosen_color[3] * 256)})"

        series = y[1]

        series = series.groupby(pd.Grouper(freq="15D"))["AvgTemperature"].mean()

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                name=y[0],
                opacity=0.6,
                mode="markers+lines",
                line={"color": rgb_color, "width": 2},
                marker={"color": rgb_color, "size": 6},
            )
        )

    fig.update_layout(
        legend={"traceorder": "reversed"},
        template="plotly_dark",
        xaxis=dict(
            tickformat="%b",
        ),
        title=f"⛅ Overlay of years {city_df.index.min().year} to {city_df.index.max().year}",
        xaxis_title="Month",
        yaxis_title=f"Daily air temperature 🌡 {get_symbol(is_fahrenheit)}",
    )
    return fig


if __name__ == "__main__":
    app.run_server(debug=DEBUG)
