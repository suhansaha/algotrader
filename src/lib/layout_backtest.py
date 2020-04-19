import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
from dash.dependencies import Input, Output, State
from datetime import datetime as dt
from datetime import timedelta

df = pd.read_csv('data/ind_nifty50list.csv')

# Loading OHLC data from local cache
temp_file = pd.HDFStore("data/kite_cache_day.h5", mode="r")
# Loading OHLC data for a stock for initial render
#data = temp_file.get('/day/NSE/WIPRO').tail(100)['close']

layout_backtest = html.Div(children=[ 
    # Sidebar
    html.Div(className = 'columns five', children=[
        html.Div(children=[
            # Group 1
            html.Label("Pick Stock(s):", className='columns twelve'),
            html.Br(),
            dcc.Dropdown(id='yaxis-column', value='TCS', multi=False,  className='columns twelve',
                        options=pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records')),

            # Group 2
            html.Label("Algo:"),
            dcc.Textarea(value='Algo:Suhan',style={'width': '100%', 'height':'200px'}, id='algo', rows=30, wrap='soft'),
            html.Br(),
            # Group 3
            html.Label("Date:", className='columns one'),
            dcc.DatePickerRange( id='date-picker-range', className='columns seven', end_date_placeholder_text='Select a date!',
                    end_date=temp_file.get('/day/NSE/WIPRO').index[-1].strftime("%Y-%m-%d"),
                    start_date=(temp_file.get('/day/NSE/WIPRO').index[-1] - timedelta(days=90)).strftime("%Y-%m-%d")),
            html.Label("Qty:", className='columns one'),
            dcc.Input(id='input-box', type='text', className='columns two'),
            html.Br(), html.Br(), 
            html.Button('BackTest: Start', id='button', disabled=True, className='columns five'),
            html.Br(),html.Hr(), 
            # Group 4
            html.Label("Log:"),html.Br(),
            html.Div( id='msg', children='')
        ])  
    ]),
    # Main graph
    html.Div(className = 'columns seven', children=[
        dcc.Graph(id='example-graph'),
        dcc.Interval( id='graph-update', interval=1000, n_intervals=0, max_intervals=-1, disabled = True) ])
    ])

