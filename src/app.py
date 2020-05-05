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

def store_algo(algo, algo_name="default"):
    redis_conn.hset("algos",algo_name, algo)
    algo_f = open("log/"+algo_name+".txt", "w")
    algo_f.write(algo)
    algo_f.close()

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
    State('algo','value'), State('freq','value'), State('algo-name', 'value')])
def start_backtest(n_clicks, stocks, qty, sl, target, start_date, end_date, algo, freq, algo_name ):
    toDate = end_date
    fromDate = start_date
    
    if not isinstance(stocks,list):
        stocks = [stocks]

    pdebug1(stocks)
    # Step 1: Create the msg for initiating backtest
    backtest_msg={'stock':stocks,'sl':sl,'target':target,'qty':qty,'algo':algo_name,'fromDate':fromDate,'toDate':toDate,'freq':freq}

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
    return stock_select_options, values[0]

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
    summary_stat = redis_conn.hget(stock+cache_type, 'last_processed')

    if redis_conn.get('done'+cache_type) == "1":
        fig = freedom_chart(stock, chart_type) ## to reduce load on processor
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

#@dash_app.callback(
#    Output('table-editing-simple', 'data'),
#    [Input('stock_picker_live', 'value')])
#def update_live_table(value ):
#    live_cache = cache_state('live')
#    for stock in value:
#        pinfo(stock)
        #live_cache.add(stock)
#        return df_to_table(live_cache.getValue(), 'table-editing-simple', True)

@dash_app.callback(
    [Output('table-editing-simple', 'data'),
    Output('table-editing-simple', 'columns')],
    [Input('stock_picker_live', 'value'), Input('table-editing-simple', 'data_timestamp')],
    [State('table-editing-simple', 'data'),
     State('table-editing-simple', 'columns')])
def add_row(value, ts, rows, columns):
    live_cache = cache_state('live')
    df_updates = pd.DataFrame.from_dict(rows)
    df_cache = live_cache.getValue()
    

    if df_updates.shape[0] > 0 and df_cache.shape[0] > 0:
        for stock in df_cache[df_cache['stock'].isin(df_updates['stock']) == False]['stock']:
            live_cache.remove(stock)
            pinfo("Removed stock: {}".format(stock))

        for index, row in  df_updates.iterrows():
            live_cache.setValue(row['stock'], 'qty', row['qty'])
            live_cache.setValue(row['stock'], 'TP %', row['TP %'])
            live_cache.setValue(row['stock'], 'SL %', row['SL %'])
            live_cache.setValue(row['stock'], 'algo', row['algo'])
            live_cache.setValue(row['stock'], 'freq', row['freq'])
    else:
        live_cache.remove()
        
    try:
        for stock in value:
            live_cache.add(stock)
            pinfo("Added stock: {}".format(stock))
    except:
        pass


    df = live_cache.getValue()


    #TODO: Send message to live_trade_handler

    if df.shape[0] > 0:
        df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 
        'amount', 'p_n_l', 'Total_p_n_l', 'low', 'sl', 'ltp', 'tp', 'high', 'mode','state','last_processed']]
            
        return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
    else:
        return [],[{}]
