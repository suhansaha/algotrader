import pandas as pd
import numpy as np
from redis import Redis
from datetime import datetime, timedelta
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo

userid = 'suhan'

       
to_tick = lambda df, delta: pd.DataFrame( data = df.values, index =  df.index+timedelta(seconds=delta), columns=['ltp']  )
def ohlc_to_tick(df):
    ohlc_df = pd.DataFrame()
    #pinfo(df)
    tmp_df = to_tick(df['open'], 1)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['close'], 50)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['high'], 10)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['low'], 20)
    ohlc_df = ohlc_df.append(tmp_df)

    #pinfo(ohlc_df)
    return ohlc_df

def resample(df, freq = '1T'):
    tmp_df = pd.DataFrame()    
    tmp_df = df.resample(freq,label='left').agg(['last','max','min','first']).dropna()
    tmp_df.columns = ['close', 'high', 'low', 'open']
    #print(tmp_df.head(5))
    return tmp_df


# Wrapper for Redis cache
class cache_state(Redis):
    def __init__(self, postfix='backtest'):
        Redis.__init__(self, host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
        pdebug("Cache initialized for: "+postfix)
        self.hash_postfix = postfix
        
    def add(self, key, reset=False):
        hash_key = key+self.hash_postfix
        
        if self.hlen(hash_key) == 0 or reset == True:
            self.hmset(hash_key, {'stock':key, 'qty':0, 'SL %':0.0, 'TP %':0.0, 'amount':0,'price':0.0,'P&L':0.0,'P&L %':0.0,'Total P&L':0.0,'Total P&L %':0.0,
                                       'low':0.0,'sl':0.0,'ltp':0.0,'ltp %':0.0,'tp':0.0,'high':0.0,'last_processed':'1999-01-01',
                                       'state':'INIT','mode':'PAUSE','algo':'', 'freq':'1D','hdf_freq':'day'})
            # Trade Log: [{timestamp, buy, sale, amount, profit, cum_profit, W_L, Mode}]
            # Amount: -ve for Buy, +ve for sale; W_L: +1 for Win, -1 for Loss; Mode: EN|EX|SL|TP|F
            self.set(hash_key+'Trade', pd.DataFrame().to_json(orient='columns'))
            self.set(hash_key+'OHLC', pd.DataFrame().to_json(orient='columns'))
            self.set(hash_key+'TICK', pd.DataFrame().to_json(orient='columns'))
        self.sadd(self.hash_postfix, key)

        pinfo('{}=>{}'.format(hash_key, self.hgetall(hash_key)))
 
    
    def pushCache(self, hash_key, df):
        cache_buff = pd.read_json(self.get(hash_key))
        cache_buff = cache_buff.append(df)
        self.setCache(hash_key, cache_buff)
    
    def setCache(self, hash_key, df):
        self.set(hash_key, df.to_json(orient='columns'))

    def getTrades(self, key):
        hash_key = key+self.hash_postfix+'Trade'
        df = pd.read_json(self.get(hash_key))
        return df
    
    def pushTrade(self, key, df):
        hash_key = key+self.hash_postfix+'Trade'
        self.pushCache(hash_key, df)

    def getOHLC(self, key, freq='1D'):
        freq = self.getValue(key, 'freq')
        if freq != '1D':
            freq= '1T'
        #pinfo(freq)

        hash_key = key+self.hash_postfix+'OHLC'
        hash_key1 = key+self.hash_postfix+'TICK'
        df = pd.read_json(self.get(hash_key))
        df1 =  pd.read_json(self.get(hash_key1))
        #pinfo(df1['ltp'].head())
        #return resample(df['ltp'], freq)
        resample_df = resample(df1['ltp'], freq)
        #pinfo(resample_df.head())
        return resample_df
    
    def setOHLC(self, key, df):
        # Overwrites existing content
        self.setCache(key+self.hash_postfix+'OHLC', df)
        self.setCache(key+self.hash_postfix+'TICK', ohlc_to_tick(df))
        return df

    def pushTICK(self, key, df):
        #pdebug1("{}=>{}".format(key,df))
        self.pushCache(key+self.hash_postfix+'TICK', df)
        return df

    def pushOHLC(self, key, df):
        self.pushCache(key+self.hash_postfix+'OHLC', df)
        self.pushCache(key+self.hash_postfix+'TICK', ohlc_to_tick(df))
        
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