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


cache.set('done',1)
import pandas as pd
import json
@dash_app.callback(
    Output('graph-update', 'n_intervals'),
    [Input('button', 'n_clicks')],
    [State('yaxis-column','value'), 
    State('input-qty', 'value'), 
    State('input-sl', 'value'),
    State('input-target', 'value'),
    State('date-picker-range', 'start_date'), State('date-picker-range', 'end_date'),
    State('algo','value'), State('freq','value')])
def start_backtest(n_clicks, stocks, qty, sl, target, start_date, end_date, algo, freq ):
    toDate = end_date
    fromDate = start_date
    
    if not isinstance(stocks,list):
        stocks = [stocks]

    pdebug1(stocks)
    # Step 1: Create the msg for initiating backtest
    backtest_msg={
        'stock':stocks,
        'sl':sl,
        'target':target,
        'qty':qty,
        #'data':data.to_json(orient='records'),
        'algo':algo,
        'fromDate':fromDate,
        'toDate':toDate,
        'freq':freq
    }

    pdebug1(backtest_msg)
    # Step 2: Store the stock name under backtest in the redis cache
    for stock in stocks:
        cache.set('stock',stock)
        # Step 3 : Store the OHLC and backtest data in the redis: to be used by plotter
        ohlc_dict = '[{"date":'+json.dumps(fromDate)+',"close":0,"high":0,"low":0,"open":0,"volume":0}]'
        cache.set(stock,ohlc_dict)

    # Step 4: Done is set to 0: Backtest is in progress, will be resetted by backtest job
    cache.set('done',0)
    # Step 5: Send the msg to backtest thread to initiate the back test
    cache.publish('kite_simulator',json.dumps(backtest_msg))
    
    # Step 6: Return 0 to reset n_intervals count
    return 0 

@dash_app.callback(
    [Output('graph-update', 'disabled'),Output('button', 'disabled'),Output('button', 'children')],
    [Input('graph-update', 'n_intervals'), 
     Input('button', 'n_clicks')])
def update_intervals(n_intervals, clicks):
    pdebug1("Update Intervals: {}: {}".format(n_intervals, cache.get('done')))

    # if done is set to 1 then backtest is complete -> Time to disable interval and enable backtest button
    if cache.get('done') == "1": # Backtest complete
        pdebug5("Returning True: Disable Interval")
        return True, False, 'BACKTEST: Start' 
    else: # Backtest is in progress
        pdebug1("Returning False: Enable Interval")
        return False, True, 'BACKTEST: In Progress'


def freedom_chart(symbol):
    ohlc_df = pd.read_json(cache.get(symbol), orient='columns')
    ohlc_df.index.rename('date', inplace=True)
    trade_df = pd.read_json(cache.get(symbol+'Trade'), orient='columns')

    return render_charts(ohlc_df, trade_df, symbol)

@dash_app.callback(
    [Output('example-graph', 'figure'),
     Output('msg', 'children')],
    [Input('graph-update', 'n_intervals')])
def update_output(n_intervals ):
    stock = cache.get('stock')
    pdebug1("In update output: {}".format(stock))
    
    logMsg = cache.get('logMsg')
    fig = ''

    if cache.get('done') == "1":
    #if n_intervals % 10 == 0:
        #pinfo(n_intervals)
        fig = freedom_chart(stock) ## to reduce load on processor
  
    return fig, logMsg
