'''
This module fetches data from a client's Shopify Store account. The data then serves as a data
source for data visualizations.

Run this app with `python app.py` and
visit http://127.0.0.1:8050/ in your web browser.
'''


from time import time
import json
import webbrowser
from urllib.parse import urlparse

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import requests
import numpy as np


# Global Variables
RESOURCE = 'orders'
FIELDS = ['id', 'app_id', 'buyer_accepts_marketing', 'cancel_reason', 'cancelled_at', 'client_details', 'closed_at', 'contact_email', 'created_at', 'current_subtotal_price', 'current_total_discounts', 'current_total_price', 'customer', 'discount_codes', 'email', 'financial_status', 'fulfillment_status', 'gateway', 'landing_site', 'name', 'order_number', 'payment_gateway_names', 'phone', 'processed_at', 'processing_method', 'referring_site', 'source_name', 'subtotal_price', 'total_discounts', 'total_line_items_price', 'total_outstanding', 'total_price', 'updated_at', 'billing_address', 'discount_applications', 'line_items', 'refunds', 'shipping_address']

# DataFrame that contains Philippines zipcodes mapped to their area and province/city
zipcodes = (
    pd.read_csv("zipcodes.csv")
    .rename(columns={"ZIP Code": "ZIP_Code"})
    .assign(ZIP_Code=lambda x: x.ZIP_Code.astype("object"))
)

# Dictionary from zipcodes DataFrame for Pandas Series.map() method.
zipcodesdict = pd.Series(zipcodes["Province or city"].values, index=zipcodes["ZIP_Code"]).to_dict()


app = dash.Dash(__name__)
pd.set_option("display.max_columns", None) # Set Pandas Display Options


def measure_time(func):
    """This function shows the execution time of the function object passed in. This function is a decorator."""
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}s')
        return result
    return wrap_func


@measure_time
def main():
    orders = get_all_orders()
    orders = preprocess_orders(orders)
    generate_layout(orders)


def get_all_orders():
    """Fetch data from Shopify using Rest Admin API and store it in a DataFrame. Iteration is due to the API's constraint of only fetching a max of 250 rows."""
    with open('Credentials.json') as file:
        credentials = json.load(file)
    last = 0
    orders = pd.DataFrame()
    while True:
        params = {
            'limit': '250',
            'status': 'any',
            'since_id': str(last),
            'fields': ','.join(FIELDS)
        }
        url = f"https://{credentials['APIKEY']}:{credentials['APIPASS']}@{credentials['HOSTNAME']}/admin/api/{credentials['VERSION']}/{RESOURCE}.json"
        r = requests.get(url, params = params)
        df = pd.DataFrame(r.json()['orders'])
        orders = pd.concat([orders,df])
        last = df['id'].iloc[-1]
        if len(df) < 250:
            break
    return(orders)


def preprocess_orders(orders):
    orders = (
        orders.drop(columns=['customer', 'client_details'])
        .assign(
            total_outstanding=pd.to_numeric(orders.total_outstanding),
            created_at=pd.to_datetime(orders.created_at)
        )
        .reset_index(drop=True)
    )
    return orders


def preprocess_billing_address(billing_address):

    # DataFrame that contains Billing Addresses of each order
    billing_address = (
        billing_address.assign(
            city=lambda x: x.city.str.upper().str.replace("CITY", "").str.strip(),
            province=lambda x: x.province.replace(r'^\s*$', np.NaN, regex=True),
            zip=lambda x: pd.to_numeric(x.zip.replace(r"[A-Z, a-z]", np.nan, regex=True).replace('', np.nan)),
            province_city_fromzip=lambda x: x.zip.map(zipcodesdict).fillna(x.province).fillna(x.city)
        )
    )
    return billing_address


def generate_figures(orders, billing_address):

    hours_dict = {each : (str(each) + ' AM' if each != 0 else '12 AM') for each in range(12)}
    hours_dict_pm = {each : (str(each - 12) + ' PM' if each != 12 else '12 PM') for each in range(12, 24)}
    hours_dict.update(hours_dict_pm)

    days_of_week_dict = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }

    months_of_year_dict = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }

    metro_cities = ['Manila', 'Quezon City', 'Caloocan', 'Las Piñas', 'Makati', 'Malabon', 'Mandaluyong', 'Marikina', 'Muntinlupa', 'Navotas', 'Parañaque', 'Pasay', 'Pasig', 'San Juan', 'Taguig', 'Valenzuela', 'Pateros']

    # This section plots date and time trends.
    def plot_popular_datetimes(datain, xaxisname: str, title: str, map_vals: bool, map_dict=None):
        view = (
            pd.DataFrame(datain)
            .assign(
                xaxis=lambda x: x.index.map(map_dict).to_list() if map_vals == True else x.index.astype(str),
                yaxis=lambda x: x[x.columns[0]]
            )
            .reset_index(drop=True)
        )
        fig = px.bar(view, x='xaxis', y='yaxis', labels={'xaxis': xaxisname, 'yaxis': 'Quantity of Orders'}, title=title)
        return fig

    fig_hours_day = plot_popular_datetimes(
        orders.created_at.dt.hour.value_counts(),
        'Hour of Day',
        'Popular Hours of the Day',
        True, 
        hours_dict
    )

    fig_days_week = plot_popular_datetimes(
        orders.created_at.dt.dayofweek.value_counts(),
        'Day of Week',
        'Popular Days of the Week',
        True, 
        days_of_week_dict
    )

    fig_days_month = plot_popular_datetimes(
        orders.created_at.dt.day.value_counts(),
        'Day of Month',
        'Popular Days of the Month',
        False
    )

    fig_months_year = plot_popular_datetimes(
        orders.created_at.dt.month.value_counts(),
        'Month of Year',
        'Popular Months of the Year',
        True,
        months_of_year_dict
    )

    fig_weeks_year = plot_popular_datetimes(
        orders.created_at.dt.isocalendar().week.value_counts(),
        'Week of Year',
        'Popular Weeks of the Year',
        False
    )

    # This section plots location trends.
    view = (
        pd.DataFrame(billing_address.province_city_fromzip.replace(r'^\s*$', np.NaN, regex=True).value_counts())
        .reset_index(drop=False)
        .rename(columns={'index': 'xaxis', 'province_city_fromzip': 'yaxis'})
        .assign(Province_or_City = lambda x: x.xaxis.apply(lambda y: 'Metro Manila' if y in metro_cities else y))
    )

    xaxisname = "Province or City"
    title = "Distribution of Orders over Billing Address Location"
    fig_location = px.bar(view, x='Province_or_City', y='yaxis', labels={'xaxis': xaxisname, 'yaxis': 'Quantity of Orders'}, title=title, hover_data=["xaxis"])
    fig_location.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})

    # This section plots the referring sites
    def parse_url(url):
        parsed = urlparse(url)
        return parsed.netloc

    view = (
        pd.DataFrame(
            orders.referring_site
            .fillna("")
            .apply(parse_url)
            .replace("", "No referring site or no data")
            .value_counts()
        )
        .reset_index(drop=False)
        .rename(columns={'index': 'xaxis', 'referring_site': 'yaxis'})
    )

    xaxisname = "Referring Site"
    title = "Popular Referring Sites"
    fig_referring = px.bar(view, x='xaxis', y='yaxis', labels={'xaxis': xaxisname, 'yaxis': 'Quantity of Referrals'}, title=title)
    fig_referring.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})

    return fig_hours_day, fig_days_week, fig_days_month, fig_months_year, fig_weeks_year, fig_location, fig_referring


def generate_layout(orders):

    app.layout = html.Div(children=[
        html.H1(children='Hola Said Lola Analytics', style={'text-align': 'center'}),
        html.Div(children="A Dashboard for analyzing your audience.", style={'text-align': 'center'}),
        html.Div([
            html.Div([
                html.Strong(html.Label('Filter By Date ')),
                html.Div(
                    dcc.DatePickerRange(
                        id='date-picker',
                        min_date_allowed=orders.created_at.min().date(),
                        max_date_allowed=orders.created_at.max().date(),
                        initial_visible_month=orders.created_at.max().date(),
                        start_date=orders.created_at.min().date(),
                        end_date=orders.created_at.max().date()
                    ), style={'float': 'inline-start'}
                )
            ], style={'float': 'left','margin': '15px'}),
            html.Div([
                html.Strong(html.Label('Filter By City ')),
                dcc.Dropdown(
                    id='city-list',
                    options=[
                        {'label': 'All', 'value': 'All'},
                        {'label': 'Montreal', 'value': 'MTL'},
                        {'label': 'San Francisco', 'value': 'SF'}
                    ],
                    value='All'
                ),
            ], style={'float': 'left','margin': '15px', 'width': '200px'}),
        ],),
        html.Div(children=[
            dcc.Graph(id='graph1'),
            dcc.Graph(id='graph2'),
        ], style={'columnCount': 2, 'clear': 'both'}),
        html.Div(children=[
            dcc.Graph(id='graph3'),
            dcc.Graph(id='graph4'),
        ], style={'columnCount': 2}),
        html.Div(children=[
            dcc.Graph(id='graph5'),
        ]),
        html.Div(children=[
            dcc.Graph(id='graph6'),
        ]),
        html.H3("Referring Site: The website where the customer clicked a link to the shop."),
        html.Div(children=[
            dcc.Graph(id='graph7'),
        ]),
    ])

    @app.callback(
        output=[
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            Output('graph3', 'figure'),
            Output('graph4', 'figure'),
            Output('graph5', 'figure'),
            Output('graph6', 'figure'),
            Output('graph7', 'figure')
        ],
        inputs=[
            Input('date-picker', 'start_date'),
            Input('date-picker', 'end_date')
        ]
    )
    def update_figures(start_date, end_date):
        date_filtered_orders = orders[orders.created_at.between(start_date, end_date)]
        billing_address = pd.json_normalize(date_filtered_orders[date_filtered_orders["billing_address"].notnull()]["billing_address"])
        billing_address = preprocess_billing_address(billing_address)
        return generate_figures(date_filtered_orders, billing_address)


if __name__ == "__main__":
    main()
    webbrowser.open('http://127.0.0.1:8050/')
    app.run_server(debug=True)
    