import pandas as pd
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta

from talib import MACD, MACDEXT, RSI, BBANDS, MACD, AROON, STOCHF, ATR, OBV, ADOSC, MINUS_DI, PLUS_DI, ADX, EMA, SMA
from talib import LINEARREG, BETA, LINEARREG_INTERCEPT, LINEARREG_SLOPE, STDDEV, TSF, ADOSC, VAR, ROC, MIN, MAX, MINMAX
#from talib import CDLABANDONEDBABY, CDL3BLACKCROWS,CDLDOJI, CDLDOJISTAR, CDLDRAGONFLYDOJI,CDLENGULFING,CDLEVENINGDOJISTAR,CDLEVENINGSTAR, CDLGRAVESTONEDOJI, CDLHAMMER, CDLHANGINGMAN,CDLHARAMI,CDLHARAMICROSS,CDLINVERTEDHAMMER,CDLMARUBOZU,CDLMORNINGDOJISTAR,CDLMORNINGSTAR,CDLSHOOTINGSTAR,CDLSPINNINGTOP,CDL3BLACKCROWS, CDL3LINESTRIKE, CDLKICKING
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, redis_conn, cache_type

# ====== Tradescript Wrapper =======
# Methods

#TREND_UP = lambda a,b: ROC(a, b) >= 0.1
#TREND_DOWN = lambda a,b: ROC(a, b) <= -0.1

#import traceback
#TREND_UP = lambda a,b: a > MAX(REF(a,1),b)
#TREND_DOWN = lambda a,b: a < MIN(REF(a,1),b)

#CROSSOVER = lambda a, b: (REF(a,1)<=REF(b,1)) & (a > b)

#Heikin Asi
def HAIKINASI(ohlc_data_df):
    REF = lambda key, i: ohlc_get(ohlc_data_df.shift(i), key)
    
    OPEN  = ohlc_data_df['open']
    HIGH  = ohlc_data_df['high']
    LOW   = ohlc_data_df['low']
    CLOSE = ohlc_data_df['close']
    
    haOPEN  = (OPEN.shift(1) + CLOSE.shift(1))/2
    haHIGH  = pd.DataFrame([HIGH,OPEN,CLOSE]).max(axis = 0, skipna = True)
    haLOW   = pd.DataFrame([LOW,OPEN,CLOSE]).min(axis = 0, skipna = True)
    haCLOSE = (OPEN+HIGH+LOW+CLOSE)/4
    
    return (haOPEN, haHIGH, haLOW, haCLOSE)

ohlc_get = lambda df, key: df.iloc[-1][key]
REF = lambda df, i: df.iloc[-i-1]

def order_details(cache, key, decision = 'WAIT', x2 = -1, qty=-1, sl=-1, tp=-1):
    redis_conn.set('decision'+cache_type,decision)

def myalgo_old(cache, key, ohlc_data_df, algo='', state='SCANNING'): 
    #pdebug(ohlc_data_df.shape)
    ohlc_data_temp = ohlc_data_df.tail(31).head(30)

    #pinfo(ohlc_data_temp)
    
    if ohlc_data_temp.shape[0] < 5:
        return 'WAIT'

    OPEN = ohlc_data_temp['open']
    CLOSE = ohlc_data_temp['close']
    HIGH = ohlc_data_temp['high']
    LOW = ohlc_data_temp['low']
    #VOLUME = ohlc_data_temp['volume']
    
    (haOPEN, haHIGH, haLOW, haCLOSE) = HAIKINASI(ohlc_data_temp)

    decision = 'WAIT'
    redis_conn.set('decision'+cache_type,decision)
    TIME = ohlc_data_temp.index[-1].minute+ohlc_data_temp.index[-1].hour*60
    BUY = lambda qty=-1, sl=-1, tp=-1, x2 = -1:order_details(cache, key, 'BUY', x2, qty, sl, tp)
    SELL = lambda qty=-1, sl=-1, tp=-1, x2 = -1:order_details(cache, key, 'SELL', x2, qty, sl, tp)
    WAIT = lambda : order_details(cache, key, 'WAIT')
    
    if algo != '':
        #postfix = "redis_conn.set('decision"+cache_type+"',decision)"
        
        code = algo #+ '\n'+ postfix
        #pinfo(code)

        try:
            exec(code)
        except:
            perror("Error in executing algorithm")
    else:
        if (REF(haCLOSE,2) < REF(haOPEN,2)) and (REF(haCLOSE,1) < REF(haOPEN,1)) and (REF(haCLOSE,0) > REF(haOPEN,0)): 
            BUY()
        elif (REF(haCLOSE,2) > REF(haOPEN,2)) and (REF(haCLOSE,1) > REF(haOPEN,1)) and (REF(haCLOSE,0) < REF(haOPEN,0)): 
            SELL()

        #redis_conn.set('decision'+cache_type,decision)

    decision = redis_conn.get('decision'+cache_type)
    return decision #"BUY"|"SELL"


def myalgo(cache, key, ohlc_data_df, algo='', state='SCANNING', quick=False): 
    #pdebug(ohlc_data_df.shape)

    if quick == False:
        ohlc_data_temp = ohlc_data_df.tail(31).head(30)
    else:
        ohlc_data_temp = ohlc_data_df

    #pinfo(ohlc_data_temp)
    
    if ohlc_data_temp.shape[0] < 5: #TODO
        return 'WAIT'

    OPEN = ohlc_data_temp['open']
    CLOSE = ohlc_data_temp['close']
    HIGH = ohlc_data_temp['high']
    LOW = ohlc_data_temp['low']
    #VOLUME = ohlc_data_temp['volume']
    
    (haOPEN, haHIGH, haLOW, haCLOSE) = HAIKINASI(ohlc_data_temp)

    decision = 'WAIT'
    redis_conn.set('decision'+cache_type,decision)
    TIME = ohlc_data_temp.index[-1].minute+ohlc_data_temp.index[-1].hour*60
    BUY = lambda qty=-1, sl=-1, tp=-1, x2 = -1:order_details(cache, key, 'BUY', x2, qty, sl, tp)
    SELL = lambda qty=-1, sl=-1, tp=-1, x2 = -1:order_details(cache, key, 'SELL', x2, qty, sl, tp)
    WAIT = lambda : order_details(cache, key, 'WAIT')
    
    REF = lambda df, i: df.shift(i)
    TREND_UP = lambda : ROC(CLOSE, 10) >= 0.1
    TREND_DOWN = lambda : ROC(CLOSE, 10) <= -0.1
    CROSSOVER = lambda a, b: (REF(a,1)<=REF(b,1)) & (a > b)
    sell = pd.DataFrame()
    buy = pd.DataFrame()
    def update_decision(buy, sell):
        try:
            if buy[-1] == True:
                BUY()
            elif sell[-1] == True:
                SELL()
            else:
                WAIT()
        except:
            WAIT()

    if algo != '':

        postfix = "update_decision(buy, sell)"        
        
        code = algo + '\n'+ postfix

        try:
            exec(code)
        except:
            perror("Error in executing algorithm")

    else:
        sell = (REF(haOPEN, 0) > REF(haCLOSE,0)) & (REF(haOPEN, 1) < REF(haCLOSE,1))
        buy = (REF(haOPEN, 0) < REF(haCLOSE,0)) & (REF(haOPEN, 1) > REF(haCLOSE,1))
        update_decision(buy, sell)
    
    decision = redis_conn.get('decision'+cache_type)

    if quick == False:
        return decision #"BUY"|"SELL"
    else:
        return buy, sell