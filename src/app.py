import pandas as pd
from lib.layout_bootstrap import *
import redis
from flask import Flask, render_template, request
from collections import deque
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, redis_conn, cache_type
from lib.charting_lib import *
from lib.multitasking_lib import trade_analysis_raw

app = Flask(__name__)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)
dash_app.layout = layout_bootstrap

redis_conn.set('done'+cache_type,1)

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
    backtest_msg={'stock':stocks,'sl':sl,'target':target,'qty':qty,'algo':algo,'fromDate':fromDate,'toDate':toDate,'freq':freq}

    pdebug1(backtest_msg)
    # Step 2: Store the stock name under backtest in the redis cache
    for stock in stocks:
        redis_conn.set('stock',stock) #TODO: replace

    # Step 4: Done is set to 0: Backtest is in progress, will be resetted by backtest job
    redis_conn.set('done'+cache_type,0)
    # Step 5: Send the msg to backtest thread to initiate the back test
    pdebug(json.dumps(backtest_msg))
    redis_conn.publish('kite_simulator'+cache_type,json.dumps(backtest_msg))
    
    # Step 6: Return 0 to reset n_intervals count
    return 0 

@dash_app.callback(
    [Output('graph-update', 'disabled'),Output('button', 'disabled'),Output('button', 'children')],
    [Input('graph-update', 'n_intervals'), 
     Input('button', 'n_clicks')])
def update_intervals(n_intervals, clicks):
    pdebug1("Update Intervals: {}: {}".format(n_intervals, redis_conn.get('done')))

    # if done is set to 1 then backtest is complete -> Time to disable interval and enable backtest button
    if redis_conn.get('done'+cache_type) == "1": # Backtest complete
        pdebug("Returning True: Disable Interval")
        return True, False, 'Go' 
    else: # Backtest is in progress
        pdebug1("Returning False: Enable Interval")
        return False, True, 'Wait'

@dash_app.callback(
    [Output('select_chart', 'options'),Output('select_chart', 'value')],
    [Input('yaxis-column', 'value')])
def update_select_chart(values ):
    stock_select_options = pd.DataFrame({'label':values,'value':values}).to_dict(orient='records')
    return stock_select_options, values[0]

def freedom_chart(symbol):
    #key = symbol+cache_type+'OHLC'
    #key = symbol
    if not redis_conn.exists(symbol):
        return ""
    #    ohlc_df = pd.read_json(cache_raw)
    #    ohlc_df.index.rename('date', inplace=True)
    #    trade_df = pd.read_json(redis_conn.get(symbol+cache_type+'Trade'), orient='columns')
    #    return render_charts(ohlc_df, trade_df, symbol)

    ohlc_df = pd.read_json(redis_conn.get(symbol), orient='columns')
    ohlc_df.index.rename('date', inplace=True)
    trade_df = pd.read_json(redis_conn.get(symbol+cache_type+'Trade'), orient='columns')
    return render_charts(ohlc_df, trade_df, symbol)

@dash_app.callback(
    [Output('example-graph', 'figure'),
     Output('msg', 'children'), Output('trade_summary','children')],
    [Input('graph-update', 'n_intervals'), Input('select_chart', 'value')])
def update_output(n_intervals, value ):
    #stock = redis_conn.get('stock')
    stock = value
    pdebug1("In update output: {}".format(stock))
    
    logMsg = redis_conn.get('logMsg'+cache_type)
    fig = ''
    trade_summary = 'Ongoing ...'

    if redis_conn.get('done'+cache_type) == "1":
        fig = freedom_chart(stock) ## to reduce load on processor
        trade_df = pd.read_json( redis_conn.get(stock+cache_type+'Trade') )
        try:
            (total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log_df) = trade_analysis_raw(trade_df)
            trade_summary = df_to_table(trade_log_df, 'trade_summary_table', False)
        except:
            trade_summary = 'not enough data'
  
    return fig, logMsg, trade_summary


@dash_app.callback(
    [Output("alert-fade", "is_open"), Output("alert-fade", "children"), Output("alert-fade", "color"),
     Output("select_algo",'options')],
    [Input('algo-save', 'n_clicks')], 
    [State('algo', 'value'), State('algo-name', 'value'), State("alert-fade", "is_open")] )
def save_algo(n, algo, algo_name, is_open ):
    #pinfo(algo_name)
    #pinfo(algo)
    redis_conn.hset("algos",algo_name, algo)

    alert_is_open = is_open
    color = "success"
    msg= "Saved algo "+algo_name

    algo_list = redis_conn.hkeys('algos')
    algo_list_options = pd.DataFrame({'label':algo_list,'value':algo_list}).to_dict(orient='records')
    if n:
        alert_is_open =  not is_open

    try:
        algo_f = open("log/"+algo_name+".txt", "w")
        algo_f.write(algo)
    except:
        color = "danger"
        msg= "Failed to Saved algo "+algo_name
        return

    return alert_is_open, msg, color, algo_list_options

@dash_app.callback(
    Output("algo", "value"),
    [Input('select_algo', 'value')] )
def update_algo(algo_name ):

    algo = redis_conn.hget('algos',algo_name)
    return algo