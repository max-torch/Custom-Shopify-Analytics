'''
This module fetches data from a client's Shopify Store account, uses it to generate a dashboard, and starts a web application server
in debug mode for app testing. Additional steps need to be taken to prepare this for deployment, such as using an appropriate
production server.
'''

from time import time
import json
from urllib.parse import urlparse
import datetime

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
FIELDS = [
    'id', 'app_id', 'buyer_accepts_marketing', 'cancel_reason', 'cancelled_at',
    'client_details', 'closed_at', 'contact_email', 'created_at',
    'current_subtotal_price', 'current_total_discounts', 'current_total_price',
    'customer', 'discount_codes', 'email', 'financial_status',
    'fulfillment_status', 'gateway', 'landing_site', 'name', 'order_number',
    'payment_gateway_names', 'phone', 'processed_at', 'processing_method',
    'referring_site', 'source_name', 'subtotal_price', 'total_discounts',
    'total_line_items_price', 'total_outstanding', 'total_price', 'updated_at',
    'billing_address', 'discount_applications', 'line_items', 'refunds',
    'shipping_address'
]
fake = True

# DataFrame that contains Philippines zipcodes mapped to their area and province/city
zipcodes = (
    pd.read_csv("zipcodes.csv")
    .rename(columns={"ZIP Code": "ZIP_Code"})
    .assign(ZIP_Code=lambda x: x.ZIP_Code.astype("object"))
)

# Dictionary from zipcodes DataFrame for Pandas Series.map() method.
zipcodesdict = pd.Series(zipcodes["Province or city"].values, index=zipcodes["ZIP_Code"]).to_dict()


app = dash.Dash(__name__)
server = app.server


def main():
    """Main routine."""
    generate_dashboard()
    app.run_server(debug=False)

    
def measure_time(func):
    """This function shows the execution time of the function object passed in. This function is meant to be used as a decorator."""
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}s')
        return result

    return wrap_func


@measure_time
def get_all_orders():
    """
    Fetches data from Shopify using Rest Admin API and stores it in a DataFrame. 
    Iteration is due to the API's constraint of only fetching a max of 250 rows.
    """
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
        r = requests.get(url, params=params)
        df = pd.DataFrame(r.json()['orders'])
        orders = pd.concat([orders, df])
        last = df['id'].iloc[-1]
        if len(df) < 250:
            break
    return (orders)


def preprocess_orders(orders):
    """Preprocess the orders DataFrame to prepare it for analysis and plot generation."""
    if fake:
        orders = (
            orders.assign(
                created_at=pd.to_datetime(orders.created_at),
                billing_address=orders.billing_address.apply(lambda x: json.loads(x.replace("'", '"'))),
                customer=orders.customer.apply(lambda x: json.loads(x.replace("'", '"')))
            )
        )
    else:
        orders = (
            orders.drop(columns=['client_details'])
            .assign(
                total_outstanding=pd.to_numeric(orders.total_outstanding),
                created_at=pd.to_datetime(orders.created_at),
                current_total_price=pd.to_numeric(orders.current_total_price)
            )
            .reset_index(drop=True)
        )
    return orders


def generate_figures(orders, location_filter=None):
    """
    Generates the graphs for the app. For each graph, a 'view' is generated from the main DataFrames.
    The sole purpose of the 'view' is to be an aggregation subset that contains only all the necessary
    information that Plotly Express needs to read to generate figures. 
    The figures are returned together as a tuple.
    """

    hours_dict = {
        each: (str(each) + ' AM' if each != 0 else '12 AM')
        for each in range(12)
    }
    hours_dict_pm = {
        each: (str(each - 12) + ' PM' if each != 12 else '12 PM')
        for each in range(12, 24)
    }
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

    metro_cities = [
        'Manila', 'Quezon City', 'Caloocan', 'Las Piñas', 'Makati', 'Malabon',
        'Mandaluyong', 'Marikina', 'Muntinlupa', 'Navotas', 'Parañaque',
        'Pasay', 'Pasig', 'San Juan', 'Taguig', 'Valenzuela', 'Pateros'
    ]

    view_billing = (
        pd.DataFrame(orders.billing_address)
        .assign(
            city=(
                lambda x: x.billing_address
                .apply(lambda y: y['city'] if pd.notnull(y) else y)
                .str.title()
                .str.replace("City", "")
                .str.strip()
            ),
            province=(
                lambda x: x.billing_address
                .apply(lambda y: y['province'] if pd.notnull(y) else y)
                .replace(r'^\s*$', np.NaN, regex=True)
            ),
            zip=(
                lambda x: pd.to_numeric(
                    x.billing_address
                    .apply(lambda y: y['zip'] if pd.notnull(y) else y)
                    .replace(r"[A-Z, a-z]", np.nan, regex=True)
                    .replace('', np.nan)
                )
            ),
            province_city_fromzip=(
                lambda x: x.zip
                .map(zipcodesdict)
                .fillna(x.province)
                .fillna(x.city)
                .replace(r'^\s*$', np.NaN, regex=True)
            ),
            name=(
                lambda x: x.billing_address
                .apply(lambda y: y['name'] if pd.notnull(y) else y)
            )
        )
    )

    # This section plots date and time trends.
    def plot_popular_datetimes(datain,
                               xaxisname: str,
                               title: str,
                               map_vals: bool,
                               map_dict=None):
        """
        Generates a 'view' DataFrame and plots it as a barchart. This function is
        dedicated for generating figures of popular dates and times of orders.
        You can make it show Popular Hours, Months, Days, etc depending on the input arguments.
        """
        view = (
            pd.DataFrame(datain)
            .assign(
                xaxis=lambda x: x.index.map(map_dict).to_list() if map_vals == True else x.index.astype(str),
                yaxis=lambda x: x[x.columns[0]]
            )
            .reset_index(drop=True)
        )
        fig = px.bar(view,
                     x='xaxis',
                     y='yaxis',
                     labels={
                         'xaxis': xaxisname,
                         'yaxis': 'Quantity of Orders'
                     },
                     title=title)
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
        pd.DataFrame(view_billing.province_city_fromzip.value_counts())
        .reset_index(drop=False)
        .rename(columns={'index': 'xaxis', 'province_city_fromzip': 'yaxis'})
        .assign(Province_or_City=lambda x: x.xaxis.apply(lambda y: 'Metro Manila' if y in metro_cities else y))
    )

    xaxisname = "Province or City"
    title = "Distribution of Orders over Billing Address Location"
    fig_location = px.bar(view,
                          x='Province_or_City',
                          y='yaxis',
                          labels={
                              'xaxis': xaxisname,
                              'yaxis': 'Quantity of Orders'
                          },
                          title=title,
                          hover_data=["xaxis"])
    fig_location.update_layout(barmode='stack',
                               xaxis={'categoryorder': 'total descending'})

    # This section plots the referring sites
    def parse_url(url):
        """Takes a url and isolates and returns its netloc. For example, 'https://www.google.com' returns 'google.com'."""
        parsed = urlparse(url)
        return parsed.netloc

    view = (
        pd.DataFrame(
            orders.referring_site
            .dropna()
            .apply(parse_url)
            .replace("", "No referring site or no data")
            .value_counts()
        )
        .reset_index(drop=False)
        .rename(columns={'index': 'xaxis', 'referring_site': 'yaxis'})
    )

    xaxisname = "Referring Site"
    title = "Popular Referring Sites"
    fig_referring = px.bar(view,
                           x='xaxis',
                           y='yaxis',
                           labels={
                               'xaxis': xaxisname,
                               'yaxis': 'Quantity of Referrals'
                           },
                           title=title)
    fig_referring.update_layout(barmode='stack',
                                xaxis={'categoryorder': 'total descending'})

    # This section plots the treemaps
    view = (
        orders[["current_total_price"]]
        .assign(
            location=view_billing.province_city_fromzip,
            city=view_billing.city,
            customer_id=orders.customer.apply(lambda x: x['id'] if pd.notnull(x) else -1),
            customer_name=orders.customer.apply(lambda x: (str(x['first_name']) + " " + str(x['last_name'])) if pd.notnull(x) else x)
        )
        .assign(location = lambda x: x.location.apply(lambda y: 'Metro Manila' if y in metro_cities else y))
        .fillna("Missing Data")
    )

    fig_tree_all = (
        px.treemap(
            view,
            path=[px.Constant("Orders"),
            "location",
            "customer_name"],
            values='current_total_price',
            hover_data=['customer_id'],
            title="Profitable Provinces and Customers"
        )
        .update_traces(root_color="lightgrey")
        .update_layout(margin = dict(t=50, l=25, r=25, b=25))
    )

    if fake:
        filtered_view = view[view["location"] == location_filter]
    else:
        filtered_view = view[view["location"] == "Metro Manila"]
    fig_tree_metro = (
        px.treemap(
            filtered_view, path=[px.Constant("Orders"), "location", "city", "customer_name"],
            values='current_total_price',
            color="city",
            color_discrete_map={'Quezon City': '#FECB52'},
            hover_data=["customer_id"],
            title="Profitable Cities and Customer in Selected Province"
        )
        .update_layout(margin = dict(t=50, l=25, r=25, b=25))
    )

    return fig_hours_day, fig_days_week, fig_days_month, fig_months_year, fig_weeks_year, fig_location, fig_referring, fig_tree_all, fig_tree_metro


@measure_time
def generate_dashboard():
    """
    Dynamically generates dashboard using Dash. Functionality of Forms and Controls are implemented
    using 'callbacks'. Callbacks are decorators wherein the function below it is called when the
    components that have been marked as 'Input' change state. In short, we can say that callbacks are 'triggers'.
    The function output is then used by the callback to update the dashboard.
    """
    def prepare_layout():
        """
        The HTML layout is produced in this function and this function is assigned to `app.layout`. This is the procedure
        described in Dash documentation on making data live update once every page load or page refresh. 
        """
        if fake:
            print("Reading fake data")
            orders = preprocess_orders(pd.read_csv('fake_data.csv', index_col=0))
        else:
            print("Fetching orders from Shopify")
            orders = preprocess_orders(get_all_orders())

        layout = html.Div(children=[
            html.H1(children='Custom Shopify Analytics', style={'text-align': 'center'}),
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
                    html.Strong(html.Label('Filter By Province')),
                    dcc.Dropdown(
                        id='location-list',
                        options=[{'label': 'All', 'value': 'All'}] + 
                        [{'label': location, 'value': location} for location in orders.province.dropna().unique()],
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
            html.Div(children=[
                dcc.Graph(id='graph8'),
            ]),
            html.Div(children=[
                dcc.Graph(id='graph9'),
            ]),
            html.Div('The client\'s local time is: ' + str(datetime.datetime.now())),
            html.Div(id="my-output"),
            dcc.Store(id='my-store', data=orders.to_json(date_format='iso'))
        ])
        return layout

    app.title = 'Hola Said Lola Custom Analytics'
    app.layout = prepare_layout

    @app.callback(
        output=[
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            Output('graph3', 'figure'),
            Output('graph4', 'figure'),
            Output('graph5', 'figure'),
            Output('graph6', 'figure'),
            Output('graph7', 'figure'),
            Output('graph8', 'figure'),
            Output('graph9', 'figure')
        ],
        inputs=[
            Input('date-picker', 'start_date'),
            Input('date-picker', 'end_date'),
            Input('location-list', 'value'),
            Input(component_id='my-store', component_property='data')
        ]
    )
    def update_figures(start_date, end_date, location, orders):
        """
        This function is executed when the Callback is triggered. The Callback listens
        for when the specified components of the Dashboard change state.
        """

        orderss = pd.DataFrame(json.loads(orders))
        orderss = orderss.assign(created_at=lambda x: pd.to_datetime(x.created_at))
        filtered_orders = orderss[orderss.created_at.between(start_date, end_date)]
        if not location == "All":
            filtered_orders = filtered_orders[filtered_orders.province == location]
        return generate_figures(filtered_orders, location)


if __name__ == "__main__":
    main()
