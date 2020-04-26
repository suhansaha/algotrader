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
    html.Div(className = 'columns three', children=[
        html.Div(children=[
            # Group 4
            html.Div( id='msg', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll','white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'650px'}, children='Welcome to Freedom')
        ])  
    ]),
    # Main graph
    html.Div(className = 'columns nine', children=[
        # Group 3
        dcc.Dropdown(id='yaxis-column', value=['TCS','WIPRO'], multi=True,  className='columns six',
                        options=pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records')),

        dcc.DatePickerRange( id='date-picker-range', className='columns five', end_date_placeholder_text='Select a date!',
                end_date=temp_file.get('/day/NSE/WIPRO').index[-1].strftime("%Y-%m-%d"),
                start_date=(temp_file.get('/day/NSE/WIPRO').index[-1] - timedelta(days=90)).strftime("%Y-%m-%d")),
        
        html.Br(),html.Br(),
        dcc.Textarea(value='', className='prettyprint lang-py',style={'width': '100%', 'height':'200px'}, id='algo', rows=30, wrap='soft'),
        html.Br(),
        html.Label("Qty:", className='columns one'),
        dcc.Input(id='input-qty', type='text', className='columns two', value='10'),
        
        html.Label("SL:", className='columns one'),
        dcc.Input(id='input-sl', type='text', className='columns one', value='1'),
        
        html.Label("Target:", className='columns one'),
        dcc.Input(id='input-target', type='text', className='columns one', value='2'),
        dcc.Dropdown(id='freq', style={'margin-left':'10px'}, value='day', multi=False,  className='columns two',
                        options=[{'label':'day', 'value':'day'},{'label':'1min', 'value':'1min'}] ),
        html.Button('BackTest: Start', id='button', disabled=True, className='columns three'), 
        # Group 2
        html.Br(),
        html.Br(),
        dcc.Graph(id='example-graph'),
        dcc.Interval( id='graph-update', interval=1000, n_intervals=0, max_intervals=-1, disabled = True) ])
    ])

