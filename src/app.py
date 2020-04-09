import pandas as pd
from lib.layout_backtest import *
import redis
from flask import Flask, render_template, request
from collections import deque
from lib.logging_lib import *
from lib.charting_lib import *


cache = redis.Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)
dash_app.layout = layout_backtest


import pandas as pd
import json



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
    data = tmpdata[(tmpdata.index >= fromDate) & (tmpdata.index <= toDate)]


    json_raw_data={
        'stock':stock,
        'data':data.to_json(orient='records'),
        'algo':algo
    }

    json_df = pd.DataFrame(data=json_raw_data, index=['stock'])
    json_data = json_df.to_json(orient='records')
    cache.publish('backtest/data',json_data)
    #exec(algo)
    return render_charts(data, stock), cache.get('temp')