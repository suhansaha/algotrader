import threading
from threading import Semaphore
import time
import pandas as pd
import math
from queue import Queue
from redis import Redis
import multiprocessing
import numpy as np
import sys
import json
import ast
from datetime import datetime, timedelta
import time
import sys
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker

from lib.logging_lib import *
from lib.kite_wrapper_lib import *
from lib.algo_lib import *
from lib.data_model_lib import *
timestamp_to_id = lambda x:str(int(float(x)*1000))+'-'+str(0)

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
            #pinfo(msg)
            if msg == 'stop':
                pinfo('Stopping : {}'.format(self.name))
                self.manager.abort = True
                #pubsub.unsubscribe()
                #pinfo(self.worker.is_alive())
                #self.worker.terminate()
                #break
            elif msg == 'pause':
                self.manager.pause = True
                pinfo('Paused : {}: {}'.format(self.name, self.manager.pause))
            elif msg == 'resume':
                self.manager.pause = False
                pinfo('Resume : {}: {}'.format(self.name, self.manager.pause))
            else:
                self.manager.abort = False
                self.workerThread = myThread(self.manager, self.name+'_worker', self.callback, False, msg)
                self.workerThread.start()
                #self.worker = multiprocessing.Process(target=self.callback, args=(self.manager, msg,)) 
                #self.worker.start()
        self.workerThread.join()
    
    #The thread function for one of tasks
    def thread_worker(self, callback):
        callback(self.manager, self.msg)

jobs = []
cache_postfix = ""
cache = ""
kws = None
kite_api_key = 'b2w0sfnr1zr92nxm'
kite = KiteConnect(api_key=kite_api_key)

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
        self.pause = False
        self.abort = False
        #cache.flushall()
        # Create new threads
        for tName in self.threadList:
            self.add(tName, self.threadCallback[self.threadID-1])

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


# This function is called by Kite or Kite_Simulation
def notification_despatcher(ws, msg, id='*', Tick=True ):
    pdebug7('notification_despatcher:{}=>{}'.format(id,msg))
    # Step 1: Extract msg type: Tick/Callbacks
    
    # Step 2.1: If Tick
    if Tick == True:
        # Push msg to msgBufferQueue
        #msg_id = cache.xadd('msgBufferQueue'+cache_postfix, msg, id=id)
        msg_id = cache.xadd('msgBufferQueue'+cache_postfix, {'data':json.dumps(msg)}, id=id, maxlen=5000)
        #pinfo(msg)
    
    # Step 2.2: else
    else:
        # Push msg to notificationQueue
        cache.xadd('notificationQueue'+cache_postfix+'new', {'data':json.dumps(msg)}, id = id)


#####################################################################################################################
#### BackTest: KiteSimulator, Full Back Test, Quick Back Test                                                     ###
#####################################################################################################################
trade_lock_store = {} 
simulator_lock = Lock()
def trade_init(stock_key, data):        
    # Initialize state
    pdebug("Trade_init: {}".format(stock_key))

    algo = data['algo']
    sl = data['sl']
    target = data['target']
    qty = data['qty']
    freq = data['freq']
    algo = data['algo']
    mode = data['mode']
    job_id = data['job_id']

    user_id = job_id.split('-')[1]
    hash_key = stock_key+user_id
    cache.add(hash_key, reset=True)

    if freq == '1D':
        hdf_freq='day'
    else:
        hdf_freq='minute'

    cache.setValue(hash_key, 'stock', stock_key)
    cache.setValue(hash_key, 'algo', algo)
    cache.setValue(hash_key, 'freq', freq)
    cache.setValue(hash_key, 'qty', qty)
    cache.setValue(hash_key, 'SL %', sl)
    cache.setValue(hash_key, 'TP %', target)
    cache.setValue(hash_key, 'P&L', 0)
    cache.setValue(hash_key, 'Total P&L', 0)
    cache.setValue(hash_key, 'price', 0)
    cache.setValue(hash_key, 'hdf_freq', hdf_freq)
    cache.setValue(hash_key, 'mode', mode)
    cache.setValue(hash_key, 'last_processed', 0)
    cache.setValue(hash_key, 'job_id', job_id)

    #cache.set(stock_key, pd.DataFrame().to_json(orient='columns')) #Used for plotting
    
    #trade_lock_store[stock_key] = Lock()


max_simu_msg = 100
ohlc_handler_sem = Semaphore(max_simu_msg)
def slow_full_simulation(data, ohlc_data, cache, exchange, manager):
    cache.publish('ohlc_tick_handler'+cache_postfix,'start')

    stock = data['stock'][-1]
    no = ohlc_data[stock].shape[0]
    counter = 0
    stream_id = lambda x,y:str(int(x.tz_localize(tz='Asia/Calcutta').timestamp()+y)*1000)+'-0'
    cache.xtrim('msgBufferQueue'+cache_postfix, 0, True)
    cache.xtrim('notificationQueue'+cache_postfix, 0, True)
    cache.delete('msgBufferQueue'+cache_postfix)
    cache.delete('notificationQueue'+cache_postfix)
    cache.set('last_id_msg'+cache_postfix, 0)
    #pinfo(data['stock'])
    for i in np.linspace(0,no-1,no): # Push data
        if manager.abort == True:
            pinfo('Abort Request: Full Simulation')
            return

        i = int(i)
        msg_dict_open = []
        msg_dict_high = []
        msg_dict_low = []
        msg_dict_close = []
        for stock in data['stock']:
            #pinfo(stock)
            row = ohlc_data[stock].iloc[i]
            index = ohlc_data[stock].index[i]
            
            instrument_token = int(cache.hmget('eq_token',stock)[0])

            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {'instrument_token':instrument_token,"last_price":row['open']}
            msg_dict_open.append(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {'instrument_token':instrument_token,"last_price":row['high']}
            #msg = {exchange+":"+stock:json.dumps({"last_price":row['high']})}
            msg_dict_high.append(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {'instrument_token':instrument_token,"last_price":row['low']}
            #msg = {exchange+":"+stock:json.dumps({"last_price":row['low']})}
            msg_dict_low.append(msg)
            
            #stream_id = str(int(index.timestamp())*1000)+'-0'
            msg = {'instrument_token':instrument_token,"last_price":row['close']}
            #msg = {exchange+":"+stock:json.dumps({"last_price":row['close']})}
            msg_dict_close.append(msg)
        
        #pinfo(msg_dict_open)

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


def full_simulation(data, ohlc_data, cache, exchange, manager):
    #cache.publish('ohlc_tick_handler'+cache_postfix,'start')

    stock = data['stock'][-1]
    user_id = data['job_id'].split('-')[1]

    no = ohlc_data[stock].shape[0]
    counter = 0
    stream_id = lambda x,y:str(int(x.tz_localize(tz='Asia/Calcutta').timestamp()+y)*1000)+'-0'
    
    for i in np.linspace(0,no-1,no): # Push data
        if manager.abort == True:
            pinfo('Abort Request: Full Simulation')
            return

        i = int(i)
        msg_dict_open = []
        msg_dict_high = []
        msg_dict_low = []
        msg_dict_close = []
        for stock in data['stock']:
            #pinfo(stock)
            hash_key = stock+user_id
            row = ohlc_data[stock].iloc[i:i+1]
            index = ohlc_data[stock].index[i]
            cache.pushOHLC(hash_key, row)
            trade_lock_store[hash_key] = Lock()
            trade_job(manager, hash_key)
            cache.setValue(hash_key,'last_processed',str( index.tz_localize(tz='Asia/Calcutta').timestamp() ))
            
        counter = counter + 1
        #cache.set('last_id_msg'+cache_postfix, index.strftime('%d:%m:%y %H:%M'))
        

    cache.set('done'+user_id+cache_postfix,1) #Trigger to UI thread
    pinfo('Kite_Simulator: Done: {}'.format(counter))


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

    user_id = data['job_id'].split('-')[1]
    for stock_key in data['stock']:
        temp_df = ohlc_data[stock_key]
        
        hash_key = stock_key+user_id
        hdf_freq = cache.getValue(hash_key, 'hdf_freq')
        deltaT = getDeltaT(hdf_freq)
        
        toDate = temp_df.index[-1].strftime('%Y-%m-%d')
        fromDate = (temp_df.index[0] - deltaT).strftime('%Y-%m-%d')

        #pinfo(toDate)
        #pinfo(fromDate)
        pre_data = getData(stock_key, fromDate, toDate, exchange, hdf_freq, False, stock_key)

        cache.setOHLC(hash_key, pre_data)

        trade_df1 = pd.DataFrame()

        my_algo = cache.hget('algos',data['algo'])
        buy, sell = myalgo(cache, hash_key, pre_data, algo=my_algo, state='SCANNING', quick=True)

        #pinfo(pre_data['close'])
        trade_df1 = SELL(pre_data['close'], sell, trade_df1)
        trade_df1 = BUY(pre_data['close'], buy, trade_df1)

        #pinfo(trade_df1.sort_index().tail(10))
        cache.setCache(hash_key+cache_postfix+'Trade',trade_df1.sort_index())
    
    cache.set('done'+user_id+cache_postfix,1)


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

        user_id = data['job_id'].split('-')[1]
        hdf_freq = cache.getValue(stock_key+user_id, 'hdf_freq')
        df = getData(stock_key, startDate, toDate, exchange, hdf_freq, False, stock_key)
        ohlc_data[stock_key] = df

    if data['mode'] == 'quick':
        pinfo('Running Quick Backtest')
        quick_backtest(data, ohlc_data, cache, exchange)
    else:
        pinfo('Running Full Backtest')
        full_simulation(data, ohlc_data, cache, exchange, manager)
    
def order_notification_handler(manager, msg):
    pdebug('order_notification_handler({}) - INIT: {}'.format(cache_postfix, msg))
    last_msg_id = '0'

    while(True):
        if manager.abort == True:
            break
        msgs_q = cache.xread({'notificationQueuelivenew':last_msg_id}, block=2000, count=5000)
        #cache.xtrim('notificationQueuelivenew', maxlen=0, approximate=False)

        if len(msgs_q) == 0:
            continue
        #cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
        
        try:
            #last_id_msg = cache.get('last_id_msg')
            last_msg_id = msgs_q[0][1][-1][0]
        except:
            perror('Could not read data from msgBufferQueue: {}'.format(msgs_q))
            continue

        for msg in msgs_q[0][1]:
            #last_msg_id = msg[0]
            #print(msg[1]['data'])
            data = json.loads(msg[1]['data'])
            order_id = data['order_id']
            status = data['status']
            symbol = data['tradingsymbol']
            price = data['average_price']
            state = cache.getValue(symbol,'state')
            cache_order_id = cache.getValue(symbol,'order_id')
            #if cache_order_id != order_id:
            #    continue

            if status == 'COMPLETE':
                if state == 'PO:LONG':
                    cache.setValue(symbol,'state','LONG')
                elif state == 'PO:SHORT':
                    cache.setValue(symbol,'state','SHORT')
                elif state == 'SQUAREOFF:LONG' or state == 'SQUAREOFF:SHORT' :
                    cache.setValue(symbol,'state','SCANNING')

                cache.setValue(symbol, 'price', price)

            elif status == 'REJECTED' or  status == 'CANCELLED' :
                if state == 'PO:LONG' or state == 'PO:SHORT':
                    cache.setValue(symbol,'state','SCANNING')
                elif state == 'SQUAREOFF:LONG':
                    cache.setValue(symbol,'state','LONG')
                elif state == 'SQUAREOFF:SHORT':
                    cache.setValue(symbol,'state','SHORT')
            #elif status == 'OPEN':
            print("{}: {} - {} : {} => {}".format(symbol, order_id, status, state, cache.getValue(symbol,'state')))


trade_job_sem = Semaphore(10)
ohlc_tick_handler_lock = Lock()
def ohlc_tick_handler(manager, msg):
    with ohlc_tick_handler_lock:

        pdebug('ohlc_tick_handler({}) - INIT: {}'.format(cache_postfix, msg))
        last_id_msg = '0'
        #last_id_msg = cache.get('last_id_msg'+cache_postfix)
        
        counter = 0
        while(True):
            if manager.abort == True:
                pinfo("Abort Request: ohlc_tick_handler")
                #cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
                cache.set('done'+cache_postfix,1)
                counter = 0
                ohlc_handler_sem.release()
                break

            #pinfo(cache_postfix)
            # Step 1: Blocking call to msgBufferQueue and notificationQueue
            #pinfo(cache.xlen('msgBufferQueue'+cache_postfix))
            #if cache.xlen('msgBufferQueue'+cache_postfix) == 0:
            #    cache.xread({'msgBufferQueue'+cache_postfix:'$'}, block=0, count=5000)

            last_id_msg = cache.get('last_id_msg'+cache_postfix)
            #pinfo(cache.xlen('msgBufferQueue'+cache_postfix))
            
            msgs_q = cache.xread({'msgBufferQueue'+cache_postfix:last_id_msg}, block=2000, count=5000)

            if len(msgs_q) == 0:
                continue
            #cache.xtrim('msgBufferQueue'+cache_postfix,maxlen=0, approximate=False)
            
            try:
                #last_id_msg = cache.get('last_id_msg')
                last_id_msg = msgs_q[0][1][-1][0]
            except:
                perror('Could not read data from msgBufferQueue: {}'.format(msgs_q))
                continue
            #pinfo(last_id_msg)
            
            # Step 3: Process tick: Start a worker thread for each msg       
            for msg in msgs_q[0][1]:
                pdebug7('ohlc_tick_handler({}): {}'.format(cache_postfix ,msg))
                counter = counter + 1
                val = json.loads(msg[1]['data'])
                if val == 'done': # Backtest completed, exit gracefully
                    pinfo("Processing done({}): {}: {}".format(cache_postfix, counter, msg))
                    cache.set('done'+cache_postfix,1) #Trigger to UI thread
                    counter = 0
                    cache.set('last_id_msg'+cache_postfix, msg[0])
                    ohlc_handler_sem.release()

                    #cache.set('last_id_msg', msg[0])
                    break
                
                
                date_val = datetime.fromtimestamp(int(msg[0].split('-')[0])/1000).strftime('%Y-%m-%d %H:%M:%S')

                for data in val:
                    #{'data': '{"tradable": true, "mode": "quote", "instrument_token": 969473, "last_price": 185.0, "last_quantity": 6, "average_price": 187.11, "volume": 4319803, "buy_quantity": 469701, "sell_quantity": 539438, "ohlc": {"open": 185.0, "high": 189.95, "low": 184.1, "close": 184.0}, "change": 0.5434782608695652}'}
                    instrument_token = int(data['instrument_token'])
                    stock_id = cache.hmget('eq_token',instrument_token)[0]
                    hash_key = stock_id

                    if stock_id not in cache.getKeys():
                        perror('Cache not created for: {}'.format(stock_id))
                        continue

                    ltp = data['last_price'] # Get LTP from the latest msg
                    temp_df = pd.DataFrame(data={'date':[date_val],'ltp':[ltp]})
                    temp_df = temp_df.set_index('date')
                    temp_df.index = pd.to_datetime(temp_df.index)
                    
                    hdf_freq = cache.getValue(hash_key,'hdf_freq') # Needed to pull data
                    state = cache.getValue(hash_key,'state') # Initialize OHLC buffer

                    cache.setValue(hash_key, 'ltp', ltp)

                    #pdebug('TH: {} =>{}'.format(hash_key, state))
                    if state == 'INIT': # State: Init: Load historical data from cache
                        # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
                        deltaT = getDeltaT(hdf_freq)

                        toDate = (temp_df.index[0] - timedelta(days=1)).strftime('%Y-%m-%d')
                        fromDate = (temp_df.index[0] - deltaT).strftime('%Y-%m-%d')

                        try:
                            exchange = 'NSE'
                            ohlc_data = getData(stock_id, fromDate, toDate, exchange, hdf_freq, False, stock_id)

                            ohlc_data = ohlc_data.tail(no_of_hist_candles)
                            #cache.setOHLC(hash_key,ohlc_data) #TODO
                        except:
                            pwarning('Historical data is not found {} {} {} {} {}'.format(stock_id, fromDate, toDate, exchange, hdf_freq))

                        cache.setValue(hash_key,'state','SCANNING')

                    if not stock_id in trade_lock_store:
                        trade_lock_store[stock_id] = Lock()

                    try:
                        cache.pushTICK(stock_id, temp_df)
                    except:
                        pwarning('Can not push tick data: {}:{}'.format(stock_id, temp_df))

                    cache.set('last_id_msg'+cache_postfix, msg[0])
                    ########## Should I start Trade Job? ###########################
                    
                    mode = cache.getValue(stock_id,'mode') #don't start if mode is paused
                    # Start job to process Tick
                    if manager.abort == False and manager.pause == False and mode != 'PAUSE':
                        #last_processed = temp_df.index[-1].strftime('%Y-%m-%d %H:%M')
                        last_processed = float(cache.getValue(hash_key,'last_processed'))
                        curr_processed = int(msg[0].split('-')[0])/1000
                        next_processed = float(last_processed + 60)
    
                        #pdebug("{}, {}=>{}=>{}".format(temp_df.index[-1], last_processed, curr_processed, next_processed))
                        
                        if curr_processed >= next_processed:  
                            #pinfo(last_processed)
                            cache.setValue(hash_key,'last_processed',curr_processed)

                            pdebug7('start trade job: {}=>{}'.format(stock_id, curr_processed))
                            trade_job_sem.acquire()
                            manager.add(stock_id, trade_job, False, hash_key)
                    else:
                        pdebug1('Algotrade Paused for {}:[abort:{}, pause:{}, mode:{}]'.format(stock_id, manager.abort, manager.pause, mode))
                    
                ohlc_handler_sem.release()

def trade_job(manager, hash_key):
    if manager.abort == True or manager.pause == True:
        return

    pdebug7('trade_job: {}'.format(hash_key))

    stock = cache.getValue(hash_key,'stock')

        
    if cache.getValue(hash_key).empty:
        perror('Exiting tradejob as there is no cache')
        return

    try:
        trade_lock = trade_lock_store[hash_key]
        trade_lock.acquire()
    except:
        perror('Exiting trade job as could not get lock {}'.format(stock))
        trade_job_sem.release()
        return
    try:
        # Step 1: Get state for the stock from the redis
        state = cache.getValue(hash_key,'state')
        if not state:
            trade_lock.release()
            trade_job_sem.release()
            return

        freq = cache.getValue(hash_key,'freq')
        algo_name = cache.getValue(hash_key,'algo')
        algo = cache.hget('algos',algo_name)
        tp = float(cache.getValue(hash_key,'tp'))
        sl = float(cache.getValue(hash_key,'sl'))

        pdebug1("{}: {}: {}".format(hash_key, stock, state ))
        ohlc_df = cache.getOHLC(hash_key)

        ltp = float(ohlc_df.iloc[-1:]['close'][0])
        low = float(ohlc_df['low'].tail(30).min())
        high =  float(ohlc_df['high'].tail(30).max())

        cache.setValue(hash_key, 'ltp', ltp)
        cache.setValue(hash_key, 'low', low)
        cache.setValue(hash_key, 'high', high)
        
        time_val = ohlc_df.index[-1].minute+ohlc_df.index[-1].hour*60
        cutoff_time = (15*60+5)
        last_processed = ohlc_df.index[-1].strftime('%Y-%m-%d %H:%M')

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
                cache.setValue(hash_key,'state','PO:LONG')
                placeorder("B: EN: ", ohlc_df, hash_key, last_processed)
            
            # 3: If Algo returns Sell: set State to 'Pending Order: Short'
            elif tradeDecision=="SELL":
                cache.setValue(hash_key,'state','PO:SHORT')
                placeorder("S: EN: ", ohlc_df, hash_key, last_processed)
            
            # 4: Update TradeMetaData: Push order details to OrderQueue
        
        elif state == 'PO:LONG': # State: Pending Order: Long
        
            # 1: On Fill: set State to Long
            #cache.setValue(hash_key,'state','LONG')
            pass
        
        
        elif state == 'PO:SHORT': # State: Pending Order: Short
        
            # 1: On Fill: set State to Short
            #cache.setValue(hash_key,'state','SHORT')
            pass
        
        
        elif state == 'LONG': # State: Long
            # 1: If notification for AutoSquare Off: set state to init
            if time_val >= cutoff_time:
                cache.setValue(hash_key,'state','SQUAREOFF:LONG')
                placeorder("S: EX: ", ohlc_df, hash_key, last_processed)
            elif ltp < sl:
                cache.setValue(hash_key,'state','SQUAREOFF:LONG')
                placeorder("S: SL: ", ohlc_df, hash_key, last_processed)
            elif ltp > tp:
                cache.setValue(hash_key,'state','SQUAREOFF:LONG')
                placeorder("S: TP: ", ohlc_df, hash_key, last_processed)
                pass
            else:
                # 2: Else run trading algorithm for square off
                tradeDecision = myalgo(cache, hash_key, ohlc_df, algo, state)
                if tradeDecision == "SELL":
                    cache.setValue(hash_key,'state','SQUAREOFF:LONG')
                    placeorder("S: EX: ", ohlc_df, hash_key, last_processed)

                    # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'   
        
        
        elif state == 'SHORT': # State: Short
            # 1: If notification for AutoSquare Off: set state to init
            if time_val >= cutoff_time:
                cache.setValue(hash_key,'state','SQUAREOFF:SHORT')
                placeorder("B: EX: ", ohlc_df, hash_key, last_processed)
            elif ltp > sl:
                cache.setValue(hash_key,'state','SQUAREOFF:SHORT')
                placeorder("B: SL: ", ohlc_df, hash_key, last_processed)
            elif ltp < tp:
                cache.setValue(hash_key,'state','SQUAREOFF:SHORT')
                placeorder("B: TP: ", ohlc_df, hash_key, last_processed)
            else:
                # 2: Else run trading algorithm for square off
                tradeDecision = myalgo(cache, hash_key, ohlc_df, algo, state)
                if tradeDecision == "BUY":
                    cache.setValue(hash_key,'state','SQUAREOFF:SHORT')
                    placeorder("B: EX: ", ohlc_df, hash_key, last_processed)
                
                    # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'
            
        elif state == 'SQUAREOFF:LONG':  # State: Awaiting Square Off
            # 1: On Fill notification: set state to SCANNING
            #cache.setValue(hash_key,'state','SCANNING')
            pass
        elif state == 'SQUAREOFF:SHORT':  # State: Awaiting Square Off
            # 1: On Fill notification: set state to SCANNING
            #cache.setValue(hash_key,'state','SCANNING')
            pass
    except:
        perror('Issue in algotrade')
    finally:
        trade_job_sem.release()
        trade_lock.release()

#####################################################################################################################
#### Order Handler: Provides api to buy, sell and cancle order using Kite                                         ###
#####################################################################################################################


def placeorder(prefix, df, hash_key, last_processed):

    stock = cache.getValue(hash_key,'stock')
    job_id =  cache.getValue(hash_key,'job_id')
    logtrade(prefix+" : {} : {} -> {}".format(last_processed, stock, ohlc_get(df,'close')))

    tp_pt = float(cache.getValue(hash_key,'TP %'))
    sl_pt = float(cache.getValue(hash_key,'SL %'))
    qty = float(cache.getValue(hash_key,'qty'))

    ltp = df.iloc[-1:]['close']
    amount = ltp[0] *qty
    sl = 0
    tp = 0
    price = float(cache.getValue(hash_key,'price'))
    profit = 0
    pl_pt = 0
    totalprofit =  float(cache.getValue(hash_key,'Total P&L'))

    pdebug("Place Order: {},{},{},{}".format(ltp[0], price, profit, totalprofit))
    tmp_df = pd.DataFrame()
    if prefix == "B: EN: ":
        tmp_df['buy'] = ltp
        sl = ltp[0] * ( 1 - sl_pt / 100 )
        tp =  ltp[0] * ( 1 + tp_pt / 100 )
        price = ltp[0] 
        cache.publish('order_handler'+cache_postfix,json.dumps({'cmd':'buy','symbol':hash_key,'price':ltp[0],'qty':qty}))
        
        update_trade_log(last_processed, stock, ltp[0], qty, "B", prefix, job_id)

    elif prefix == "B: EX: " or prefix == "B: SL: " or prefix == "B: TP: ":
        tmp_df['buy'] = ltp
        profit = (price - ltp[0]) * qty
        pl_pt = profit/price * 100
        cache.publish('order_handler'+cache_postfix,json.dumps({'cmd':'buy','symbol':hash_key,'price':ltp[0],'qty':qty}))
        update_trade_log(last_processed, stock, ltp[0], qty, "B", prefix, job_id)
        price = 0
    elif prefix == "S: EN: ":
        tmp_df['sell'] = ltp
        sl = ltp[0] * ( 1 + sl_pt / 100 )
        tp =  ltp[0] * ( 1 - tp_pt / 100 )
        price = ltp[0] 
        cache.publish('order_handler'+cache_postfix,json.dumps({'cmd':'sell','symbol':hash_key,'price':ltp[0],'qty':qty}))
        update_trade_log(last_processed, stock, ltp[0], qty, "S", prefix, job_id)
    elif prefix == "S: EX: " or prefix == "S: SL: " or prefix == "S: TP: ":
        tmp_df['sell'] = ltp
        profit = (ltp[0] - price) * qty
        pl_pt = profit/price * 100
        cache.publish('order_handler'+cache_postfix,json.dumps({'cmd':'sell','symbol':hash_key,'price':ltp[0],'qty':qty}))
        update_trade_log(last_processed, stock, ltp[0], qty, "S", prefix, job_id)
        price = 0

    totalprofit = totalprofit + profit

    total_pt = totalprofit / amount * 100
    

    cache.setValue(hash_key,'amount', amount)
    cache.setValue(hash_key,'sl', sl)
    cache.setValue(hash_key,'tp', tp)
    cache.setValue(hash_key,'price', price)
    cache.setValue(hash_key,'P&L', profit)
    cache.setValue(hash_key,'P&L %', pl_pt)
    cache.setValue(hash_key,'Total P&L', totalprofit)
    cache.setValue(hash_key,'Total P&L %', total_pt)

    tmp_df['mode'] = prefix
    #cache.pushTrade(hash_key, tmp_df) #TODO




def order_handler(manager, msg):
    global kws, kite, kite_api_key
    pdebug('order_handler({}): {}'.format(cache_postfix, msg))

    KiteAPIKey = cache.get('KiteAPIKey')
    kite = KiteConnect(api_key=KiteAPIKey)
    access_token = cache.get('access_token')
    kite.set_access_token(access_token)

    #pinfo(manager.pause)
   
    try:
        msg_j = json.loads(msg)
        cmd = msg_j['cmd']

        if cmd == 'cancel':
            pinfo('Cancel Order({})'.format(mode))

            #if mode == 'live':
            symbol = msg_j['symbol']
            #pinfo(symbol)
            cancel_order(kite, [symbol])
        elif cmd == 'cancelAll':
            #if mode == 'live':
            cancel_all(kite)
        elif cmd == 'getOrder':
            pinfo(getOrders(kite))

        else:

            hash_key = msg_j['symbol']
            price = float(msg_j['price'])
            quantity = int(msg_j['qty'])

            symbol = cache.getValue(hash_key, 'stock')
            mode = cache.getValue(hash_key, 'mode')
            state = cache.getValue(hash_key, 'state')

            if manager.pause == True:
                pwarning('Order Handler Paused: Can not place order now: {}'.format(msg))
                if state == 'PO:LONG':
                    cache.setValue(hash_key, 'state','LONG')
                elif state == 'PO:SHORT':
                    cache.setValue(hash_key, 'state','SHORT')
                else:
                    cache.setValue(hash_key, 'state','SCANNING') 
                return

            pinfo('Placeorder({}):{}: {}: {}x{}'.format(mode, cmd, symbol, quantity, price))

            if cmd == 'buy':
                if mode == 'live':
                    order_id = buy_limit(kite, symbol, price, quantity)
                    cache.setValue(hash_key,'order_id', order_id)
                else:
                    state = cache.getValue(hash_key, 'state')
                    pinfo(state)
                    if state == 'PO:LONG':
                        cache.setValue(hash_key, 'state','LONG')
                    else:
                        cache.setValue(hash_key, 'state','SCANNING')                    

            elif cmd == 'sell':
                if mode == 'live':
                    order_id = sell_limit(kite, symbol, price, quantity)
                    cache.setValue(hash_key,'order_id', order_id)
                else:
                    state = cache.getValue(hash_key, 'state')
                    pinfo(state)
                    if state == 'PO:SHORT':
                        cache.setValue(hash_key, 'state','SHORT')
                    else:
                        cache.setValue(hash_key, 'state','SCANNING')

        
    except:
        perror('Error in order handler')
        pass


#####################################################################################################################
#### Kite Ticker Handler: Provides api to Subscribe, Unsubscribe for ticks                                        ###
#####################################################################################################################

def kite_ticker_handler(manager, msg):
    global kws, kite, kite_api_key, access_token
    pdebug('kite_ticker_handler: {}'.format(msg))
    # 1: Start kite websocket connections
    # Initialise
    if kws is None and msg != 'INIT':
        return

    pdebug('kite_ticker_handler: Exec {}'.format(msg))

    if msg == 'INIT':
        try:
            cache.set('KiteAPIKey',kite_api_key)
            access_token = cache.get('access_token')
            kite.set_access_token(access_token)
            pinfo(kite.access_token)
            kws = KiteTicker(kite_api_key, kite.access_token)

            # Assign the callbacks.
            kws.on_ticks = on_ticks
            kws.on_connect = on_connect
            kws.on_order_update = on_order_update
            #kws.on_close = on_close
            cache.publish('kite_ticker_handler'+cache_postfix,'START')
        except Exception as e:
            perror('Could not connect to KITE server: {}'.format(e))
    elif msg == 'START':
        kws.connect(threaded=True)
        #kws.subscribe(value)
        #kws.set_mode(kws.MODE_LTP, value) #Default mode LTP

    elif msg == 'STATUS':
        pinfo(kws.is_connected())
    elif msg == 'CLOSE':
        cache.set('Kite_Status','closed')
        cache.publish('ohlc_tick_handler'+cache_id,'stop')
        #cache.publish('ohlc_tick_handler'+cache_id,'stop')
        kws.close()
    elif msg == 'profile':
        pinfo(kite.profile())
    else:
        try:
            msg_j = json.loads(msg)
            cmd = msg_j['cmd']
            value = msg_j['value']
            mode_map = {'ltp':kws.MODE_LTP, 'full':kws.MODE_FULL, 'quote': kws.MODE_QUOTE}
            mode = mode_map[msg_j['mode']]
            
            if cmd == 'add':
                kws.subscribe(value)
                kws.set_mode(mode, value)
                pinfo('Subscribe: {}: {}'.format(cmd, msg))
            elif cmd == 'remove':
                kws.unsubscribe(value)
                pinfo('Un-Subscribe: {}: {}'.format(cmd, msg))
            elif cmd == 'mode':
                pinfo('Set Mode: {}: {}'.format(cmd, msg))
                kws.set_mode(mode, value)
        except:
            pass


###################################################
### Kite CallBack functions                     ###
###################################################

ticker_count = 0
def on_ticks(ws, ticks):
  global ticker_count
  # Callback to receive ticks.
  ticker_count = ticker_count + 1

  if ticker_count % 1000 == 0:
    pdebug("Ticks: {}".format(ticks))
  
  cache = cache_state(cache_id)
  cache.set('tick_count', ticker_count)
  #for tick in ticks:
  notification_despatcher(ws, ticks)


def on_connect(ws, response):
    pinfo('connected')
    cache = cache_state(cache_id)
    
    value = list(map(int,cache.smembers('ticker_list'))) #Initialize
    pinfo(value)
    if len(value) > 0:
        ws.subscribe(value)
        ws.set_mode(ws.MODE_QUOTE, value)

    #ws.cache = cache_state(cache_id)
    cache.set('Kite_Status','connected')

    cache.publish('ohlc_tick_handler'+cache_id,'start')
    #pinfo('Exiting on connected')

  # Callback on successful connect.
  # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
  #ws.subscribe([225537])

  # Set RELIANCE to tick in `full` mode.
  # MODE_LTP, MODE_QUOTE, or MODE_FULL

  #ws.set_mode(ws.MODE_LTP, [225537])
  #ws.set_mode(ws.MODE_FULL, [225537]) 
  #ws.set_mode(ws.MODE_LTP, [225537, 3861249]) 
  #ws.set_mode(ws.MODE_MODE_QUOTE, [2714625,779521]) 

def on_close(ws, code, reason):

  cache = cache_state(cache_id)
  # On connection close stop the main loop
  # Reconnection will not happen after executing `ws.stop()`
  cache.set('Kite_Status','closed')
  cache.publish('ohlc_tick_handler'+cache_id,'stop')
  #ws.cache.xtrim('msgBufferQueue'+cache_postfix, 0, False)
  #notification_despatcher(ws,'done')
  ws.stop()
  pinfo('Exiting on close')

def on_order_update(ws, data):
  #logger.info("New Order Update")
  notification_despatcher(ws,data, Tick=False)

    
#TODO: Watchdog implementation to resume processes

