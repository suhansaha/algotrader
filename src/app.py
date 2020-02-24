import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
from dash.dependencies import Input, Output, State

import redis
cache = redis.Redis(host='redis', port=6379)

from flask import Flask, render_template, request

import pandas as pd
import plotly
import random
import plotly.graph_objs as go
from collections import deque
from datetime import datetime as dt
from datetime import timedelta

df = pd.read_csv('data/ind_nifty50list.csv')


app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)

temp_file = pd.HDFStore("data/kite_cache_day.h5", mode="r")
data = temp_file.get('/day/NSE/WIPRO').tail(100)['close']
#fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 1, 2])])
fig = go.Figure(data=[go.Scatter(x=data.index, y=data)])

dash_app.layout = html.Div(children=[ 
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
    html.Div(className = 'columns nine', children=[dcc.Graph(id='example-graph') ])
                                                        ])

@dash_app.callback(
    [Output('example-graph', 'figure'),
    Output('msg', 'children')],
    [Input('button', 'n_clicks')],
    [State('yaxis-column','value'), State('input-box', 'value'), 
    State('date-picker-range', 'start_date'), State('date-picker-range', 'end_date'),
    State('algo','value')])
def update_output(n_clicks, stock, value, start_date, end_date, algo ):
    tmpdata = temp_file.get('/day/NSE/'+stock)
    toDate = end_date
    fromDate = start_date
    data = tmpdata[(tmpdata.index >= fromDate) & (tmpdata.index <= toDate)]['close']
    exec(algo)
    return {'data': [go.Scatter(x=data.index, y=data)]}, cache.get('temp').decode("utf-8") 