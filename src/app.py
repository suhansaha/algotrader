import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
from dash.dependencies import Input, Output, State

import redis
from flask import Flask, render_template, request

import pandas as pd
import plotly
import random
import plotly.graph_objs as go
from collections import deque

df = pd.read_csv('data/ind_nifty50list.csv')


app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)

dash_app.layout = html.Div(className='container', children=[ 
    dcc.Dropdown(
                id='yaxis-column',
                options=pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records'),
                value=['TCS'],
                multi=True
            ),
        html.Div(dcc.Input(id='input-box', type='text')),
        html.Button('Submit', id='button'),
        html.Div(id='output-container-button', children='Enter a value and press submit') 
                                                        ])

@dash_app.callback(
    Output('output-container-button', 'children'),
    [Input('button', 'n_clicks'), Input('yaxis-column','value')],
    [State('input-box', 'value')])
def update_output(n_clicks, pathname, value ):
    return 'The input value was "{}" and the button has been clicked {} times: {}'.format(
        value,
        n_clicks,
        pathname
    )