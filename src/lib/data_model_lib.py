import pandas as pd
import numpy as np
from redis import Redis
from datetime import datetime
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo

userid = 'suhan'

# Wrapper for Redis cache
class cache_state(Redis):
    def __init__(self, postfix='backtest'):
        Redis.__init__(self, host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
        pdebug("Cache initialized for: "+postfix)
        self.hash_postfix = postfix
        
    def add(self, key, reset=False):
        hash_key = key+self.hash_postfix
        
        pinfo(hash_key)

        if self.hlen(hash_key) == 0 or reset == True:
            self.hmset(hash_key, {'stock':key, 'qty':0, 'amount':0,'p_n_l':0.0,'Total_p_n_l':0.0,
                                       'low':0.0,'sl':0.0,'ltp':0.0,'tp':0.0,'high':0.0,'last_processed':'1999-01-01',
                                       'state':'INIT','algo':'', 'freq':'day','hdf_freq':'day'})
            # Trade Log: [{timestamp, buy, sale, amount, profit, cum_profit, W_L, Mode}]
            # Amount: -ve for Buy, +ve for sale; W_L: +1 for Win, -1 for Loss; Mode: EN|EX|SL|TP|F
            self.set(hash_key+'Trade', pd.DataFrame().to_json(orient='columns'))
            self.set(hash_key+'OHLC', pd.DataFrame().to_json(orient='columns'))
        self.sadd(self.hash_postfix, key)
        
    def getTrades(self, key):
        hash_key = key+self.hash_postfix+'Trade'
        df = pd.read_json(self.get(hash_key))
        return df
    
    def pushTrade(self, key, df):
        hash_key = key+self.hash_postfix+'Trade'
        cache_buff = pd.read_json(self.get(hash_key))
        cache_buff = cache_buff.append(df)
        self.set(hash_key, cache_buff.to_json(orient='columns'))

    def getOHLC(self, key):
        hash_key = key+self.hash_postfix+'OHLC'
        df = pd.read_json(self.get(hash_key))
        return df

    def setOHLC(self, key, df):
        hash_key = key+self.hash_postfix+'OHLC'
        self.set(hash_key, df.to_json(orient='columns'))
        return df

    def pushOHLC(self, key, df):
        hash_key = key+self.hash_postfix+'OHLC'
        cache_buff = pd.read_json(self.get(hash_key))
        cache_buff = cache_buff.append(df)
        
        #pinfo("CB: {}=>{}".format(hash_key, cache_buff.shape))
        self.set(hash_key, cache_buff.to_json(orient='columns'))
        
    def getValue(self, key='', field=''):
        hash_key = key+self.hash_postfix
        if key == '':
            df = pd.DataFrame()
            for key in self.smembers(self.hash_postfix):
                hash_key = key+self.hash_postfix
                tmp_df = pd.DataFrame([self.hgetall(hash_key)])
                df = df.append(tmp_df, ignore_index=True)
            return df
            
        elif field == '': # return all
            return pd.DataFrame([self.hgetall(hash_key)])
        else:
            return self.hget(hash_key,field)
    
    def setValue(self, key, field, value):
        hash_key = key+self.hash_postfix
        return self.hset(hash_key, field, value)
   
    def remove(self, key=''):
        if key == '':
            for key in self.smembers(self.hash_postfix):
                hash_key = key+self.hash_postfix
                for field in self.hkeys(hash_key):
                    self.hdel(hash_key, field)

                self.srem(self.hash_postfix, key)
            
        else:
            hash_key = key+self.hash_postfix
            for field in self.hkeys(hash_key):
                self.hdel(hash_key, field)

            self.srem(self.hash_postfix, key)
            
    def reset(self, key=''):
        if key == '':
            for key in self.smembers(self.hash_postfix):
                self.add(key,True)
        else:
            self.add(key,True)
            
    def getKeys(self):
        return self.smembers(self.hash_postfix)