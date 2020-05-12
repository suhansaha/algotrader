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
from lib.data_model_lib import *
import sys
import json
import ast
from datetime import datetime, timedelta
import time
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker

logger.setLevel(1)
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
            elif msg == 'resume':
                self.manager.pause = False
            else:
                self.manager.abort = False
                self.manager.pause = False
                self.workerThread = myThread(self.manager, self.name+'_worker', self.callback, False, msg)
                self.workerThread.start()
                #self.worker = multiprocessing.Process(target=self.callback, args=(self.manager, msg,)) 
                #self.worker.start()
        self.workerThread.join()
    
    #The thread function for one of tasks
    def thread_worker(self, callback):
        callback(self.manager, self.msg)

jobs = []
cache_postfix = 'live'
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


no_of_hist_candles = 100
getDeltaT = lambda freq: timedelta(days=no_of_hist_candles*2) if freq == 'day' else timedelta(days=5)



# This function is called by Kite or Kite_Simulation
def notification_despatcher(ws, msg, id='*', Tick=True ):
    #pdebug('notification_despatcher:{}=>{}'.format(id,msg))
    # Step 1: Extract msg type: Tick/Callbacks
    
    # Step 2.1: If Tick
    if Tick == True:
        # Push msg to msgBufferQueue
        #msg_id = cache.xadd('msgBufferQueue'+cache_postfix, msg, id=id)
        msg_id = cache.xadd('msgBufferQueue'+cache_postfix, {'data':json.dumps(msg)}, id=id)
        #pinfo(msg_id)
    
    # Step 2.2: else
    else:
        # Push msg to notificationQueue
        cache.xadd('notificationQueue'+cache_postfix+'new', {'data':json.dumps(msg)}, id = id)



###################################################
### Kite CallBack functions                     ###
###################################################
def initTrade(ws):
  ws.cache = cache_state(cache_id)

def on_ticks(ws, ticks):
  # Callback to receive ticks.
  #pdebug1("Ticks: {}".format(ticks))
  #for tick in ticks:
  notification_despatcher(ws, ticks)


def on_connect(ws, response):
  initTrade(ws)
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
  # On connection close stop the main loop
  # Reconnection will not happen after executing `ws.stop()`
  ws.stop()

def on_order_update(ws, data):
  #logger.info("New Order Update")
  notification_despatcher(ws,data, Tick=False)


import json
kws = None
kite = None
kite_api_key = 'b2w0sfnr1zr92nxm'
def live_trade_handler(manager, msg):
    global kws, kite, kite_api_key
    pdebug('live_trade_handler: {}'.format(msg))
    # 1: Start kite websocket connections
    # Initialise
    if msg == 'INIT':
        try:
            cache.set('KiteAPIKey',kite_api_key)
            KiteAPIKey = cache.get('KiteAPIKey')
            kite = KiteConnect(api_key=KiteAPIKey)
            access_token = cache.get('access_token')
            kite.set_access_token(access_token)
            pinfo(kite.access_token)
            cache.publish('ohlc_tick_handler'+cache_id,'start')
            cache.publish('live_trade_handler'+cache_id,'START')
            #kws.connect(threaded=True)
        except Exception as e:
            perror('Could not connect to KITE server: {}'.format(e))
    elif msg == 'START':
        kws = KiteTicker(kite_api_key, kite.access_token)
        # Assign the callbacks.
        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.on_order_update = on_order_update
        kws.connect(threaded=True)
        pinfo("KiteTicker: ".format(kws.is_connected()))
        #value = list(cache.smembers('ticker_list'))
        #kws.subscribe(value)
        #kws.set_mode(kws.MODE_LTP, value)
    elif msg == 'STATUS':
        pinfo(kws.is_connected())
    elif msg == 'CLOSE':
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
                pinfo('Subscribe: {}: {}: {}'.format(cmd, mode, msg))
                #value = list(cache.smembers('ticker_list'))
                kws.subscribe(value)
                kws.set_mode(mode, value)
            elif cmd == 'remove':
                pinfo('Un-Subscribe: {}: {}'.format(cmd, msg))
                kws.unsubscribe(value)
            elif cmd == 'mode':
                pinfo('Set Mode: {}: {}'.format(cmd, msg))
                kws.set_mode(mode, value)
        except:
            pass

if __name__ == "__main__":
    tick_manager = threadManager(cache_id, ["live_trade_handler"], [live_trade_handler])