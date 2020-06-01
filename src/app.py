from flask import Flask, redirect, url_for, request
from flask_login import LoginManager, login_required
from lib.data_model_lib import User, db
import os
import dash
import dash_html_components as html
import pandas as pd
from lib.layout_bootstrap import *
from flask import render_template, request, jsonify, session
from collections import deque
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, redis_conn, cache_type, cache_id, logger
from lib.charting_lib import *
from lib.multitasking_lib import trade_analysis_raw
import json
import os
from datetime import date, datetime
from decimal import Decimal
import dash_auth

#from lib.user_pass import *

db_url = os.environ.get('DATABASE_URL')
#pinfo(db_url)

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)



    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        return redirect(url_for('auth.login', _scheme='https',_external=True) + '?next=' + request.path)

    return app

app = create_app()


db.create_all(app=create_app())

dash_app = dash.Dash(
    __name__,
    server=app,
    external_stylesheets=external_stylesheets,
 #   routes_pathname_prefix='/dash/'
)

dash_app.layout = html.Div("My Dash app")

@app.route("/dash", methods=['POST','GET'])
@login_required
def dash_index():
    return dash_app.index()


######################



#auth = dash_auth.BasicAuth(
#    dash_app,
#    VALID_USERNAME_PASSWORD_PAIRS
#)

dash_app.layout = layout_bootstrap

backtest_cache = cache_state(cache_type)
live_cache = cache_state(cache_id)
backtest_cache.set('done'+cache_type,1)

def store_algo(algo, algo_name="default"):
    live_cache.hset("algos",algo_name, algo)
    algo_f = open("algo/"+algo_name+".txt", "w")
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

    try:
        pinfo("==========: {} :========".format(session["access_token"]))
    except:
        perror("Access Token Not found")
        #return 0

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
        backtest_cache.set('stock',stock) #TODO: replace

    # Step 4: Done is set to 0: Backtest is in progress, will be resetted by backtest job
    backtest_cache.set('done'+cache_type,0)
    # Step 5: Send the msg to backtest thread to initiate the back test
    pdebug(json.dumps(backtest_msg))
    backtest_cache.publish('kite_simulator'+cache_type,json.dumps(backtest_msg))
    
    # Step 6: Return 0 to reset n_intervals count
    return 0 

@dash_app.callback(
    [Output('graph-update', 'disabled'),Output('button', 'disabled'),Output('button', 'children')],
    [Input('graph-update', 'n_intervals'), 
     Input('button', 'n_clicks')])
def update_intervals(n_intervals, clicks):
    pdebug1("Update Intervals: {}: {}".format(n_intervals, backtest_cache.get('done')))
 
    # if done is set to 1 then backtest is complete -> Time to disable interval and enable backtest button
    if backtest_cache.get('done'+cache_type) == "1": # Backtest complete
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

    summary_stat = datetime.fromtimestamp(float(backtest_cache.hget(stock+cache_type, 'last_processed')))

    if backtest_cache.get('done'+cache_type) == "1":
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
            #trade_log_df = trade_log_df.map("{:,.0f}".format) backtest_cache
            if 'mode' in trade_log_df.columns:
                trade_summary = df_to_table(trade_log_df[['date','mode','buy','sell','profit','CumProfit']], 'trade_summary_table', False)
            else:
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

    algo_list = backtest_cache.hkeys('algos')
    algo_list_options = pd.DataFrame({'label':algo_list,'value':algo_list}).to_dict(orient='records')
    if n:
        alert_is_open =  not is_open

    return alert_is_open, msg, color, algo_list_options

@dash_app.callback(
    [Output("algo", "value"), Output('algo-name', 'value')],
    [Input('select_algo', 'value')] )
def update_algo(algo_name ):

    algo = backtest_cache.hget('algos',algo_name)
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


is_connected = lambda : True if live_cache.get('Kite_Status') == 'connected' or live_cache.get('Kite_Status') == 'connecting' else False 
import time


def get_live_table(df, tab='monitor'):
    if df.shape[0] > 0:
        if tab == 'monitor':
            df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state', 'ltp','last_processed',
        'amount', 'price','P&L','P&L %', 'Total P&L', 'Total P&L %','low', 'sl',  'ltp %','tp', 'high']]

            columns = [{"name": i, "id": i} for i in df.columns]
            return df.to_dict('records'), columns
        else:
            df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state']]

            columns = [{"name": 'stock', "id": 'stock'},{"name": 'qty', "id": 'qty'},{"name": 'TP %', "id": 'TP %'},
            {"name": 'SL %', "id": 'SL %'},{"name": 'algo', "id": 'algo'},{"name": 'freq', "id": 'freq'},
            {"name": 'mode', "id": 'mode'},{"name": 'state', "id": 'state'}]
            
            live_dropdown = {
                    'freq': {
                        'options': [{'label': '1D', 'value': '1D'}, {'label': '1T', 'value': '1T'}]
                    }
                }
            pinfo(live_dropdown)
            return df.to_dict('records'), columns
    else:
        return [],[{}]


@dash_app.callback(
    [Output('table-editing-simple', 'data'),
    Output('table-editing-simple', 'columns')
    ],
    [Input('stock_picker_live', 'value'), Input('table-editing-simple', 'data_timestamp') ],
    [State('table-editing-simple', 'data'),
     State('table-editing-simple', 'columns')])  
def add_row(values, ts, rows, columns):
    df_table_new = pd.DataFrame.from_dict(rows)
    df_cache = live_cache.getValue()
    cache_keys =  live_cache.getKeys()

    if values is not None: #Addition of new stock in the list
        for value in values:
            if value not in cache_keys:
                symbol = value
                live_cache.add(symbol)
                live_cache.setValue(symbol,'qty','1')
                live_cache.setValue(symbol,'SL %','0.4')
                live_cache.setValue(symbol,'TP %','1')
                live_cache.setValue(symbol,'algo','haikin_1_new')
                live_cache.setValue(symbol,'freq','1T')
                live_cache.setValue(symbol,'last_processed',datetime.now().timestamp())
                live_cache.setValue(symbol,'mode','paper')

                token = int(live_cache.hmget('eq_token',symbol)[0])

                live_cache.sadd('ticker_list',token)
                
                stock_list = list(map(int,live_cache.smembers('ticker_list')))

                live_cache.publish('kite_ticker_handlerlive', json.dumps({'cmd':'add','value':stock_list,'mode':'ltp'}))
                return get_live_table(live_cache.getValue(), 'setup')

    #TODO: Removal of last stock
    if df_cache.shape[0] > df_table_new.shape[0]: # Removal of stock
        for key in cache_keys:
            try:
                if not key in df_table_new['stock'].values:
                    symbol = key
                    token = int(live_cache.hmget('eq_token',symbol)[0])
                    live_cache.srem('ticker_list',token)
                    live_cache.publish('kite_ticker_handlerlive', json.dumps({'cmd':'remove','value':[token],'mode':'ltp'}))
                    live_cache.remove(symbol)
            except:
                pass

    for index, row in  df_table_new.iterrows():  
            #pinfo("Updated stock: {}".format(row['stock']))
            live_cache.setValue(row['stock'], 'qty', row['qty'])
            live_cache.setValue(row['stock'], 'TP %', row['TP %'])
            live_cache.setValue(row['stock'], 'SL %', row['SL %'])
            live_cache.setValue(row['stock'], 'algo', row['algo'])
            live_cache.setValue(row['stock'], 'freq', row['freq'])
            live_cache.setValue(row['stock'], 'mode', row['mode'])
            live_cache.setValue(row['stock'], 'state', row['state'])
            # TODO: If mode == Pause, continue getting ticks, only pause tradejob. Live/Paper Trade in Order Placement

            
            #state = row['state']
            #prev_state = live_cache.getValue(row['stock'], 'state')
            #if state != prev_state:
            #    order_id = live_cache.getValue(row['stock'], 'order_id')
                #TODO: User initiated Buy/Sell, Cancel
            #live_cache.setValue(row['stock'], 'state', row['state'])
 
    return get_live_table(live_cache.getValue(), 'setup')


@dash_app.callback(
    [ Output('table-editing-monitor', 'data'),
    Output('table-editing-monitor', 'columns')
    ],
    [Input('live-table-update', 'n_intervals')])  
def refresh_trade_monitor(n_intervals):
    return get_live_table(live_cache.getValue())


@dash_app.callback(
    Output('reset-live', 'value'),
    [Input('reset-live', 'n_clicks')])  
def resete_live_cache(n_clicks):

    if n_clicks > 0:
        for stock in live_cache.getKeys():
            live_cache.add(stock, True)
    
    live_cache.publish('order_handlerlive',json.dumps({'cmd':'cancelAll'}))
    return 'Reset'


@dash_app.callback(
    Output('live-status', 'children'),
    [Input('live-table-update', 'n_intervals')])  
def refresh_live_status(n_intervals):
    status = 'connecting ...'
    try:
        status = 'Ticker Status:' + live_cache.get('Kite_Status') + ' | Total Ticks: ' +  live_cache.get('tick_count')

        val = live_cache.get('last_id_msglive')
        dateval = datetime.fromtimestamp(int(val.split('-')[0] )/1000).strftime('%d-%m-%y %H:%M:%S')

        status = status + ' | last_id_msg: ' + dateval

        peek_msg_queue = live_cache.xrange('msgBufferQueuelive')[-1]
        dateval = datetime.fromtimestamp(int(peek_msg_queue[0].split('-')[0] )/1000).strftime('%d-%m-%y %H:%M:%S')
        status = status + ' | last MsgQueue: ' + dateval
    except:
        pass

    return status

@dash_app.callback(
    [Output("live-start", "disabled"), Output("live-stop", "disabled")],
    [Input('live-start', 'n_clicks'), Input('live-stop', 'n_clicks')],
    [State('live-start', 'disabled'),State('live-stop', 'disabled')] )
def toggle_trade(n1, n2, d1, d2):
    if n2 > 0 and d1 == True: #Trade is onoging: Connected
        if is_connected() == True:
            live_cache.publish('kite_ticker_handlerlive', 'CLOSE')
            pinfo('Stopping Connection')
        else:
            pinfo("Connection is already closed")
        return False, True
    elif n1 > 0 and d2 == True: # Trade is stopped: Closed
        if  is_connected() == False:
            live_cache.publish('kite_ticker_handlerlive', 'START')
            live_cache.set('Kite_Status','connecting')
            pinfo('Start Trade')
        return True, False

    return False, True

@dash_app.callback(
    [Output("order-pause", "children"),Output("order-pause", "color")],
    [Input('order-pause', 'n_clicks')],
    [State('order-pause', 'children')] )
def toggle_trade(n1, v):
    pinfo(v)
    if n1 == 0:
        return 'Order Pause', "danger"
    if v == 'Order Pause':
        live_cache.publish('order_handlerlive', 'pause')
        return 'Order Resume', "success"
    live_cache.publish('order_handlerlive', 'resume')
    return 'Order Pause', "danger"