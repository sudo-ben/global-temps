# Daily average temperature values recorded in major cities of the world

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from matplotlib import cm
import plotly.express as px
import datetime
import urllib
import functools

from datetime import datetime as dt
from process_data import (
    preprocess,
    load_data,
    build_city_df,
    calc_monthly,
    calc_yearly,
    day_of_year_pivot,
    data_summary,
)
import numpy as np
import pandas as pd
import dash_daq as daq
from joblib import Memory

memory = Memory("cache", verbose=0)

df = preprocess(load_data)

title = f"Cities of the world temperatures from {df.Date.min().strftime('%Y')} to {df.Date.max().strftime('%Y')}"

app = dash.Dash(name=title)

starting_cities = [
    "New York City, New York, US",
    "Tokyo, Japan",
    "Shanghai, China",
    "Los Angeles, California, US",
    "Delhi, India",
    "London, United Kingdom",
    "Abu Dhabi, United Arab Emirates",
]

all_city_ids = list(df.CityCountry.unique())

app.layout = html.Div(
    [
        # represents the URL bar, doesn't render anything
        dcc.Location(id="url", refresh=False),
        dcc.Link(html.H2(children=title), href="/"),
        html.Div(children=data_summary(df)),
        html.Div(
            [
                html.H3(children="Select city"),
                dcc.Dropdown(
                    id="city_country-dropdown",
                    options=[{"label": s, "value": s} for s in all_city_ids],
                    value="",
                ),
            ]
        ),
        daq.ToggleSwitch(
            id="my-daq-toggleswitch",
            label="Celsius °C   - Fahrenheit °F",
            labelPosition="bottom",
        ),
        # content will be rendered in this element
        html.Div(id="page-content"),
    ]
)


def load_city_page(city_country):

    if city_country in all_city_ids:
        return html.Div(
            [
                dcc.Input(
                    id="intermediate-value",
                    type="text",
                    style={"display": "none"},
                    value=city_country,
                ),
                dcc.Graph(id="all-graph"),
                dcc.Graph(id="yearly-average-graph"),
                dcc.Graph(id="yearly-graph"),
            ],
            style={"width": "500"},
        )
    else:
        return html.Div("City not found")


@app.callback(
    dash.dependencies.Output("page-content", "children"),
    [dash.dependencies.Input("url", "pathname"), Input("my-daq-toggleswitch", "value")],
)
def display_page(pathname, is_fahrenheit):

    city_name = urllib.parse.unquote(pathname[1:])
    print(pathname, city_name)
    if pathname == "/" or city_name not in all_city_ids:
        return (
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Link(c, href="/" + c),
                            dcc.Graph(
                                id="yearly-graph",
                                figure=build_city_all_with_mean(c, is_fahrenheit),
                            ),
                        ]
                    )
                    for c in starting_cities
                ]
            ),
        )

    else:
        return load_city_page(city_name)


"""
<a href="https://twitter.com/BenMcDonald___?ref_src=twsrc%5Etfw" class="twitter-follow-button" data-show-count="false">Follow @BenMcDonald___</a><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
"""

"""
Invalid temperture entries
"Occasionally, problems with weather station metering equipment result in missing average daily temperatures. We denote missing data using a “–99” flag." http://academic.udayton.edu/kissock/http/Weather/missingdata.htm

The dataset is from the University of Dayton and is available here.
http://academic.udayton.edu/kissock/http/Weather/default.htm

"""

viridis = cm.get_cmap("viridis", 12)
year_colors = list(reversed(viridis(np.linspace(0, 1, 2021 - int(df.Date.min().year)))))


def get_symbol(is_fahrenheit):
    return "°F" if is_fahrenheit else "°C"


@app.callback(
    Output("yearly-graph", "figure"),
    [
        Input("intermediate-value", "value"),
        Input("my-daq-toggleswitch", "value"),
    ],
)
def _update_month_each_year_graph(city_country, is_fahrenheit):
    return update_month_each_year_graph(city_country, is_fahrenheit)


@memory.cache
def update_month_each_year_graph(city_country, is_fahrenheit):
    print(city_country)
    city_df = build_city_df(df, city_country, is_fahrenheit)

    yearly_data = calc_yearly(city_df)

    print(df.Date.min())

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
                marker={"color": rgb_color, "size": 4},
            )
        )

    fig.update_layout(
        legend={"traceorder": "reversed"},
        template="plotly_dark",
        xaxis=dict(
            tickformat="%b",
        ),
        title=f"Air temperature in {city_country}",
        xaxis_title="Month",
        yaxis_title=get_symbol(is_fahrenheit),
    )
    return fig


@app.callback(
    Output("yearly-average-graph", "figure"),
    [
        Input("intermediate-value", "value"),
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

    yearly_mean = (
        city_df[city_df.index.year < city_df.index.max().year]["AvgTemperature"]
        .astype(float)
        .resample("Y")
        .mean()
    )
    for y in yearly_data:
        chosen_color = year_colors[(2021 - y[0]) - 1]
        rgb_color = f"rgb({int(chosen_color[1] * 256)},{int(chosen_color[2] * 256)},{int(chosen_color[3] * 256)})"

        single_year = yearly_mean[
            (yearly_mean.index.year == int(y[0]))
            | (yearly_mean.index.year == (int(y[0]) + 1))
        ]
        fig.add_trace(
            go.Scatter(
                x=single_year.index,
                y=single_year,
                name=y[0],
                line={"color": rgb_color, "width": 1},
            )
        )

    fig.update_layout(
        legend={"traceorder": "reversed"},
        template="plotly_dark",
        title=f"Yearly average air temperature in {city_country}",
        xaxis_title="Year",
        yaxis_title=get_symbol(is_fahrenheit),
    )
    return fig


@app.callback(
    Output("all-graph", "figure"),
    [
        Input("intermediate-value", "value"),
        Input("my-daq-toggleswitch", "value"),
    ],
)
def _build_city_all_with_mean(city_country, is_fahrenheit):
    return build_city_all_with_mean(city_country, is_fahrenheit)


@memory.cache
def build_city_all_with_mean(city_country, is_fahrenheit):
    print(city_country)
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
                marker={"color": rgb_color, "size": 5},
            )
        )

    yearly_mean = (
        city_df[city_df.index.year < city_df.index.max().year]["AvgTemperature"]
        .astype(float)
        .resample("Y")
        .mean()
    )
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
        title=f"Air temperature in {city_country}",
        xaxis_title="Year",
        yaxis_title=get_symbol(is_fahrenheit),
    )
    return fig


if __name__ == "__main__":
    app.run_server()
