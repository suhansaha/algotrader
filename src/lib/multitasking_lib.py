import threading
from threading import Semaphore
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
        self.stop = False
        
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
            #pinfo(msg)
            if msg == 'stop':
                pinfo('Stopping : {}'.format(self.name))
                self.manager.abort = True
                #pubsub.unsubscribe()
                #pinfo(self.worker.is_alive())
                #self.worker.terminate()
                #break
            else:
                self.workerThread = myThread(self.manager, self.name+'_worker', self.callback, False, msg)
                self.workerThread.start()
                self.manager.abort = False
                #self.worker = multiprocessing.Process(target=self.callback, args=(self.manager, msg,)) 
                #self.worker.start()
        self.workerThread.join()
    
    #The thread function for one of tasks
    def thread_worker(self, callback):
        callback(self.manager, self.msg)

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
        #cache.flushall()
        # Create new threads
        for tName in self.threadList:
            self.add(tName, self.threadCallback[self.threadID-1])

        #self.add('watchdog', thread_watchdog)

        # Wait for all threads to complete
        for t in self.threads:
            t.join()
        pinfo("Exiting Main Thread")
        
    def add(self, name, callback, pubsub=True, cmd=""):
        # Create an instance of mythrade class and start the thread
        #pinfo('In thread manager add: {}'.format(name))
        thread = myThread(self, name, callback, pubsub, cmd)

        #pinfo(cmd)
        thread.start()
        self.threads.append(thread)
        self.threadID += 1

def thread_watchdog():
    pinfo('in thread watchdog')
    pinfo(self)



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
    #svolume = ohlc_list['volume']

    temp_df = pd.DataFrame(ohlc_list, columns=['open','high','low','close'], 
                           index=[datetime.strptime(ohlc_list['date'],'%Y-%m-%d %H:%M:%S')])
    
    return temp_df


# This function is called by Kite or Kite_Simulation
def notification_despatcher(ws, msg, id='*', Tick=True ):
    pdebug1('notification_despatcher:{}=>{}'.format(id,msg))
    # Step 1: Extract msg type: Tick/Callbacks
    
    # Step 2.1: If Tick
    if Tick == True:
        # Push msg to msgBufferQueue
        #msg_id = cache.xadd('msgBufferQueue'+cache_postfix, msg, id=id)
        msg_id = cache.xadd('msgBufferQueue'+cache_postfix, {'data':json.dumps(msg)}, id=id)
    
    # Step 2.2: else
    else:
        # Push msg to notificationQueue
        cache.xadd('notificationQueue'+cache_postfix, msg, id = id)

###################### BackTest ######################
trade_lock_store = {} 
simulator_lock = Lock()
def trade_init(stock_key, data):        
    # Initialize state
    pdebug("Trade_init: {}".format(stock_key))

    cache.add(stock_key, reset=True)

    algo = data['algo']
    sl = data['sl']
    target = data['target']
    qty = data['qty']
    freq = data['freq']
    algo = data['algo']

    if freq == '1D':
        hdf_freq='day'
    else:
        hdf_freq='minute'

    cache.setValue(stock_key, 'algo', algo)
    cache.setValue(stock_key, 'freq', freq)
    cache.setValue(stock_key, 'qty', qty)
    cache.setValue(stock_key, 'SL %', sl)
    cache.setValue(stock_key, 'TP %', target)
    cache.setValue(stock_key, 'P&L', 0)
    cache.setValue(stock_key, 'Total P&L', 0)
    cache.setValue(stock_key, 'price', 0)
    cache.setValue(stock_key, 'hdf_freq', hdf_freq)

    #cache.set(stock_key, pd.DataFrame().to_json(orient='columns')) #Used for plotting
    
    #trade_lock_store[stock_key] = Lock()


max_simu_msg = 100
ohlc_handler_sem = Semaphore(max_simu_msg)
def full_simulation(data, ohlc_data, cache, exchange, manager):
    cache.publish('ohlc_tick_handler'+cache_postfix,'start')

    stock = data['stock'][-1]
    no = ohlc_data[stock].shape[0]
    counter = 0
    stream_id = lambda x,y:str(int(x.timestamp()+y)*1000)+'-0'
    cache.delete('msgBufferQueue'+cache_postfix)
    cache.delete('notificationQueue'+cache_postfix)
    for i in np.linspace(0,no-1,no): # Push data
        if manager.abort == True:
            pinfo('Abort Request: Full Simulation')
            return

        i = int(i)
        msg_dict_open = {}
        msg_dict_high = {}
        msg_dict_low = {}
        msg_dict_close = {}
        for stock in data['stock']:
            row = ohlc_data[stock].iloc[i]
            index = ohlc_data[stock].index[i]
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {exchange+":"+stock:json.dumps({"last_price":row['open']})}
            msg_dict_open.update(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {exchange+":"+stock:json.dumps({"last_price":row['high']})}
            msg_dict_high.update(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {exchange+":"+stock:json.dumps({"last_price":row['low']})}
            msg_dict_low.update(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {exchange+":"+stock:json.dumps({"last_price":row['close']})}
            msg_dict_close.update(msg)
            
        ohlc_handler_sem.acquire()
        notification_despatcher(None, msg_dict_open, id=stream_id(index,5))
        ohlc_handler_sem.acquire()
        notification_despatcher(None, msg_dict_high, id=stream_id(index,10))
        ohlc_handler_sem.acquire()
        notification_despatcher(None, msg_dict_low, id=stream_id(index,20))
        ohlc_handler_sem.acquire()
        notification_despatcher(None, msg_dict_close, id=stream_id(index,30))

        counter = counter + 4
            
    pinfo('Kite_Simulator: Done: {}'.format(counter))

    notification_despatcher(None, 'done')


def quick_backtest(data, ohlc_data, cache, exchange):
    pinfo('quick backtest')

    def BUY(CLOSE, x, trade_df1):
        #global trade_df1
        tmp_df = pd.DataFrame()
        tmp_df["buy"] = CLOSE[x]
        trade_df1 = trade_df1.append(tmp_df)
        return trade_df1
    
    def SELL(CLOSE, x, trade_df1):
        #global trade_df1
        tmp_df = pd.DataFrame()
        tmp_df["sell"] = CLOSE[x]
        trade_df1 = trade_df1.append(tmp_df)
        return trade_df1

    for stock_key in data['stock']:
        temp_df = ohlc_data[stock_key]
        
        hdf_freq = cache.getValue(stock_key, 'hdf_freq')
        deltaT = getDeltaT(hdf_freq)
        
        toDate = temp_df.index[-1].strftime('%Y-%m-%d')
        fromDate = (temp_df.index[0] - deltaT).strftime('%Y-%m-%d')

        #pinfo(toDate)
        #pinfo(fromDate)
        pre_data = getData(stock_key, fromDate, toDate, exchange, hdf_freq, False, stock_key)

        cache.setOHLC(stock_key, pre_data)

        trade_df1 = pd.DataFrame()

        buy, sell = myalgo(cache, stock_key, pre_data, algo='', state='SCANNING', quick=True)

        #pinfo(pre_data['close'])
        trade_df1 = SELL(pre_data['close'], sell, trade_df1)
        trade_df1 = BUY(pre_data['close'], buy, trade_df1)

        #pinfo(trade_df1.sort_index().tail(10))
        cache.setCache(stock_key+cache_type+'Trade',trade_df1)
    
    cache.set('done'+cache_postfix,1)


def kite_simulator(manager, msg):
    pdebug('kite_simulator: {}'.format(msg))

    try:
        data = json.loads(msg)
    except:
        perror('kite_simulator: Invalid msg: {}'.format(msg))
        return
    
    toDate = data['toDate']
    fromDate = data['fromDate']
    startDate = datetime.strptime(fromDate,'%Y-%m-%d') 
    exchange = 'NSE'
    
    ohlc_data = {}
    for stock_key in data['stock']: #Initialize
        # Load data from the Cache
        #cache.setValue(stock_key, 'hdf_freq', hdf_freq)        
        trade_init(stock_key, data)

        hdf_freq = cache.getValue(stock_key, 'hdf_freq')
        df = getData(stock_key, startDate, toDate, exchange, hdf_freq, False, stock_key)
        ohlc_data[stock_key] = df

    if data['mode'] == 'quick':
        pinfo('Running Quick Backtest')
        quick_backtest(data, ohlc_data, cache, exchange)
    else:
        pinfo('Running Full Backtest')
        full_simulation(data, ohlc_data, cache, exchange, manager)
    



trade_job_sem = Semaphore(10)
def ohlc_tick_handler(manager, msg):
    pdebug('ohlc_tick_handler: {}'.format(msg))

    if msg != 'start':
        return

    # Step 0: Clean queue
    cache.delete('msgBufferQueue'+cache_postfix)
    cache.delete('notificationQueue'+cache_postfix)
    last_id_msg = '0'
     
    counter = 0
    while(True):
        if manager.abort == True:
            pinfo("Abort Request: ohlc_tick_handler")
            #cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
            cache.set('done'+cache_postfix,1)
            counter = 0
            ohlc_handler_sem.release()
            break
            #cache.xtrim('notificationQueue'+cache_postfix,maxlen=0, approximate=False)

        # Step 1: Blocking call to msgBufferQueue and notificationQueue
        if cache.xlen('msgBufferQueue'+cache_postfix) == 0:
            cache.xread({'msgBufferQueue'+cache_postfix:'$','notificationQueue'+cache_postfix:'$'}, block=0, count=5000)
        msgs_q = cache.xread({'msgBufferQueue'+cache_postfix:last_id_msg,'notificationQueue'+cache_postfix:'0'}, block=2000, count=5000)
        #cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
        cache.xtrim('notificationQueue'+cache_postfix,maxlen=0, approximate=False)
        
        try:
            last_id_msg = msgs_q[0][1][-1][0]
        except:
            break
            pass
        #pinfo(last_id_msg)
        # Step 2: Process notifications: Start a worker thread for each notification
        #TODO
        
        # Step 3: Process tick: Start a worker thread for each msg       
        for msg in msgs_q[0][1]:
            #pdebug('ohlc_tick_handler: {}'.format(msg[1]))
            counter = counter + 1
            val = json.loads(msg[1]['data'])
            if val == 'done':
                perror("Processing done: {}: {}".format(counter, msg))
                cache.set('done'+cache_postfix,1)
                counter = 0
                ohlc_handler_sem.release()
                break
            
            
            date_val = datetime.fromtimestamp(int(msg[0].split('-')[0])/1000).strftime('%Y-%m-%d %H:%M:%S')

            #stock = []
            #ltp = []
            #date = []
            for key, data in val.items():
                stock_id = key.split(':')[1]
                exchange = key.split(':')[0]
                ltp = json.loads(data)['last_price']
                temp_df = pd.DataFrame(data={'date':[date_val],'ltp':[ltp]})
                temp_df = temp_df.set_index('date')
                temp_df.index = pd.to_datetime(temp_df.index)


                hash_key = stock_id
                hdf_freq = cache.getValue(hash_key,'hdf_freq')
                state = cache.getValue(hash_key,'state')

                #pdebug('TH: {} =>{}'.format(hash_key, state))
                #temp_df = msg_to_ohlc(data)
                if state == 'INIT': # State: Init: Load historical data from cache
                    # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
                    deltaT = getDeltaT(hdf_freq)

                    toDate = (temp_df.index[0] - timedelta(days=1)).strftime('%Y-%m-%d')
                    fromDate = (temp_df.index[0] - deltaT).strftime('%Y-%m-%d')
                    ohlc_data = getData(stock_id, fromDate, toDate, exchange, hdf_freq, False, stock_id)

                    ohlc_data = ohlc_data.tail(no_of_hist_candles)
                    cache.setOHLC(hash_key,ohlc_data)

                    cache.setValue(hash_key,'state','SCANNING')

                if not stock_id in trade_lock_store:
                    trade_lock_store[stock_id] = Lock()

                try:
                    cache.pushTICK(stock_id, temp_df)
                except:
                    pass
                
                # Start job to process Tick
                if manager.abort == False:
                    trade_job_sem.acquire()
                    manager.add(stock_id, trade_job, False, hash_key)

            ohlc_handler_sem.release()

def trade_job(manager, hash_key):
    if manager.abort == True:
        return

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
    algo = cache.hget('algos',algo_name)
    tp = float(cache.getValue(hash_key,'tp'))
    sl = float(cache.getValue(hash_key,'sl'))

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
        trade_job_sem.release()
        return
    else:
        cache.setValue(hash_key,'last_processed',last_processed)
    
    # Step 2: Switch to appropriate state machine based on current state
    if state == 'INIT': # State: Init
        # 2: Set state to Scanning
        cache.setValue(hash_key,'state','SCANNING')
    
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
    
    
    elif state == 'PO:SHORT': # State: Pending Order: Short
    
        # 1: On Fill: set State to Short
        cache.setValue(hash_key,'state','SHORT')
    
    
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
   
    trade_lock.release()
    trade_job_sem.release()


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


def tick_resampler(manager, msg):
    pdebug('tick_resampler: {}'.format(msg))

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

    cache.set('done'+cache_type,1)
    backtest_manager = threadManager(cache_type, ["kite_simulator","ohlc_tick_handler"], [kite_simulator, ohlc_tick_handler])

    #live_manager = threadManager(cache_id, ["ohlc_tick_handler","tick_resampler","order_handler"], [ohlc_tick_handler, tick_resampler, order_handler])

    # 2: Start kite websocket connections
    # Initialise
    #kws = KiteTicker(KiteAPIKey, kite.access_token)

    # Assign the callbacks.
    #kws.on_ticks = on_ticks
    #kws.on_connect = on_connect
    #kws.on_order_update = on_order_update
    
#TODO: Watchdog implementation to resume processes
#TODO: Implementation of user initiated aborts and restart
