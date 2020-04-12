
#setup logging
import logging
logging.basicConfig(format='%(asctime)s:%(levelname)s:\t%(message)s', level=logging.DEBUG, datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('simple_example')
#logger.setLevel(logging.DEBUG)

pdebug = lambda x: logger.debug(x)
pinfo = lambda x: logger.info(x)
perror = lambda x: logger.error(x)
pexception = lambda x: logger.critical(x)



import threading
import time
from queue import Queue
from redis import Redis
import multiprocessing

exitFlag = 0

conn = Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)

# The base thread class to enable multithreading
class myThread (threading.Thread):
    def __init__(self, manager, name, callback, pubsub=True, q="default"):
        threading.Thread.__init__(self)
        self.threadID = manager.threadID
        self.name = name
        self.callback = callback
        self.pubsub = pubsub
        self.queue = q
        self.manager = manager
        
    def run(self):
        pdebug("Starting " + self.name)
        if self.pubsub:
            self.thread_function(self.callback)
        else:
            self.thread_job(self.callback, self.queue)
        pdebug("Exiting " + self.name)
    
    # The thread function for infinite threads which can expect IPC using Redis
    def thread_function(self, callback):
        pubsub = conn.pubsub()
        pubsub.subscribe([self.name+'/cmd', self.name+'/data'])
        
        pubsub.get_message(self.name+'/cmd')
        pubsub.get_message(self.name+'/data')

        for item in pubsub.listen():
            channel = item['channel'].split('/')[1]
            data = item['data']
            pdebug(self.name+':'+channel)
            if channel== 'data':
                callback(self.manager, data)
            elif channel== 'cmd' and data == 'stop':
                pubsub.unsubscribe()
                break
    
    #The thread function for one of tasks
    def thread_job(self, callback, queue):
        #pdebug(conn.rpop(queue))
        callback(queue)

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
        
    def add(self, name, callback, pubsub=True, q="default"):
        # Create an instance of mythrade class and start the thread
        thread = myThread(self, name, callback, pubsub, q)
        thread.start()
        self.threads.append(thread)
        self.threadID += 1

def hello_world1(manager, data):
    pdebug("1: "+ str(data))
    
def hello_world2(manager, data):
    pdebug("2: "+ str(data))


###################### Ordering ######################
'''
# order/data
{
'stock':'NIFTY',
'qty':'12',
'type':'BO',
'SL':'1234',
'Target':'1234',
'Price':'1234'
}


'''
import pandas as pd
import json

def order_job(queue):
    data = conn.rpop(queue)
    order_df = pd.read_json(data)
    
    stock = order_df['stock'][0]
    state=stock+'_state'
    
    pdebug('order_job: start: {}\n{}'.format(stock, order_df))
    
    pubsub = conn.pubsub()
    pubsub.subscribe([stock+'/cmd'])
    
    for item in pubsub.listen():
        data = item['data']
        pdebug('order_job: running: {}'.format(stock))
        conn.set(state, 'running')
        
        if data == "abort":
            conn.delete(state)
            pubsub.unsubscribe()
            break
        elif data == "info":
            pinfo("{} : {}\n {}\n".format(stock, conn.get(state), order_df))
    conn.delete(state)
            


#order_queue_lock = r.lock('order_queue_lock')
orderManager = ""
def order_handler(manager, data):
    pdebug('order_handler: {}'.format(data))
    stock = pd.read_json(data)['stock']
    state = stock[0]+'_state'
    if conn.get(state) == None:
        #Kex does not exist
        conn.lpush('order_queue', data)
        conn.set(state,'init')
        manager.add("order_job_"+stock[0],order_job, False, 'order_queue')
    else:
        for t in manager.threads:
            print(t.name)
        pinfo('order_handler: Trade in progress: publish command to {}/cmd'.format(pd.read_json(data)['stock'][0]))


###################### BackTest ######################
'''
# backtest/data
{
'stock':'NIFTY',
'ohlc':[],
'algo':'BO'
}


'''
import json
import ast
from datetime import datetime, timedelta
import time

def backtest_handler(manager, data):
    pdebug('order_handler: {}'.format(data))

    try:
        json_data = json.loads(data)
    except:
        pdebug("input data is not json")
        return
    stock = json_data['stock']
    toDate = json_data['toDate']
    fromDate = json_data['fromDate']
    algo = json_data['algo']

    temp_file = pd.HDFStore("data/kite_cache_day.h5", mode="r")
    tmpdata = temp_file.get('/day/NSE/'+stock)

    per1 = pd.date_range(start =fromDate, end =toDate, freq ='1D') 
    startDate = datetime.strptime(fromDate,'%Y-%m-%d') - timedelta(days=30)

    for val in per1:
        data = tmpdata[(tmpdata.index >= startDate) & (tmpdata.index <= val)]
        conn.set(stock, data.to_json(orient='columns'))
        time.sleep(0.3)
        #pdebug(val)

    conn.set('done',1)
    exec(algo)
    #OPEN = stock_data['open']
    #CLOSE = stock_data['close']
    #HIGH = stock_data['high']
    #LOW = stock_data['low']
    

################## Freedom App #######################
