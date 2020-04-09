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
data = temp_file.get('/day/NSE/WIPRO').tail(100)['close']

layout_backtest = html.Div(children=[ 
    # Sidebar
    html.Div(className = 'columns three', children=[
        html.Label("Pick Stock(s):"),
        dcc.Dropdown(
                    id='yaxis-column',
                    options=pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records'),
                    value='TCS',
                    multi=False
                ),
        html.Br(),
        html.Div( children=[html.Label("Qty:", className='columns two'),
        dcc.Input(id='input-box', type='text', className='columns nine')]),
        html.Br(),
        html.Br(),
        html.Div( children=[dcc.DatePickerRange( id='date-picker-range',end_date=temp_file.get('/day/NSE/WIPRO').index[-1].strftime("%Y-%m-%d"),
                start_date=(temp_file.get('/day/NSE/WIPRO').index[-1] - timedelta(days=90)).strftime("%Y-%m-%d"),
              end_date_placeholder_text='Select a date!')]),
        html.Br(),
        html.Div( children=[html.Button('BackTest', id='button')]),
        html.Div( id='msg', children=''),
        dcc.Textarea(value='',style={'width': '100%'}, id='algo')  
        ]),
    # Main graph
    html.Div(className = 'columns nine', children=[dcc.Graph(id='example-graph') ])
                                                        ])

