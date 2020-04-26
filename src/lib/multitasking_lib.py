import threading
import time
import pandas as pd
import math
from queue import Queue
from redis import Redis
import multiprocessing
import numpy as np

conn = Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)

from lib.logging_lib import *
from lib.kite_helper_lib import *
from lib.algo_lib import *
import sys
import json
import ast
from datetime import datetime, timedelta
import time

exitFlag = 0


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
        pdebug("Starting " + self.name)
        if self.pubsub:
            pinfo("Starting Handler: " + self.name)
            self.thread_pubsub(self.callback)
            pinfo("Terminating Handler: " + self.name)
        else:
            self.thread_worker(self.callback)
        pdebug("Exiting " + self.name)
    
    # The thread function for infinite threads which can expect IPC using Redis
    def thread_pubsub(self, callback):
        pubsub = conn.pubsub()
        pubsub.subscribe([self.name])
        
        pubsub.get_message(self.name)

        for item in pubsub.listen():
            msg = item['data']
            if msg == 'stop':
                pubsub.unsubscribe()
                break
            else:
                callback(self.manager, msg)
    
    #The thread function for one of tasks
    def thread_worker(self, callback):
        #pdebug(conn.rpop(queue))
        callback(self.msg)

jobs = []
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

def trade_analysis(stock):
    trade_log = pd.read_json(conn.get(stock+'Trade'))

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

    for index, row in trade_log.iterrows():
        if not math.isnan(row.buy):
            profit -= row['buy']
            #print(row['buy'])  
        if not math.isnan(row.sell):
            profit += row['sell']
            #print(row['sell'])

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
 ===================================================='''.format(stock, total_profit, max_loss, max_profit, total_win, total_loss, max_winning_streak, max_loosing_streak, trade_log.fillna(''))  )


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
    pdebug('notification_despatcher: {}'.format(msg))
    # Step 1: Extract msg type: Tick/Callbacks
    
    # Step 2.1: If Tick
    if Tick == True:
        # Push msg to msgBufferQueue
        #pdebug(msg)
        msg_id = conn.xadd('msgBufferQueue',{'msg': msg})
        pdebug("Despatcher: {}".format(msg_id))
    
    # Step 2.2: else
    else:
        # Push msg to notificationQueue
        conn.xadd('notificationQueue',{'msg': msg})

###################### BackTest ######################
'''
# backtest/data
{
'stock':'NIFTY',
'ohlc':[],
'algo':'BO'
}


'''
 

def kite_simulator(manager, msg):
    pinfo('kite_simulator: {}'.format(msg))

    try:
        data = json.loads(msg)
    except:
        perror('kite_simulator: Invalid msg: {}'.format(msg))
        return
    #pdebug(data)
    
    toDate = data['toDate']
    fromDate = data['fromDate']
    algo = data['algo']
    sl = data['sl']
    target = data['target']
    qty = data['qty']

    startDate = datetime.strptime(fromDate,'%Y-%m-%d') - timedelta(days=1) #TODO
    startDatestr = startDate.strftime('%Y-%m-%d')
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

        # Initialize state
        hash_key = stock_key+'_state'
        
        try:
            all_keys = list(conn.hgetall(hash_key).keys())
            conn.hdel(hash_key,*all_keys)
        except:
            pass
        
        conn.hmset(hash_key, {'state':'INIT','stock':stock_key, 'algo':algo, 'freq':freq,
        'qty':qty,'price':0,'sl':sl,'target':target,'last_processed':'1999-01-01'})

        conn.set(stock_key, pd.DataFrame().to_json(orient='columns')) #Used for plotting
        conn.set(stock_key+'Trade', pd.DataFrame().to_json(orient='columns')) #Used for storing trade data
    

    stock = data['stock'][-1] #TODO: Add for loop
    conn.publish('trade_handler','start')
    conn.set('logMsg','Backtest Started: {} :\n'.format(stock)) # Used for displaying trade log

    no = ohlc_data[stock].shape[0]
    for i in np.linspace(0,no-1,no): # Push data
        i = int(i)

        for stock in  data['stock']:
            row = ohlc_data[stock].iloc[i]
            index = ohlc_data[stock].index[i]
        #for index, row in ohlc_data[stock].iterrows(): 
            update_plot_cache(stock, row)
            #pinfo(row)
            # Check square off conditions
        
            # Construct Json message like Kite
            mydate = "{}-{}-{} {}:{}:{}".format(index.year,index.month,index.day, index.hour, index.minute, index.second)        
            msg = {exchange+":"+stock:{"ohlc":{'date':mydate,'open':row['open'],'high':row['high'],'low':row['low'],'close':row['close'],'volume':row['volume']}}}
            #pinfo(msg)
            msg = json.dumps(msg)
            
            # Call notification_despatcher
            notification_despatcher(None, msg)
            # Optional: wait few miliseconds
            #time.sleep(0.1)

    for stock in  data['stock']:
        conn.set(stock, ohlc_data[stock].to_json(orient='columns'))
    
    pinfo('Kite_Simulator: Done')
    time.sleep(1)  
    notification_despatcher(None, 'next')
    time.sleep(1)
    conn.set('done',1)

    for stock in  data['stock']:
        trade_analysis(stock)


def update_plot_cache(key, tmp_df):
    cache_buff = pd.read_json(conn.get(key))
    #tmp_df = ohlc_data.loc[index]
    cache_buff = cache_buff.append(tmp_df)
    conn.set(key, cache_buff.to_json(orient='columns'))


def trade_handler(manager, msg):
    pdebug('trade_handler: {}'.format(msg))
    # Step 1: Blocking call to msgBufferQueue and notificationQueue
    conn.xtrim('msgBufferQueue',maxlen=0, approximate=False)
    conn.xtrim('notificationQueue',maxlen=0, approximate=False)
    while(True):
        msg_q = conn.xread({'msgBufferQueue':'$','notificationQueue':'$'}, block=0, count=100)
        msgs_q = conn.xread({'msgBufferQueue':'0','notificationQueue':'0'}, block=1, count=100)
        conn.xtrim('msgBufferQueue',maxlen=0, approximate=False)
        conn.xtrim('notificationQueue',maxlen=0, approximate=False)
        
        # Step 2: Process notifications: Start a worker thread for each notification
        
        #TODO
        
        # Step 3: Process tick: Start a worker thread for each msg        
        for msg in msgs_q[0][1]:
            pdebug('trade_handler: {}'.format(msg[1]['msg']))
            
            try:
                data = json.loads(msg[1]['msg'])
            except:
                perror("Un-supported message: {} : {}".format(msg, sys.exc_info()[0]))
                break

            for key in data.keys():
                stock = key.split(':')[1]
                exchange = key.split(':')[0]

            hash_key = stock+'_state'
            freq = conn.hget(hash_key,'freq')
            state = conn.hget(hash_key,'state')


            temp_df = msg_to_ohlc(data)
            if state == 'INIT': # State: Init: Load historical data from cache
                # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
                toDate = (temp_df.index[0] - timedelta(days=1)).strftime('%Y-%m-%d') #TODO: Change based on freq
                fromDate = (temp_df.index[0] - timedelta(days=2)).strftime('%Y-%m-%d')
                ohlc_data = getData(stock, fromDate, toDate, exchange, freq, False, stock)
            else: # Load data from OHLC buffer in hash
                ohlc_data = pd.read_json(conn.hget(hash_key, 'ohlc'))
            

            ohlc_data = ohlc_data.append(temp_df) #Append to ohlc_data

            #pinfo(ohlc_data.tail(1))

            # Add to OHLCBuffer in hash
            conn.hset(hash_key,'ohlc',ohlc_data.to_json())

            # Start job to process Tick
            manager.add(stock, trade_job, False, hash_key)
            pdebug(msg[0])
            
# A thread function to process notifications and tick
algo_idle = myalgo
algo_long_so = myalgo
algo_short_so = myalgo

trade_lock = Lock() #TODO: make lock per stockname
def trade_job(hash_key):
    pdebug('trade_job: {}'.format(hash_key))
    
    trade_lock.acquire()
    # Step 1.1: Get stock name from the message    
    
    # Step 1.2: Get state for the stock from the redis
    state = conn.hget(hash_key,'state')
    if not state:
        return
    stock = conn.hget(hash_key,'stock')
    freq = conn.hget(hash_key,'freq')
    algo = conn.hget(hash_key,'algo')
    
    pdebug("{}: {}: {}".format(hash_key, stock, state ))
    ohlc_df = pd.read_json(conn.hget(hash_key,'ohlc'))
    
    last_processed = ohlc_df.index[-1].strftime('%Y-%m-%d')
    pdebug("{}=>{}".format(last_processed,conn.hget(hash_key,'last_processed')))
    
    if last_processed == conn.hget(hash_key,'last_processed'):   
        trade_lock.release()
        return
    else:
        conn.hset(hash_key,'last_processed',last_processed)
    
    #print('{}:{}'.format(stock,ohlc_df.index[-1]))
    
    # Step 2: Switch to appropriate state machine based on current state
    if state == 'INIT': # State: Init
        # 1: Populate Redis buffer stock+"OHLCBuffer" with historical data
            # Done inside thread handler
        
        # 2: Set state to Scanning
        conn.hset(hash_key,'state','SCANNING')
        pass
    
    elif state == 'SCANNING':  # State: Scanning
        # 1: Run trading algorithm for entering trade
        tradeDecision = algo_idle(ohlc_df, algo)
        
        # 2: If Algo returns Buy: set State to 'Pending Order: Long'
        if tradeDecision=="BUY":
            placeorder("BUY ", ohlc_df, stock, last_processed)
            #logtrade("BUY : {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
            conn.hset(hash_key,'state','PO:LONG')
        
        # 3: If Algo returns Sell: set State to 'Pending Order: Short'
        elif tradeDecision=="SELL":
            placeorder("SELL", ohlc_df, stock, last_processed)
            #logtrade("SELL: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
            conn.hset(hash_key,'state','PO:SHORT')
        
        # 4: Update TradeMetaData: Push order details to OrderQueue
    
    elif state == 'PO:LONG': # State: Pending Order: Long
    
        # 1: On Fill: set State to Long
        conn.hset(hash_key,'state','LONG')
        pass
    
    
    elif state == 'PO:SHORT': # State: Pending Order: Short
    
        # 1: On Fill: set State to Short
        conn.hset(hash_key,'state','SHORT')
        pass
    
    
    elif state == 'LONG': # State: Long
    
        # 1: If notification for AutoSquare Off: set state to init
        
        # 2: Else run trading algorithm for square off
        
        tradeDecision = algo_long_so(ohlc_df, algo)
        if tradeDecision == "SELL":
            placeorder("SO-S", ohlc_df, stock, last_processed)
            #logtrade("SO-S: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))

            # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'   
            conn.hset(hash_key,'state','SQUAREOFF')
    
    
    elif state == 'SHORT': # State: Short
    
        # 1: If notification for AutoSquare Off: set state to init
        
        # 2: Else run trading algorithm for square off
        tradeDecision = algo_short_so(ohlc_df, algo)
        
        if tradeDecision == "BUY":
            placeorder("SO-B", ohlc_df, stock, last_processed)
            #logtrade("SO-B: {} : {} -> {}".format(last_processed, stock, ohlc_get(ohlc_df,'close')))
        
            # 3: If algo returns square off: then push square off details to OrderQueue, set state to 'Awaiting Square Off'
    
            conn.hset(hash_key,'state','SQUAREOFF')
        
    elif state == 'SQUAREOFF':  # State: Awaiting Square Off
        
        conn.hset(hash_key,'state','INIT')
        pass
   
        # 1: On Fill notification: set state to Init

    trade_lock.release()


def placeorder(prefix, df, stock, last_processed):
    logtrade(prefix+" : {} : {} -> {}".format(last_processed, stock, ohlc_get(df,'close')))

    tmp_df = pd.DataFrame()
    if prefix == "BUY " or prefix == "SO-B":
        tmp_df['buy'] = df.iloc[-1:]['close']
    else:
        tmp_df['sell'] = df.iloc[-1:]['close']
    #df.iloc[-1].index
    #df.iloc[-1]['close']
    update_plot_cache(stock+'Trade', tmp_df)


def order_handler(manager, msg):
    pdebug('order_handler: {}'.format(msg))
    
    # Step 1: Block for new order request: OrderQueue
    
    # Step 2: Create order msg for Kite: fill metadata
    
    # Step 3: If papertrade: create a log entry
    
    # Step 4: If not a papertrade: despatch order
        

def user_requests_handler(manager, msg): 
    # {'request':'start|stop|pause|buy|sell|so|status','stock':'TCS', 'qty':10, 'price':1200}
    pdebug('user_requests_handler: {}'.format(msg))
    # Step 1: Blocking call to userRequestsQueue
    msg = conn.xread({'userRequestsQueue':'$'}, block=0, count=100)
    
    # Step 2: Process userRequest: Start a worker thread for each request
    
    # 2.1: Start Algo Trade: Stock
    # 2.2: Stop Algo Trade: Stock
    # 2.3: Pause Algo Trade: Stock
    # 2.4: Force Buy: Stock
    # 2.5: Force Sell: Stock
    # 2.6: Square Off
    # 2.7: Current Status
    
    # Step 3: Put it in the userRequestsQueue
   

# This function implements logic to resume trading post abrupt termination
def auto_resume_trade(msg):
    pdebug('resume_trade: {}'.format(msg))
    
    # 1: Get list of open orders from Kite
    
    # 2: Loop through all the open trades in the system
    
    # 3: If an open trade in the system is not present in Kite, reset status to init
    
    # 4: For open trades fill OHLC buffer with historical data
    
def freedom_init(manager, msg):
    pdebug('freedom_init: {}'.format(msg))
    # 0: Initialize settings
    
    # 1: Start Freedom threads and processes
    freedom = threadManager("freedom", ["user_requests_handler", "kite_simulator", "backtest_handler", "trade_handler","order_handler"], 
                        [user_requests_handler, kite_simulator, backtest_handler, trade_handler, order_handler])
    
    # 2: Start kite websocket connections
    # Initialise
    #kws = KiteTicker(KiteAPIKey, kite.access_token)

    # Assign the callbacks.
    #kws.on_ticks = on_ticks
    #kws.on_connect = on_connect
    #kws.on_order_update = on_order_update
    
#TODO: Watchdog implementation to resume processes
#TODO: Implementation of user initiated aborts and restart
