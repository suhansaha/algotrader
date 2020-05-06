import threading
import time
import pandas as pd
import math
from queue import Queue
from redis import Redis
import multiprocessing
import numpy as np
from lib.logging_lib import *
from lib.kite_helper_lib import *
from lib.algo_lib import *
from lib.data_model_lib import *
import sys
import json
import ast
from datetime import datetime, timedelta
import time

logger.setLevel(logging.DEBUG)
#logger.setLevel(1)
loggerT.setLevel(21)
# The base thread class to enable multithreading
class myThread (threading.Thread):
    def __init__(self, manager, name, callback, pubsub=True, msg=""):
        threading.Thread.__init__(self)
        self.threadID = manager.threadID
        self.name = name
        self.callback = callback
        self.pubsub = pubsub
        self.manager = manager
        self.msg = msg
        
    def run(self):
        pdebug1("Starting " + self.name)
        if self.pubsub:
            pinfo("Starting Handler: " + self.name)
            self.thread_pubsub(self.callback)
            pinfo("Terminating Handler: " + self.name)
        else:
            self.thread_worker(self.callback)
        pdebug1("Exiting " + self.name)
    
    # The thread function for infinite threads which can expect IPC using Redis
    def thread_pubsub(self, callback):
        pubsub = cache.pubsub()
        pubsub.subscribe([self.name+cache_postfix])
        #pubsub.get_message(self.name+cache_postfix)

        for item in pubsub.listen():
            msg = item['data']
            if msg == 'stop':
                pubsub.unsubscribe()
                break
            else:
                callback(self.manager, msg)
    
    #The thread function for one of tasks
    def thread_worker(self, callback):
        callback(self.msg)

jobs = []
cache_postfix = ""
cache = ""
class threadManager():
    def __init__(self, name, thread_list, callback_list):
        self.threads = []
        self.name = name
        self.threadList = thread_list
        self.threadCallback = callback_list
        self.threadID = 1
        
        self.job = multiprocessing.Process(target=self.init)
        jobs.append(self.job)
        self.job.start()
        
    def init(self):
        global cache_postfix, cache
        cache_postfix = self.name
        cache = cache_state(cache_postfix)
        # Create new threads
        for tName in self.threadList:
            self.add(tName, self.threadCallback[self.threadID-1])

        # Wait for all threads to complete
        #for t in self.threads:
        #    t.join()
        #pinfo("Exiting Main Thread")
        
    def add(self, name, callback, pubsub=True, cmd=""):
        # Create an instance of mythrade class and start the thread
        thread = myThread(self, name, callback, pubsub, cmd)
        thread.start()
        self.threads.append(thread)
        self.threadID += 1


######################################################
###                Freedom App                     ###
######################################################
no_of_hist_candles = 100
getDeltaT = lambda freq: timedelta(days=no_of_hist_candles*2) if freq == 'day' else timedelta(days=5)

def trade_analysis(stock):
    pdebug1("trade_analysis: {}".format(stock))
    trade_log = cache.getTrades(stock)
    (total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log_df) = trade_analysis_raw(trade_log)

    logtrade('''
 ====================================================
 *** Trade Analysis for : {}
 ----------------------------------------------------
  Total Profit: {:.2f}
  Max Loss: {:.2f}, Max Win: {:.2f}
  # of Win: {}, # of Loss: {}
  Longest Winning Streak: {}, Longest Loosing Streak: {}
 ----------------------------------------------------
 {}
 ===================================================='''.format(stock, total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log_df.fillna(''))  )


def trade_analysis_raw(trade_log):
    state = 'None'
    trade_log['profit'] = 0
    profit = 0
    total_win = 0
    total_loss = 0
    max_profit = 0 
    max_loss = 0
    winning_streak = 0
    loosing_stream = 0
    prev_profit = 0
    winning_streak = 1
    loosing_streak = 1
    max_winning_streak = 0
    max_loosing_streak = 0

    
    try:
        for index, row in trade_log.iterrows():
            if not math.isnan(row.buy):
                profit -= row['buy'] 
            if not math.isnan(row.sell):
                profit += row['sell']

            if state=='None':
                trade_log.loc[index,'profit'] = 0
                state='Trade'
            else:
                trade_log.loc[index,'profit'] = profit
                if profit >=0:
                    total_win += 1
                    if profit > max_profit:
                        max_profit = profit

                    if prev_profit > 0:
                        winning_streak += 1
                    elif loosing_streak > max_loosing_streak:
                        max_loosing_streak = loosing_streak
                    loosing_streak = 1    

                else:
                    total_loss += 1
                    if profit < max_loss:
                        max_loss = profit

                    if prev_profit < 0:
                        loosing_streak += 1
                    elif winning_streak > max_winning_streak:
                        max_winning_streak = winning_streak
                    winning_streak = 1

                prev_profit = profit
                profit = 0
                state = 'None'

        total_profit = trade_log.profit.sum()
        trade_log['CumProfit'] = trade_log.profit.cumsum()
    except:
        perror('Something wrong in TradeAnalysis')

    return (total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log)


def msg_to_ohlc(data):
    ohlc_list = list(data.values())[0]['ohlc']
    sdate = ohlc_list['date']
    shigh = ohlc_list['high']
    slow = ohlc_list['low']
    sopen = ohlc_list['open']
    sclose = ohlc_list['close']
    svolume = ohlc_list['volume']

    temp_df = pd.DataFrame(ohlc_list, columns=['open','high','low','close','volume'], 
                           index=[datetime.strptime(ohlc_list['date'],'%Y-%m-%d %H:%M:%S')])
    
    return temp_df


# This function is called by Kite or Kite_Simulation
def notification_despatcher(ws, msg, Tick=True ):
    pdebug1('notification_despatcher: {}'.format(msg))
    # Step 1: Extract msg type: Tick/Callbacks
    
    # Step 2.1: If Tick
    if Tick == True:
        # Push msg to msgBufferQueue
        msg_id = cache.xadd('msgBufferQueue'+cache_postfix,{'msg': msg})
        pdebug1("Despatcher: {}".format(msg_id))
    
    # Step 2.2: else
    else:
        # Push msg to notificationQueue
        cache.xadd('notificationQueue'+cache_postfix,{'msg': msg})

###################### BackTest ######################
'''
# backtest/data
{
'stock':'NIFTY',
'ohlc':[],
'algo':'BO'
}


'''

trade_lock_store = {} 
simulator_lock = Lock()
def trade_init(stock_key, algo, freq, qty, sl, target):        
    # Initialize state
    pdebug("Trade_init: {}".format(stock_key))

    cache.add(stock_key, reset=True)

    cache.setValue(stock_key, 'algo', algo)
    cache.setValue(stock_key, 'freq', freq)
    cache.setValue(stock_key, 'qty', qty)
    cache.setValue(stock_key, 'SL %', sl)
    cache.setValue(stock_key, 'TP %', target)
    cache.setValue(stock_key, 'P&L', 0)
    cache.setValue(stock_key, 'Total P&L', 0)
    cache.setValue(stock_key, 'price', 0)

    #cache.set(stock_key, pd.DataFrame().to_json(orient='columns')) #Used for plotting
    
    trade_lock_store[stock_key] = Lock()


def kite_simulator(manager, msg):
    pdebug('kite_simulator: {}'.format(msg))

    try:
        data = json.loads(msg)
    except:
        perror('kite_simulator: Invalid msg: {}'.format(msg))
        return
    
    toDate = data['toDate']
    fromDate = data['fromDate']
    algo = data['algo']
    sl = data['sl']
    target = data['target']
    qty = data['qty']

    startDate = datetime.strptime(fromDate,'%Y-%m-%d') 
    exchange = 'NSE'
    freq = data['freq']
    algo = data['algo']
    if not freq == 'day':
        freq='minute'

    ohlc_data = {}
    for stock_key in data['stock']: #Initialize
        # Load data from the Cache
        df = getData(stock_key, startDate, toDate, exchange, freq, False, stock_key)
        ohlc_data[stock_key] = df
        trade_init(stock_key, algo, freq, qty, sl, target)

    cache.publish('tick_handler'+cache_postfix,'start')

    #cache.set('logMsg'+cache_postfix,'Backtest Started: {} :\n'.format(stock)) # Used for displaying trade log

    stock = data['stock'][-1]
    no = ohlc_data[stock].shape[0]
    counter = 0
    for i in np.linspace(0,no-1,no): # Push data
        i = int(i)

        for stock in  data['stock']:
            row = ohlc_data[stock].iloc[i]
            index = ohlc_data[stock].index[i]
        
            # Construct Json message like Kite
            mydate = "{}-{}-{} {}:{}:{}".format(index.year,index.month,index.day, index.hour, index.minute, index.second)        
            msg = {exchange+":"+stock:{"ohlc":{'date':mydate,'open':row['open'],'high':row['high'],'low':row['low'],'close':row['close'],'volume':row['volume']}}}
            pdebug1(msg)
            msg = json.dumps(msg)
            
            # Call notification_despatcher
            notification_despatcher(None, msg)
            counter = counter + 1
            if counter % 500 == 0:
                pinfo('Kite simulator is on a short break')
                time.sleep(2)
            

    #for stock in  data['stock']:
    #    cache.set(stock, ohlc_data[stock].to_json(orient='columns'))
    
    pinfo('Kite_Simulator: Done: {}'.format(counter))

    time.sleep(1)
    notification_despatcher(None, 'done')
    
    simulator_lock.acquire()

    pdebug('Kite_Simulator: Trade Handler Done')

    cache.set('done'+cache_postfix,1)
    for key in data['stock']:
        pdebug1(key)
        try:
            trade_analysis(key)
        except:
            perror("Exception in trade analysis")
            pass
    
    pdebug('Kite_Simulator: Trade Analysis Done')


#def update_plot_cache(key, tmp_df):
#    cache_buff = pd.read_json(cache.get(key))
#    cache_buff = cache_buff.append(tmp_df)
#    cache.set(key, cache_buff.to_json(orient='columns'))


def tick_handler(manager, msg):
    pinfo('tick_handler: {}'.format(msg))

    # Step 0: Clean queue
    cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
    cache.xtrim('notificationQueue'+cache_postfix,maxlen=0, approximate=False)

    simulator_lock.acquire()
     
    counter = 0
    while(True):
        # Step 1: Blocking call to msgBufferQueue and notificationQueue
        if cache.xlen('msgBufferQueue'+cache_postfix) == 0:
            msg_q = cache.xread({'msgBufferQueue'+cache_postfix:'$','notificationQueue'+cache_postfix:'$'}, block=0, count=5000)
        msgs_q = cache.xread({'msgBufferQueue'+cache_postfix:'0','notificationQueue'+cache_postfix:'0'}, block=2000, count=5000)
        cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
        cache.xtrim('notificationQueue'+cache_postfix,maxlen=0, approximate=False)
        
        # Step 2: Process notifications: Start a worker thread for each notification
        #TODO
        
        # Step 3: Process tick: Start a worker thread for each msg       
        for msg in msgs_q[0][1]:
            pdebug1('tick_handler: {}'.format(msg[1]['msg']))
            counter = counter + 1
            try:
                data = json.loads(msg[1]['msg'])
            except:
                simulator_lock.release()
                perror("Un-supported message: {}: {} : {}".format(counter, msg, sys.exc_info()[0]))
                counter = 0
                break
            
            for key in data.keys():
                stock = key.split(':')[1]
                exchange = key.split(':')[0]

            hash_key = stock
            freq = cache.getValue(hash_key,'freq')
            state = cache.getValue(hash_key,'state')

            #pdebug('TH: {} =>{}'.format(hash_key, state))
            temp_df = msg_to_ohlc(data)
            if state == 'INIT': # State: Init: Load historical data from cache
                # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
                deltaT = getDeltaT(freq)

                toDate = (temp_df.index[0] - timedelta(days=1)).strftime('%Y-%m-%d')
                fromDate = (temp_df.index[0] - deltaT).strftime('%Y-%m-%d')
                ohlc_data = getData(stock, fromDate, toDate, exchange, freq, False, stock)

                ohlc_data = ohlc_data.tail(no_of_hist_candles)
                cache.setOHLC(hash_key,ohlc_data)

                #cache.setValue(hash_key,'state','SCANNING')
            
            # Add to OHLCBuffer in hash
            cache.pushOHLC(hash_key,temp_df)

            # Start job to process Tick
            manager.add(stock, trade_job, False, hash_key)
            #pdebug(msg[0])

def trade_job(hash_key):
    pdebug1('trade_job: {}'.format(hash_key))
    
    stock = cache.getValue(hash_key,'stock')

    trade_lock = trade_lock_store[stock]
    trade_lock.acquire()

    # Step 1: Get state for the stock from the redis
    state = cache.getValue(hash_key,'state')
    if not state:
        return
    freq = cache.getValue(hash_key,'freq')
    algo_name = cache.getValue(hash_key,'algo')
    tp = float(cache.getValue(hash_key,'tp'))
    sl = float(cache.getValue(hash_key,'sl'))
    algo = cache.hget('algos',algo_name)

    #pdebug("{}: {}: {}".format(hash_key, stock, state ))
    ohlc_df = cache.getOHLC(hash_key)

    ltp = float(ohlc_df.iloc[-1:]['close'][0])
    low = float(ohlc_df['low'].tail(30).min())
    high =  float(ohlc_df['high'].tail(30).max())

    cache.setValue(hash_key, 'ltp', ltp)
    cache.setValue(hash_key, 'low', low)
    cache.setValue(hash_key, 'high', high)

    last_processed = ohlc_df.index[-1].strftime('%Y-%m-%d %H:%M')

    time_val = ohlc_df.index[-1].minute+ohlc_df.index[-1].hour*60
    cutoff_time = (15*60+15)
    pdebug1("{}=>{}".format(last_processed,cache.getValue(hash_key,'last_processed')))
    
    if last_processed == cache.getValue(hash_key,'last_processed'):   
        trade_lock.release()
        return
    else:
        cache.setValue(hash_key,'last_processed',last_processed)
    
    # Step 2: Switch to appropriate state machine based on current state
    if state == 'INIT': # State: Init
        # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
            # Done inside thread handler
        
        # 2: Set state to Scanning
        cache.setValue(hash_key,'state','SCANNING')
        pass
    
    elif state == 'SCANNING':  # State: Scanning
        # 1: Run trading algorithm for entering trade
        tradeDecision = myalgo(cache, hash_key, ohlc_df, algo, state)
        if time_val >= (cutoff_time-15):
            pass
        # 2: If Algo returns Buy: set State to 'Pending Order: Long'
        elif tradeDecision=="BUY":
            placeorder("B: EN: ", ohlc_df, stock, last_processed)
            #logtrade("BUY : {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
            cache.setValue(hash_key,'state','LONG') #TODO
        
        # 3: If Algo returns Sell: set State to 'Pending Order: Short'
        elif tradeDecision=="SELL":
            placeorder("S: EN: ", ohlc_df, stock, last_processed)
            #logtrade("SELL: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
            cache.setValue(hash_key,'state','SHORT') #TODO
        
        # 4: Update TradeMetaData: Push order details to OrderQueue
    
    elif state == 'PO:LONG': # State: Pending Order: Long
    
        # 1: On Fill: set State to Long
        cache.setValue(hash_key,'state','LONG')
        pass
    
    
    elif state == 'PO:SHORT': # State: Pending Order: Short
    
        # 1: On Fill: set State to Short
        cache.setValue(hash_key,'state','SHORT')
        pass
    
    
    elif state == 'LONG': # State: Long
        # 1: If notification for AutoSquare Off: set state to init
        if time_val >= cutoff_time:
            placeorder("S: EX: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
        elif ltp < sl:
            placeorder("S: SL: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
        elif ltp > tp:
            placeorder("S: TP: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
            pass
        else:
            # 2: Else run trading algorithm for square off
            tradeDecision = myalgo(cache, hash_key, ohlc_df, algo, state)
            if tradeDecision == "SELL":
                placeorder("S: EX: ", ohlc_df, stock, last_processed)
                #logtrade("SO-S: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))

                # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'   
                cache.setValue(hash_key,'state','SQUAREOFF')
    
    
    elif state == 'SHORT': # State: Short
        # 1: If notification for AutoSquare Off: set state to init
        if time_val >= cutoff_time:
            placeorder("B: EX: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
        elif ltp > sl:
            placeorder("B: SL: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
        elif ltp < tp:
            placeorder("B: TP: ", ohlc_df, stock, last_processed)
            cache.setValue(hash_key,'state','SQUAREOFF')
            pass
        else:
            # 2: Else run trading algorithm for square off
            tradeDecision = myalgo(cache, hash_key, ohlc_df, algo, state)
            if tradeDecision == "BUY":
                placeorder("B: EX: ", ohlc_df, stock, last_processed)
                #logtrade("SO-B: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
            
                # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'
        
                cache.setValue(hash_key,'state','SQUAREOFF')
        
    elif state == 'SQUAREOFF':  # State: Awaiting Square Off
        # 1: On Fill notification: set state to SCANNING
        cache.setValue(hash_key,'state','SCANNING')
        pass
   
    trade_lock.release()


def placeorder(prefix, df, stock, last_processed):
    logtrade(prefix+" : {} : {} -> {}".format(last_processed, stock, ohlc_get(df,'close')))

    tp_pt = float(cache.getValue(stock,'TP %'))
    sl_pt = float(cache.getValue(stock,'SL %'))
    qty = float(cache.getValue(stock,'qty'))

    ltp = df.iloc[-1:]['close']
    amount = ltp[0] *qty
    sl = 0
    tp = 0
    price = float(cache.getValue(stock,'price'))
    profit = 0
    pl_pt = 0
    totalprofit =  float(cache.getValue(stock,'Total P&L'))

    pdebug5("Place Order: {},{},{},{}".format(ltp[0], price, profit, totalprofit))
    tmp_df = pd.DataFrame()
    if prefix == "B: EN: ":
        tmp_df['buy'] = ltp
        sl = ltp[0] * ( 1 - sl_pt / 100 )
        tp =  ltp[0] * ( 1 + tp_pt / 100 )
        price = ltp[0] 
    elif prefix == "B: EX: " or prefix == "B: SL: " or prefix == "B: TP: ":
        tmp_df['buy'] = ltp
        profit = (price - ltp[0]) * qty
        pl_pt = profit/price * 100
        price = 0
    elif prefix == "S: EN: ":
        tmp_df['sell'] = ltp
        sl = ltp[0] * ( 1 + sl_pt / 100 )
        tp =  ltp[0] * ( 1 - tp_pt / 100 )
        price = ltp[0] 
    elif prefix == "S: EX: " or prefix == "S: SL: " or prefix == "S: TP: ":
        tmp_df['sell'] = ltp
        profit = (ltp[0] - price) * qty
        pl_pt = profit/price * 100
        price = 0

    totalprofit = totalprofit + profit

    total_pt = totalprofit / amount * 100
    

    cache.setValue(stock,'amount', amount)
    cache.setValue(stock,'sl', sl)
    cache.setValue(stock,'tp', tp)
    cache.setValue(stock,'price', price)
    cache.setValue(stock,'P&L', profit)
    cache.setValue(stock,'P&L %', pl_pt)
    cache.setValue(stock,'Total P&L', totalprofit)
    cache.setValue(stock,'Total P&L %', total_pt)

    tmp_df['mode'] = prefix
    cache.pushTrade(stock, tmp_df)


def order_handler(manager, msg):
    pdebug('order_handler: {}'.format(msg))
    
    # Step 1: Block for new order request: OrderQueue
    
    # Step 2: Create order msg for Kite: fill metadata
    
    # Step 3: If papertrade: create a log entry
    
    # Step 4: If not a papertrade: despatch order

   

# This function implements logic to resume trading post abrupt termination
def auto_resume_trade(msg):
    pdebug('resume_trade: {}'.format(msg))
    
    # 1: Get list of open orders from Kite
    
    # 2: Loop through all the open trades in the system
    
    # 3: If an open trade in the system is not present in Kite, reset status to init
    
    # 4: For open trades fill OHLC buffer with historical data

backtest_manager = ""
order_manager = ""
live_trade_manager = ""
def freedom_init(manager, msg):
    global backtest_manager, order_manager, live_trade_manager
    pdebug('freedom_init: {}'.format(msg))
    job_alive = lambda x: pinfo("backtest_manager: {}".format(x.job.is_alive()))
    # 0: Initialize settings

    if msg == 'backtest:start':
        cache.set('done'+cache_type,1)
        backtest_manager = threadManager(cache_type, ["kite_simulator","tick_handler"], [kite_simulator, tick_handler])
    elif msg == 'backtest:stop':
        job_alive(backtest_manager)
        backtest_manager.job.terminate()
        time.sleep(3)
        job_alive(backtest_manager)
    elif msg == 'backtest:status':
        job_alive(backtest_manager)
    elif msg == 'backtest:reset':
        backtest_manager.job.terminate()
        time.sleep(2)
        job_alive(backtest_manager)
        backtest_manager = threadManager(cache_type, ["kite_simulator","tick_handler"], [kite_simulator, tick_handler])
        time.sleep(3)
        job_alive(backtest_manager)
        cache.set('done'+cache_type,1)
    elif msg == 'live:start':
        live_trade_manager = threadManager("live", ["order_handler"], [order_handler])
    else:
        cache.set('done'+cache_type,1)
        backtest_manager = threadManager(cache_type, ["kite_simulator","tick_handler"], [kite_simulator, tick_handler])

        # 2: Start kite websocket connections
        # Initialise
        #kws = KiteTicker(KiteAPIKey, kite.access_token)

        # Assign the callbacks.
        #kws.on_ticks = on_ticks
        #kws.on_connect = on_connect
        #kws.on_order_update = on_order_update
    
#TODO: Watchdog implementation to resume processes
#TODO: Implementation of user initiated aborts and restart
