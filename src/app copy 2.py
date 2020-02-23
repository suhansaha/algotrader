import dash
import dash_core_components as dcc
import dash_html_components as html
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
from dash.dependencies import Input, Output

import redis
from flask import Flask, render_template, request

import pandas as pd
import plotly
import random
import plotly.graph_objs as go
from collections import deque
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

X = deque(maxlen=20)
X.append(1)
Y = deque(maxlen=20)
Y.append(1)

app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)

dash_app.layout = html.Div(className='container', children=[
    html.Div(className='row', children=[
    html.Div(className='col-3',children=[html.H1('left column'),
    html.Label('Text Input'),
    dcc.Input(value='MTL', type='text'),
    dcc.Input(id='my-id', value='initial value', type='text'),
    html.Div(id='my-div')

    ]),
    html.Div(className='col-9',children=[html.H1('right column')] )]),
        dcc.Graph(id='graph-with-slider'),
    dcc.Slider(
        id='year-slider',
        min=df['year'].min(),
        max=df['year'].max(),
        value=df['year'].min(),
        marks={str(year): str(year) for year in df['year'].unique()},
        step=None
    ),
        dcc.Graph(id='live-graph', animate=True),
        dcc.Interval(
            id='graph-update',
            interval=5*1000
        ),
    ]

    
)

@dash_app.callback(
    Output(component_id='my-div', component_property='children'),
    [Input(component_id='my-id', component_property='value')]
)

def update_output_div(input_value):
    return 'You\'ve entered "{}"'.format(input_value)

@dash_app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('year-slider', 'value')])

def update_figure(selected_year):
    filtered_df = df[df.year == selected_year]
    traces = []
    for i in filtered_df.continent.unique():
        df_by_continent = filtered_df[filtered_df['continent'] == i]
        traces.append(dict(
            x=df_by_continent['gdpPercap'],
            y=df_by_continent['lifeExp'],
            text=df_by_continent['country'],
            mode='markers',
            opacity=0.7,
            marker={
                'size': 15,
                'line': {'width': 0.5, 'color': 'white'}
            },
            name=i
        ))

    return {
        'data': traces,
        'layout': dict(
            xaxis={'type': 'log', 'title': 'GDP Per Capita',
                   'range':[2.3, 4.8]},
            yaxis={'title': 'Life Expectancy', 'range': [20, 90]},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest',
            transition = {'duration': 500},
        )
    }



@dash_app.callback(Output('live-graph', 'figure'),
              [Input('graph-update','n_intervals')])
def update_graph_scatter(input_data):
    X.append(X[-1]+1)
    Y.append(Y[-1]+Y[-1]*random.uniform(-0.1,0.1))

    data = plotly.graph_objs.Scatter(
            x=list(X),
            y=list(Y),
            name='Scatter',
            mode= 'lines+markers'
            )

    return {'data': [data],'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]),
                                                yaxis=dict(range=[min(Y),max(Y)]),)}

