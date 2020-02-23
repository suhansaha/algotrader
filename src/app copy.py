import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

import redis
from flask import Flask, render_template, request

app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)
cache = redis.Redis(host='redis', port=6379)

dash_app.layout = html.Div(className='container', children=[
    html.Div(className='row', children=[
    html.Div(className='col-3',children=[html.H1('left column'),
    html.Label('Text Input'),
    dcc.Input(value='MTL', type='text'),
    ]),
    html.Div(className='col-9',children=[html.H1('right column')] )])
    ]
)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.route('/')
def hello():
    count = get_hit_count()
    #return render_template('index.html')
    return 'Hello World! Shriya have been seen {} times.\n'.format(count)

import plotly
import plotly.graph_objs as go

import pandas as pd
import numpy as np
import json

def create_plot(feature='Bar'):
    if feature == 'Bar':
        N = 40
        x = np.linspace(0, 1, N)
        y = np.random.randn(N)
        df = pd.DataFrame({'x': x, 'y': y}) # creating a sample dataframe
        data = [
            go.Bar(
                x=df['x'], # assign x as the dataframe column 'x'
                y=df['y']
            )
        ]
    else:
        N = 1000
        random_x = np.random.randn(N)
        random_y = np.random.randn(N)

        # Create a trace
        data = [go.Scatter(
            x = random_x,
            y = random_y,
            mode = 'markers'
        )]


    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

@app.route('/bar', methods=['GET', 'POST'])
def change_features():

    feature = request.args['selected']
    graphJSON= create_plot(feature)
    return graphJSON

@app.route('/scanner')
def scanner():
    bar = create_plot()
    print("Suhan Saha")
    return render_template('index.html', plot=bar)