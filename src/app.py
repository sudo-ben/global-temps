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
import flask
import os

from datetime import datetime as dt
from process_data import (
    preprocess,
    load_data,
    build_city_df,
    data_summary,
    load_city_lat_long,
)
from process_city_data import (
    calc_monthly,
    calc_yearly,
)

DEBUG = False
memory = Memory(None) if DEBUG else Memory("cache", verbose=0)

df = preprocess(load_data)

title = f"Cities of the world temperatures from {df.Date.min().strftime('%Y')} to {df.Date.max().strftime('%Y')}"

app = dash.Dash(
    name=title,
    title=title,
    suppress_callback_exceptions=True,
    assets_external_path="main.css",
    index_string="""<!DOCTYPE html>
<html>
    <head>
        <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0'>
        <meta property="og:image" content="https://todaystrends.app/static/social_image.png">
        <meta property="og:image:type" content="image/png">
        <meta property="og:image:width" content="700">
        <meta property="og:image:height" content="450">
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body {
                padding: 0;
                margin: 0;
                background: #000000;
                color: #ffffff;
                text-align: center;
                font-family: "Open Sans", verdana, arial, sans-serif;
            }
            h1, h2, h3, h4, p, #my-daq-toggleswitch {
                padding: 14px 0;
                margin: 0;
            }

            #footer {
                text-align: left;
            }
            #footer p, #footer h3 {
                padding: 0.5rem 1rem;
            }
            a {
                color: #b2b2b2;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>""",
)
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
    float(city_lat_long["Wichita, Kansas, US"]["latt"]),
    float(city_lat_long["Wichita, Kansas, US"]["longt"]),
)


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
        # html.P("Select a city on the map to load temperature history"),
        html.Div(
            [
                html.Div(
                    dl.Map(
                        [dl.TileLayer(), cluster],
                        center=starting_position,
                        zoom=5,
                        id="map",
                        maxBounds=[(-180, -360), (180, 360)],
                        style={
                            "width": "100%",
                            "height": "50vh",
                            "margin": "auto",
                            "display": "block",
                            "filter": "hue-rotate(40deg) brightness(1) contrast(1) saturate(0.5)",
                        },
                    )
                )
            ]
        ),
        html.Div(
            [
                html.H1(id="intermediate-value", children=""),
                html.P(children=title),
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


---
""",
            id="footer",
        ),
    ]
)


STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")


@app.server.route("/static/<resource>")
def serve_static(resource):
    return flask.send_from_directory(STATIC_PATH, resource)


@app.callback(
    [Output("intermediate-value", "children"), Output("map", "center")],
    [dash.dependencies.Input("url", "pathname")]
    + [Input(marker.id, "n_clicks") for marker in markers],
)
def marker_click(*args):
    city_id = None
    if dash.callback_context.triggered[0]["prop_id"] == "url.pathname":
        pathname = args[0]
        city_name = urllib.parse.unquote(pathname[1:])
        print("pathname", pathname, city_name)
        if pathname == "/" or city_name not in all_city_ids:
            city_id = starting_cities[0]
        else:
            city_id = city_name
    else:
        city_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    return city_id, (
        float(city_lat_long[city_id]["latt"]),
        float(city_lat_long[city_id]["longt"]),
    )


number_colors = 2021 - int(df.Date.min().year)
viridis = cm.get_cmap("magma", None)

year_colors = list(viridis(np.linspace(0.25, 0.6, number_colors)))
year_colors_dict = {
    i
    + int(
        df.Date.min().year
    ): f"rgb({int(c[0] * 256)},{int(c[1] * 256)},{int(c[2] * 256)})"
    for i, c in enumerate(year_colors)
}


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
        chosen_color = year_colors_dict[y[0]]

        fig.add_trace(
            go.Scatter(
                x=y[1].index,
                y=y[1]["AvgTemperature"],
                name=y[0],
                mode="markers",
                marker={"color": chosen_color, "size": 3},
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
    print("city_country", city_country)
    return get_yearly_avg_fig(city_country, is_fahrenheit)


@memory.cache
def get_yearly_avg_fig(city_country, is_fahrenheit):
    city_df = build_city_df(df, city_country, is_fahrenheit)

    fig = go.Figure()

    fig = go.Figure()

    yearly_data = calc_yearly(city_df)

    yearly_mean = city_df["AvgTemperature"].astype(float).resample("Y").mean()
    for y in yearly_data:
        chosen_color = year_colors_dict[y[0]]

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
                    line={"color": chosen_color, "width": 2},
                    marker={"color": chosen_color, "size": 14},
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
        chosen_color = year_colors_dict[y[0]]

        series = y[1]

        series = series.groupby(pd.Grouper(freq="15D"))["AvgTemperature"].mean()

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                name=y[0],
                opacity=0.8,
                mode="markers+lines",
                line={"color": chosen_color, "width": 2},
                marker={"color": chosen_color, "size": 6},
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
