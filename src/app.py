import pandas as pd
from lib.layout_bootstrap import *
from flask import Flask, render_template, request
from collections import deque
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, redis_conn, cache_type, cache_id, logger
from lib.charting_lib import *
from lib.multitasking_lib import trade_analysis_raw
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

dash_app = dash.Dash(__name__, server=app, external_stylesheets=external_stylesheets)
dash_app.layout = layout_bootstrap

redis_conn.set('done'+cache_type,1)

def store_algo(algo, algo_name="default"):
    redis_conn.hset("algos",algo_name, algo)
    algo_f = open("log/"+algo_name+".txt", "w")
    algo_f.write(algo)
    algo_f.close()


@dash_app.callback(
    Output('graph-update', 'n_intervals'),
    [Input('button', 'n_clicks')],
    [State('yaxis-column','value'), 
    State('input-qty', 'value'), 
    State('input-sl', 'value'),
    State('input-target', 'value'),
    State('date-picker-range', 'start_date'), State('date-picker-range', 'end_date'),
    State('algo','value'), State('freq','value'), State('algo-name', 'value'), State('switches-input', 'value')])
def start_backtest(n_clicks, stocks, qty, sl, target, start_date, end_date, algo, freq, algo_name, mode ):
    toDate = end_date
    fromDate = start_date

    if n_clicks == 0:
        return 0
    
    if len(mode) > 0:
        backtest = 'quick'
    else:
        backtest = 'full'

    if not isinstance(stocks,list):
        stocks = [stocks]

    pdebug1(stocks)
    # Step 1: Create the msg for initiating backtest
    #pinfo(freq)
    backtest_msg={'stock':stocks,'sl':sl,'target':target,'qty':qty,'algo':algo_name,'fromDate':fromDate,'toDate':toDate,'freq':freq, 'mode':backtest}

    try:
        store_algo(algo, algo_name)
    except:
        perror('Something went wrong while saving algo')

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

    val = ""
    #pinfo(values.len)
    if len(values) != 0:
        val = values[0]

    return stock_select_options, val

@dash_app.callback(
    [Output('example-graph', 'figure'),
     Output('msg', 'children'), Output('trade_summary','children'), Output('trade_stat','children')],
    [Input('graph-update', 'n_intervals'), Input('select_chart', 'value'), Input('chart_type', 'value')])
def update_output(n_intervals, value, chart_type ):
    #stock = redis_conn.get('stock')
    stock = value
    pdebug1("In update output: {}".format(stock))
    
    try:
        fh = open('log/freedom_trade.log','r')
        logMsg = fh.read()
        fh.close()
        #logMsg = redis_conn.get('logMsg'+cache_type)
    except:
        logMsg = "Something went wrong !!"

    fig = ''
    trade_summary = 'Ongoing ...'

    if stock == '':
        return fig, 'logMsg', 'No option selected', ''

    summary_stat = redis_conn.hget(stock+cache_type, 'last_processed')

    if redis_conn.get('done'+cache_type) == "1":
        fig = freedom_chart(stock, cache_type, chart_type) ## to reduce load on processor
        trade_df = pd.read_json( redis_conn.get(stock+cache_type+'Trade') )

        try:
            (total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log_df) = trade_analysis_raw(trade_df)
            
            summary_stat = 'Total Profit: {:.02f}, Max Drawdown: {:.02f}, Max Profit {:.02f}'.format(total_profit, max_loss, max_profit)
            #summary_stat = summary_stat + html.Br()
            summary_stat = summary_stat + '\n Win: {}, Loss: {}, Longest Streak => Win: {}, Loss: {}'.format(total_win, total_loss, max_winning_streak, max_loosing_streak)

            trade_log_df['profit'] = trade_log_df['profit'].map("{:,.02f}".format)
            trade_log_df['CumProfit'] = trade_log_df['CumProfit'].map("{:,.02f}".format)
            trade_log_df['date'] = trade_log_df.index
            #trade_log_df = trade_log_df.map("{:,.0f}".format)
            trade_summary = df_to_table(trade_log_df[['date','mode','buy','sell','profit','CumProfit']], 'trade_summary_table', False)
        except:
            trade_summary = 'not enough data'
  
    return fig, logMsg, trade_summary, summary_stat

@dash_app.callback(
    [Output("alert-fade", "is_open"), Output("alert-fade", "children"), Output("alert-fade", "color"),
     Output("select_algo",'options')],
    [Input('algo-save', 'n_clicks')], 
    [State('algo', 'value'), State('algo-name', 'value'), State("alert-fade", "is_open")] )
def save_algo(n, algo, algo_name, is_open ):
    #pinfo(algo_name)
    #pinfo(algo)
    alert_is_open = is_open
    color = "success"
    msg= "Saved algo "+algo_name

    try:
        store_algo(algo, algo_name)
    except:
        color = "danger"
        msg= "Failed to Save algo "+algo_name
        return

    algo_list = redis_conn.hkeys('algos')
    algo_list_options = pd.DataFrame({'label':algo_list,'value':algo_list}).to_dict(orient='records')
    if n:
        alert_is_open =  not is_open

    return alert_is_open, msg, color, algo_list_options

@dash_app.callback(
    [Output("algo", "value"), Output('algo-name', 'value')],
    [Input('select_algo', 'value')] )
def update_algo(algo_name ):

    algo = redis_conn.hget('algos',algo_name)
    return algo, algo_name

@dash_app.callback(
    Output("console_log", "children"),
    [Input('cmd-btn', 'n_clicks'), Input('cmd-text', 'n_submit')], [State('cmd-text','value')] )
def console_cmd(n_clicks, n_submit, cmd ):

    try:
        exec(cmd)
        fh = open('log/freedom.log','r')
        console_log = fh.read()
        fh.close()
    except:
        return "Something went wrong !!"
    
    return console_log



@dash_app.callback(
    [Output('table-editing-simple', 'data'),
    Output('table-editing-simple', 'columns')],
    [Input('stock_picker_live', 'value'), Input('table-editing-simple', 'data_timestamp')
    , Input('live-table-update', 'n_intervals')],
    [State('table-editing-simple', 'data'),
     State('table-editing-simple', 'columns')])
def add_row(value, ts, n_intervals, rows, columns):
    live_cache = cache_state(cache_id)
    df_updates = pd.DataFrame.from_dict(rows)
    df_cache = live_cache.getValue()

    df = df_cache


    #TODO: Send message to live_trade_handler

    if df.shape[0] > 0:
        df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state', 'ltp',
       'amount', 'price','P&L','P&L %', 'Total P&L', 'Total P&L %','low', 'sl',  'ltp %','tp', 'high', 'last_processed']]
            
        return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
    else:
        return [],[{}]

    #TODO : to be fixed, current implementation is causing serious issues
    
    if df_updates.shape[0] > 0 and df_cache.shape[0] > 0: # Cache is not empty: need to distinguish new vs update
        for stock in df_cache[ df_cache['stock'].isin(df_updates['stock']) == False]['stock']: #Stocks which are present in cache but not in GUI
            pinfo("Removed stock: {}".format(stock))
            live_cache.remove(stock)
            #TODO: Send message to unsubscribe

            #token = int(live_cache.hmget('eq_token',stock)[0])
            #live_cache.srem('ticker_list',token)
            #live_cache.publish('kite_ticker_handlerlive', json.dumps({'cmd':'remove','value':[token], 'mode':'ltp'}))

        for index, row in  df_updates.iterrows():  #Stocks which are present in cache
            pinfo("Updated stock: {}".format(row['stock']))
            live_cache.setValue(row['stock'], 'qty', row['qty'])
            live_cache.setValue(row['stock'], 'TP %', row['TP %'])
            live_cache.setValue(row['stock'], 'SL %', row['SL %'])
            live_cache.setValue(row['stock'], 'algo', row['algo'])
            live_cache.setValue(row['stock'], 'freq', row['freq'])
            live_cache.setValue(row['stock'], 'mode', row['mode'])
            # TODO: If mode == Pause, continue getting ticks, only pause tradejob. Live/Paper Trade in Order Placement

            
            state = row['state']
            prev_state = live_cache.getValue(row['stock'], 'state')
            if state != prev_state:
                order_id = live_cache.getValue(row['stock'], 'order_id')
                #TODO: User initiated Buy/Sell, Cancel
            live_cache.setValue(row['stock'], 'state', row['state'])
    else: #both zero
        pinfo("Remove all the stock")
        
        #token = int(live_cache.hmget('eq_token',df_updates['stock'])[0])
        #live_cache.srem('ticker_list',token)
        #live_cache.publish('kite_ticker_handlerlive', json.dumps({'cmd':'remove','value':[token], 'mode':'ltp'}))
        live_cache.remove()
        
    try:
        for stock in value: #Changes done in the selector
            live_cache.add(stock)
            #live_cache.setValue(stock,'qty','1')
            #live_cache.setValue(stock,'SL %','0.4')
            #live_cache.setValue(stock,'TP %','1')
            #live_cache.setValue(stock,'algo','haikin_1_new')
            #live_cache.setValue(stock,'freq','1T')
            #live_cache.setValue(stock,'mode','paper')

            pinfo("Added stock: {}".format(stock))

            #Send message to subscribe for the stock
            
            token = int(live_cache.hmget('eq_token',stock)[0])
            live_cache.sadd('ticker_list',token)
            live_cache.publish('kite_ticker_handlerlive', json.dumps({'cmd':'add','value':[token], 'mode':'ltp'}))
            
    except:
        pass


    df = live_cache.getValue()


    #TODO: Send message to live_trade_handler

    if df.shape[0] > 0:
        df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state',
       'amount', 'price','P&L','P&L %', 'Total P&L', 'Total P&L %','low', 'sl', 'ltp', 'ltp %','tp', 'high', 'last_processed']]
            
        return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
    else:
        return [],[{}]

import time
@dash_app.callback(
    [Output("live-start", "disabled"), Output("live-stop", "disabled")],
    [Input('live-start', 'n_clicks'), Input('live-stop', 'n_clicks')],
    [State('live-start', 'disabled'),State('live-stop', 'disabled')] )
def toggle_trade(n1, n2, d1, d2):
    live_cache = cache_state(cache_id)
    return False, True

    if n2 > 0 and d1 == True: #Trade is onoging
        if live_cache.get('Kite_Status') == 'connected':
            live_cache.publish('kite_ticker_handlerlive', 'CLOSE')
        pinfo('Stop Trade')
        
        return False, True
    elif n1 > 0 and d2 == True: # Trade is stopped
        if live_cache.get('Kite_Status') != 'connected':
            live_cache.publish('kite_ticker_handlerlive', 'START')
        pinfo('Start Trade')
        return True, False

    return False, True

#@dash_app.callback(
#    Output("live-stop", "active"),
#    [Input('live-stop', 'n_clicks')] )
#def start_trade(n_clicks):
#    live_cache = cache_state(cache_id)
#    if n_clicks % 2 == 1:
#        pinfo('Stop Trade')
#        live_cache = cache_state(cache_id)
#        live_cache.publish('live_trade_handlerlive', 'CLOSE')
#        return True
#    else:
#        return False

########################### Kite Login ###########################
import os
import json
#import logging
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, request, jsonify, session
from kiteconnect import KiteConnect

#logging.basicConfig(level=logging.DEBUG)

# Base settings
#PORT = 5010
HOST = "127.0.0.1"

serializer = lambda obj: isinstance(obj, (date, datetime, Decimal)) and str(obj)  # noqa

# Kite Connect App settings. Go to https://developers.kite.trade/apps/
# to create an app if you don't have one.
kite_api_key = 'b2w0sfnr1zr92nxm'
kite_api_secret = 'jtga2mp2e5fn29h8w0pe2kb722g3dh1q'

# Create a redirect url
redirect_url = "http://{host}/login".format(host=HOST)

# Login url
login_url = "https://kite.trade/connect/login?api_key={api_key}".format(api_key=kite_api_key)

# Kite connect console url
console_url = "https://developers.kite.trade/apps/{api_key}".format(api_key=kite_api_key)


def get_kite_client():
    """Returns a kite client object
    """
    kite = KiteConnect(api_key=kite_api_key)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    return kite

# Templates
index_template = """
    <div>Make sure your app with api_key - <b>{api_key}</b> has set redirect to <b>{redirect_url}</b>.</div>
    <div>If not you can set it from your <a href="{console_url}">Kite Connect developer console here</a>.</div>
    <a href="{login_url}"><h1>Login to generate access token.</h1></a>"""

login_template = """
    <h2 style="color: green">Success</h2>
    <div>Access token: <b>{access_token}</b></div>
    <h4>User login data</h4>
    <pre>{user_data}</pre>
    <a target="_blank" href="/holdings.json"><h4>Fetch user holdings</h4></a>
    <a target="_blank" href="/orders.json"><h4>Fetch user orders</h4></a>
    <a target="_blank" href="https://localhost"><h4>Start Trading with Freedom</h4></a>"""


@app.route("/oauth")
def index():
    return index_template.format(
        api_key=kite_api_key,
        redirect_url=redirect_url,
        console_url=console_url,
        login_url=login_url
    )

@app.route("/login")
def login():
    request_token = request.args.get("request_token")

    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""

    kite = get_kite_client()
    data = kite.generate_session(request_token, api_secret=kite_api_secret)
    access_token = data["access_token"]
    session["access_token"] = access_token
    cache_live = cache_state(cache_id)
    cache_live.set('access_token', access_token)
    kite.set_access_token(access_token)

    return login_template.format(
        access_token=access_token,
        user_data=json.dumps(
            data,
            indent=4,
            sort_keys=True,
            default=serializer
        )
    )

@app.route("/holdings.json")
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())


@app.route("/orders.json")
def orders():
    kite = get_kite_client()
    return jsonify(orders=kite.orders())