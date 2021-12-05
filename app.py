'''
This module fetches data from a client's Shopify Store account. The data then serves as a data
source for data visualizations.

Run this app with `python app.py` and
visit http://127.0.0.1:8050/ in your web browser.
'''


from time import time
import json
import webbrowser

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import requests


# Global Variables
RESOURCE = 'orders'
FIELDS = ['id', 'app_id', 'buyer_accepts_marketing', 'cancel_reason', 'cancelled_at', 'client_details', 'closed_at', 'contact_email', 'created_at', 'current_subtotal_price', 'current_total_discounts', 'current_total_price', 'customer', 'discount_codes', 'email', 'financial_status', 'fulfillment_status', 'gateway', 'landing_site', 'name', 'order_number', 'payment_gateway_names', 'phone', 'processed_at', 'processing_method', 'referring_site', 'source_name', 'subtotal_price', 'total_discounts', 'total_line_items_price', 'total_outstanding', 'total_price', 'updated_at', 'billing_address', 'discount_applications', 'line_items', 'refunds', 'shipping_address']


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
    orders = preprocess(orders)
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


def preprocess(orders):
    orders = (
        orders.drop(columns = ['customer', 'client_details'])
        .assign(
            total_outstanding = pd.to_numeric(orders.total_outstanding),
            created_at = pd.to_datetime(orders.created_at)
        )
        .reset_index(drop=True)
    )
    return orders


def generate_figures(orders):

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

    def plot_popular_datetimes(datain, xaxisname: str, title: str, map_vals: bool, map_dict=None):
        view = (
            pd.DataFrame(datain)
            .assign(
                xaxis = lambda x: x.index.map(map_dict).to_list() if map_vals == True else x.index.astype(str),
                yaxis = lambda x: x[x.columns[0]]
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

    return fig_hours_day, fig_days_week, fig_days_month, fig_months_year, fig_weeks_year


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
    ])

    @app.callback(
        output=[
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            Output('graph3', 'figure'),
            Output('graph4', 'figure'),
            Output('graph5', 'figure')
        ],
        inputs=[
            Input('date-picker', 'start_date'),
            Input('date-picker', 'end_date')
        ]
    )
    def update_figures(start_date, end_date):
        date_filtered_orders = orders[orders.created_at.between(start_date, end_date)]
        return generate_figures(date_filtered_orders)


if __name__ == "__main__":
    main()
    webbrowser.open('http://127.0.0.1:8050/')
    app.run_server(debug=True)
    