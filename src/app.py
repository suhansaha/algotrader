import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

import redis
from flask import Flask

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
    return 'Hello World! Shriya have been seen {} times.\n'.format(count)


@app.route('/scanner')
def scanner():
    return "Hello Scanner"