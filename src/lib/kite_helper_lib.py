from lib.logging_lib import *
import pandas as pd
import datetime as dt
from threading import Lock


def getInstruments(exchange='NSE'):
    instruments_df = pd.DataFrame(data=kite.instruments(exchange))
    instruments_df = instruments_df.set_index('tradingsymbol')
    return instruments_df

def downloadData(symbol="HDFC", fromDate= dt.datetime.now() - dt.timedelta(days = 1), toDate=dt.datetime.now(), freq="minute"):
    symbolToken = instruments_df.loc[symbol,'instrument_token']
    
    if type(symbolToken).__name__ == 'Series':
        symbolToken = symbolToken[symbol].values[0]
    
    pdebug(freq)
    raw_data = pd.DataFrame(data=kite.historical_data(symbolToken, fromDate, toDate, freq, continuous=False))
    raw_data = raw_data.set_index('date').tz_localize(None)
    return raw_data

def resample2(data,freq):
    data = data.resample(freq).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    #data.columns = data.columns.droplevel()
    return data

kite_cache_path = 'data/kite_cache_day.h5'
kite_cache_path = 'data/kite_cache.h5'
cache_lock = Lock()

def getData(symbol, fromDate, toDate, exchange="NSE", freq="minute", force=False, symbolToken=''):
    #symbol = "SBIN"
    key = freq+"/"+exchange+"/"+symbol
    
    try:
        if symbolToken == '':
            symbolToken = instruments_df.loc[symbol,'instrument_token']
    except:
        pwarning(symbol+":stock not in the list")
        return pd.DataFrame()

    #fromDate = dt.datetime(2019,4,8)
    #toDate = dt.datetime(2019,4,10)
    
    if force:
        temp_data = downloadData(symbol, fromDate, toDate, freq)
        return temp_data
    
    try:
        cache_lock.acquire()
        temp_file = pd.HDFStore(kite_cache_path, mode="r")
        rDate = temp_file.get(key).tail(1).index
        lDate = temp_file.get(key).head(1).index
        
        #temp_file.close()
        
        #print(fromDate,toDate, lDate, rDate)
        raw_data = pd.read_hdf(temp_file, key=key)

        if   (fromDate < lDate ) and (toDate <= rDate):
            pdebug("Downloading data from fromDate to lDate")
            temp_data = downloadData(symbol,  fromDate, lDate, freq)
            temp_data = temp_data.append(raw_data.tail(-1))
#            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")
        elif (fromDate >=lDate ) and (toDate <= rDate):
            pdebug("Using cache: Not downloading data")
            temp_data = raw_data
        elif (fromDate >= lDate ) and (toDate > rDate):
            pdebug("Downloading data from rDate to toDate")
            temp_data = downloadData(symbol,  rDate, toDate, freq)
            temp_data = raw_data.append(temp_data.tail(-1))
#            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")
        elif (fromDate < lDate ) and (toDate > rDate):
            pdebug("Downloading data from fromDate to lDate")
            temp_data = downloadData(symbol,  fromDate, lDate, freq)
            temp_data = temp_data.append(raw_data.tail(-1))
            logging.info("Downloading data from rDate to toDate")
            temp_data2 = downloadData(symbol,  rDate, toDate, freq)
            temp_data = temp_data.append(temp_data2.tail(-1))
#            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")

    except Exception as e:
        pdebug(e)
        temp_data = downloadData(symbol, fromDate, toDate, freq)
    finally:
        #temp_data.to_hdf(temp_file, key=key, mode="a")
        temp_file.close()
        
        cache_lock.release()
        return temp_data[(temp_data.index >= fromDate) & (temp_data.index <= toDate)]
    
def portfolioDownload(stocklist, toDate):
    stocklist_df = pd.DataFrame()
    for index, row in stocklist.iterrows():
        symbol = row[0]
        pinfo("Downloading data for: "+symbol)
        temp_data = getData(symbol,  toDate - dt.timedelta(days = 5), toDate)
        temp_data['symbol'] = symbol
        temp_data.set_index(['symbol',temp_data.index], inplace=True)
        #print(temp_data)
        stocklist_df = stocklist_df.append(temp_data)
    
    #print(stocklist_df)
    return stocklist_df



import json

oath_resp_msg = json.loads(
'''{
  "status": "success",
  "data": {
    "user_id": "XX000",
    "user_name": "Kite Connect",
    "user_shortname": "Kite",
    "email": "kite@kite.trade",
    "user_type": "investor",
    "broker": "ZERODHA",
    "exchanges": [
      "MCX",
      "BSE",
      "NSE",
      "BFO",
      "NFO",
      "CDS"
    ],
    "products": [
      "BO",
      "CNC",
      "CO",
      "MIS",
      "NRML"
    ],
    "order_types": [
      "LIMIT",
      "MARKET",
      "SL",
      "SL-M"
    ],
    "api_key": "xxxxxx",
    "access_token": "yyyyyy",
    "public_token": "zzzzzz",
    "refresh_token": null,
    "login_time": "2018-01-01 16:15:14",
    "avatar_url": null
  }
}'''
)

user_profile_resp = json.loads(
'''{
  "status": "success",
  "data": {
    "user_type": "investor",
    "email": "kite@kite.trade",
    "user_name": "Kite Connect",
    "user_shortname": "Kite",
    "broker": "ZERODHA",
    "exchanges": [
      "MCX",
      "BSE",
      "NSE",
      "BFO",
      "NFO",
      "CDS"
    ],
    "products": [
      "BO",
      "CNC",
      "CO",
      "MIS",
      "NRML"
    ],
    "order_types": [
      "LIMIT",
      "MARKET",
      "SL",
      "SL-M"
    ]
  }
}
'''
)

fund_margins_resp_msg = json.loads('''{
  "status": "success",
  "data": {
    "equity": {
      "enabled": true,
      "net": 24966.7493,
      "available": {
        "adhoc_margin": 0,
        "cash": 25000,
        "collateral": 0,
        "intraday_payin": 0
      },
      "utilised": {
        "debits": 33.2507,
        "exposure": 0,
        "m2m_realised": -0.25,
        "m2m_unrealised": 0,
        "option_premium": 0,
        "payout": 0,
        "span": 0,
        "holding_sales": 0,
        "turnover": 0
      }
    },
    "commodity": {
      "enabled": true,
      "net": 25000,
      "available": {
        "adhoc_margin": 0,
        "cash": 25000,
        "collateral": 0,
        "intraday_payin": 0
      },
      "utilised": {
        "debits": 0,
        "exposure": 0,
        "m2m_realised": 0,
        "m2m_unrealised": 0,
        "option_premium": 0,
        "payout": 0,
        "span": 0,
        "holding_sales": 0,
        "turnover": 0
      }
    }
  }
}''')

holdings_resp_msg = json.loads('''{
  "status": "success",
  "data": [{
    "tradingsymbol": "ABHICAP",
    "exchange": "BSE",
    "isin": "INE516F01016",
    "quantity": 1,
    "t1_quantity": 1,

    "average_price": 94.75,
    "last_price": 93.75,
    "pnl": -100.0,

    "product": "CNC",
    "collateral_quantity": 0,
    "collateral_type": null
  }, {
    "tradingsymbol": "AXISBANK",
    "exchange": "NSE",
    "isin": "INE238A01034",
    "quantity": 1,
    "t1_quantity": 0,

    "average_price": 475.0,
    "last_price": 432.55,
    "pnl": -42.50,

    "product": "CNC",
    "collateral_quantity": 0,
    "collateral_type": null
  }]
}''')


positions_resp_msg = json.loads('''{
  "status": "success",
  "data": {
    "net": [{
      "tradingsymbol": "NIFTY15DEC9500CE",
      "exchange": "NFO",
      "instrument_token": 41453,
      "product": "NRML",

      "quantity": -100,
      "overnight_quantity": -100,
      "multiplier": 1,

      "average_price": 3.475,
      "close_price": 0.75,
      "last_price": 0.75,
      "value": 75.0,
      "pnl": 272.5,
      "m2m": 0.0,
      "unrealised": 0.0,
      "realised": 0.0,

      "buy_quantity": 0,
      "buy_price": 0,
      "buy_value": 0.0,
      "buy_m2m": 0.0,

      "day_buy_quantity": 0,
      "day_buy_price": 0,
      "day_buy_value": 0.0,

      "day_sell_quantity": 0,
      "day_sell_price": 0,
      "day_sell_value": 0.0,

      "sell_quantity": 100,
      "sell_price": 3.475,
      "sell_value": 347.5,
      "sell_m2m": 75.0
    }],
    "day": []
  }
}''')


order_book_resp_msg = json.loads('''{
  "status": "success",
  "data": [{
    "order_id": "151220000000000",
    "parent_order_id": "151210000000000",
    "exchange_order_id": null,
    "placed_by": "AB0012",
    "variety": "regular",
    "status": "REJECTED",

    "tradingsymbol": "ACC",
    "exchange": "NSE",
    "instrument_token": 22,
    "transaction_type": "BUY",
    "order_type": "MARKET",
    "product": "NRML",
    "validity": "DAY",

    "price": 0.0,
    "quantity": 75,
    "trigger_price": 0.0,

    "average_price": 0.0,
    "pending_quantity": 0,
    "filled_quantity": 0,
    "disclosed_quantity": 0,
    "market_protection": 0,

    "order_timestamp": "2015-12-20 15:01:43",
    "exchange_timestamp": null,

    "status_message": "RMS:Margin Exceeds, Required:0, Available:0",
    "tag": null,
    "meta": {}
  }]
}''')

order_history_resp_msg = json.loads('''{
  "status": "success",
  "data": [
    {
      "average_price": 0,
      "cancelled_quantity": 0,
      "disclosed_quantity": 0,
      "exchange": "NSE",
      "exchange_order_id": null,
      "exchange_timestamp": null,
      "exchange_update_timestamp": null,
      "filled_quantity": 0,
      "instrument_token": 1,
      "market_protection": 0,
      "order_id": "171222000539943",
      "order_timestamp": "2017-12-22 10:36:09",
      "order_type": "SL",
      "parent_order_id": null,
      "pending_quantity": 1,
      "placed_by": "ZQXXXX",
      "price": 130,
      "product": "MIS",
      "quantity": 1,
      "status": "PUT ORDER REQ RECEIVED",
      "status_message": null,
      "tag": null,
      "tradingsymbol": "ASHOKLEY",
      "transaction_type": "BUY",
      "trigger_price": 128,
      "validity": "DAY",
      "variety": "regular"
    },
    {
      "average_price": 0,
      "cancelled_quantity": 0,
      "disclosed_quantity": 0,
      "exchange": "NSE",
      "exchange_order_id": null,
      "exchange_timestamp": null,
      "filled_quantity": 0,
      "instrument_token": 54273,
      "market_protection": 0,
      "order_id": "171222000539943",
      "order_timestamp": "2017-12-22 10:36:09",
      "order_type": "SL",
      "parent_order_id": null,
      "pending_quantity": 1,
      "placed_by": "ZQXXXX",
      "price": 130,
      "product": "MIS",
      "quantity": 1,
      "status": "VALIDATION PENDING",
      "status_message": null,
      "tag": null,
      "tradingsymbol": "ASHOKLEY",
      "transaction_type": "BUY",
      "trigger_price": 128,
      "validity": "DAY",
      "variety": "regular"
    },
    {
      "average_price": 0,
      "cancelled_quantity": 0,
      "disclosed_quantity": 0,
      "exchange": "NSE",
      "exchange_order_id": null,
      "exchange_timestamp": null,
      "filled_quantity": 0,
      "instrument_token": 54273,
      "market_protection": 0,
      "order_id": "171222000539943",
      "order_timestamp": "2017-12-22 10:36:09",
      "order_type": "SL",
      "parent_order_id": null,
      "pending_quantity": 0,
      "placed_by": "ZQXXXX",
      "price": 130,
      "product": "MIS",
      "quantity": 1,
      "status": "REJECTED",
      "status_message": "RMS:Rule: Check circuit limit including square off order exceeds  for entity account-DH0490 across exchange across segment across product ",
      "tag": null,
      "tradingsymbol": "ASHOKLEY",
      "transaction_type": "BUY",
      "trigger_price": 128,
      "validity": "DAY",
      "variety": "regular"
    }
  ]
}''')


trades_list_resp_msg = json.loads('''{
    "status": "success",
    "data": [{
        "trade_id": "159918",
        "order_id": "151220000000000",
        "exchange_order_id": "511220371736111",

        "tradingsymbol": "ACC",
        "exchange": "NSE",
        "instrument_token": "22",

        "transaction_type": "BUY",
        "product": "MIS",
        "average_price": 100.98,
        "quantity": 10,

        "fill_timestamp": "2015-12-20 15:01:44",
        "exchange_timestamp": "2015-12-20 15:01:43"

    }]
}''')

order_trades_resp_msg = json.loads('''{
    "status": "success",
    "data": [{
        "trade_id": "159918",
        "order_id": "151220000000000",
        "exchange_order_id": "511220371736111",

        "tradingsymbol": "ACC",
        "exchange": "NSE",
        "instrument_token": "22",

        "transaction_type": "BUY",
        "product": "MIS",
        "average_price": 100.98,
        "quantity": 10,

        "fill_timestamp": "2015-12-20 15:01:44",
        "exchange_timestamp": "2015-12-20 15:01:43"

    }]
}''')


full_quote_resp_msg = json.loads('''{
  "status":"success",
  "data":{
    "NSE:INFY":{
      "instrument_token":408065,
      "timestamp":"2019-12-09 17:36:07",
      "last_trade_time":"2019-12-09 15:57:46",
      "last_price":717.25,
      "last_quantity":20,
      "buy_quantity":0,
      "sell_quantity":1915,
      "volume":6435865,
      "average_price":718.65,
      "oi":0,
      "oi_day_high":0,
      "oi_day_low":0,
      "net_change":0,
      "lower_circuit_limit":645.55,
      "upper_circuit_limit":788.95,
      "ohlc":{
        "open":716,
        "high":722.35,
        "low":714.25,
        "close":715.1
      },
      "depth":{
        "buy":[
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          }
        ],
        "sell":[
          {
            "price":717.25,
            "quantity":1915,
            "orders":26
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          },
          {
            "price":0,
            "quantity":0,
            "orders":0
          }
        ]
      }
    }
  }
}''')


ohlc_quote_resp_msg = json.loads('''{
    "status": "success",
    "data": {
        "BSE:SENSEX": {
            "instrument_token": 265,
            "last_price": 31606.48,
            "ohlc": {
                "open": 31713.5,
                "high": 31713.5,
                "low": 31586.53,
                "close": 31809.55
            }
        },
        "NSE:INFY": {
            "instrument_token": 408065,
            "last_price": 890.9,
            "ohlc": {
                "open": 900,
                "high": 900.3,
                "low": 890,
                "close": 901.9
            }
        },
        "NSE:NIFTY 50": {
            "instrument_token": 256265,
            "last_price": 9893.4,
            "ohlc": {
                "open": 9899.25,
                "high": 9911.9,
                "low": 9882.55,
                "close": 9952.2
            }
        }
    }
}''')

ltp_quote_resp_msg = json.loads('''{
    "status": "success",
    "data": {
        "BSE:SENSEX": {
            "instrument_token": 265,
            "last_price": 31606.48
        },
        "NSE:INFY": {
            "instrument_token": 408065,
            "last_price": 890.9
        },
        "NSE:NIFTY 50": {
            "instrument_token": 256265,
            "last_price": 9893.4
        }
    }
}''')


historical_candles_msg = json.loads('''{
    "status": "success",
    "data": {
        "candles": [
            ["2015-12-28T09:15:00+0530", 1386.4, 1388, 1381.05, 1385.1, 788],
            ["2015-12-28T09:16:00+0530", 1385.1, 1389.1, 1383.85, 1385.5, 609],
            ["2015-12-28T09:17:00+0530", 1385.5, 1387, 1385.5, 1385.7, 212],
            ["2015-12-28T09:18:00+0530", 1387, 1387.95, 1385.3, 1387.95, 1208],
            ["2015-12-28T09:19:00+0530", 1387, 1387.55, 1385.6, 1386.25, 716],
            ["2015-12-28T09:20:00+0530", 1386.95, 1389.95, 1386.95, 1389, 727],
            ["2015-12-28T09:21:00+0530", 1389, 1392.95, 1389, 1392.95, 291],
            ["2015-12-28T09:22:00+0530", 1392.95, 1393, 1392, 1392.95, 180],
            ["2015-12-28T09:23:00+0530", 1392.95, 1393, 1392, 1392.15, 1869],
            ["2016-01-01T13:22:00+0530", 1386.4, 1388, 1381.05, 1385.1, 788],
            ["2016-01-01T13:23:00+0530", 1385.1, 1389.1, 1383.85, 1385.5, 613],
            ["2016-01-01T13:24:00+0530", 1385.5, 1387, 1385.5, 1385.7, 212],
            ["2016-01-01T13:25:00+0530", 1387, 1387.95, 1385.3, 1387.95, 1208],
            ["2016-01-01T13:26:00+0530", 1387, 1387.55, 1385.6, 1386.25, 716],
            ["2016-01-01T13:27:00+0530", 1386.95, 1389.95, 1386.95, 1389, 727],
            ["2016-01-01T13:28:00+0530", 1389, 1392.95, 1389, 1392.95, 291],
            ["2016-01-01T13:29:00+0530", 1392.95, 1393, 1392, 1392.95, 180],
            ["2016-01-01T13:30:00+0530", 1392.95, 1393, 1392, 1392.15, 1869]
        ]
    }
}''')

###############################################
######### Kite Connect Wrappers ###############
##############################################

from talib import MACD, MACDEXT, RSI, BBANDS, MACD, AROON, STOCHF, ATR, OBV, ADOSC, MINUS_DI, PLUS_DI, ADX, EMA, SMA
from talib import LINEARREG, BETA, LINEARREG_INTERCEPT, LINEARREG_SLOPE, STDDEV, TSF, ADOSC, VAR, ROC
from talib import CDLABANDONEDBABY, CDL3BLACKCROWS,CDLDOJI, CDLDOJISTAR, CDLDRAGONFLYDOJI,CDLENGULFING,CDLEVENINGDOJISTAR,CDLEVENINGSTAR, CDLGRAVESTONEDOJI, CDLHAMMER, CDLHANGINGMAN,CDLHARAMI,CDLHARAMICROSS,CDLINVERTEDHAMMER,CDLMARUBOZU,CDLMORNINGDOJISTAR,CDLMORNINGSTAR,CDLSHOOTINGSTAR,CDLSPINNINGTOP,CDL3BLACKCROWS, CDL3LINESTRIKE, CDLKICKING

import pandas as pd
#import numpy as np
#import tables
import datetime as dt
#import logging

#import matplotlib.pyplot as plt
#import seaborn as sns
#import plotly.graph_objs as go
#from plotly import tools
#from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

#from kiteconnect import KiteConnect
#from kiteconnect import KiteTicker
#import platform
#from selenium import webdriver
#import re
#import os
#from multiprocessing import Process
#import gc
#import warnings
#import os
#from multiprocessing import Process
#import warnings
#warnings.filterwarnings('ignore')

nifty50 = pd.read_csv("data/ind_nifty50list.csv")
niftynext50 = pd.read_csv("data/ind_niftynext50list.csv")
midcap50 = pd.read_csv("data/ind_niftymidcap50list.csv")

downloadlist = nifty50['Symbol']
industry = niftynext50['Industry'].unique()

toTick = lambda x,n=5: np.round((np.floor(x *100)+n-1)/n)*n/100

KiteAPIKey = "b2w0sfnr1zr92nxm"
KiteAPISecret = "jtga2mp2e5fn29h8w0pe2kb722g3dh1q"

holiday = pd.DataFrame([dt.datetime(2019,3,4),
dt.datetime(2019,3,21),
dt.datetime(2019,4,17),
dt.datetime(2019,4,19),
dt.datetime(2019,4,29),
dt.datetime(2019,5,1),
dt.datetime(2019,6,5),
dt.datetime(2019,8,12),
dt.datetime(2019,8,15),
dt.datetime(2019,9,10)])


isholiday = lambda mydt: ((holiday == mydt).any() == True)[0] or mydt.weekday() == 5 or mydt.weekday() == 6

def getFromDate(todate,  days = 1):
    tmp = todate.weekday()
    if tmp == 0:
        days = days + 2
    elif tmp >4:
        days = days + tmp - 5
    
    days = days + 1
    
    
    fromdate = todate - dt.timedelta(days=days)
    
    adj = holiday[(holiday > fromdate)&(holiday<todate)].dropna().shape[0]
    fromdate = fromdate - dt.timedelta(days=adj)
    return fromdate


#logging.critical("BUY"+symbol)
def buy_slm(symbol, price, trigger,quantity=1): 
    logger.info('%12s'%"BUY SLM: "+symbol+", price: "+str('%0.2f'%price)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
    
    if papertrade:
        return
    
    try:
        order_id = kite.place_order(tradingsymbol=symbol,
                                exchange=kite.EXCHANGE_NSE,
                                transaction_type=kite.TRANSACTION_TYPE_BUY,
                                quantity=quantity,
                                order_type=kite.ORDER_TYPE_SLM,
                                product=kite.PRODUCT_MIS,
                                trigger_price=round(trigger,1),
                                #stoploss=round(stoploss,1),
                                #price=price,
                                variety=kite.VARIETY_REGULAR
                                )
        logger.info("Order placed. ID is: {}".format(order_id))
    except Exception as e:
        logger.info("Order placement failed: {}".format(e.message))
        
def sell_slm(symbol, price, trigger, quantity=1):
    
    logger.info('%12s'%"SELL SLM: "+symbol+", price: "+str('%0.2f'%price)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
       
    if papertrade:
         return
    try:
        order_id = kite.place_order(tradingsymbol=symbol,
                            exchange=kite.EXCHANGE_NSE,
                            transaction_type=kite.TRANSACTION_TYPE_SELL,
                            quantity=quantity,
                            order_type=kite.ORDER_TYPE_SLM,
                            product=kite.PRODUCT_MIS,
                            trigger_price=round(trigger,1),
                            #price=price,
                            variety=kite.VARIETY_REGULAR)
        logger.info("Order placed. ID is: {}".format(order_id))
    except Exception as e:
        logger.info("Order placement failed: {}".format(e.message))

def buy_bo(symbol, price, trigger, stoploss, squareoff, quantity=1, tag="bot"): 
    logger.info('%12s'%"BUY BO: "+symbol+", price: "+str('%0.2f'%price)+", squareoff: "+str('%0.2f'%squareoff)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
    if papertrade:
        return
    
    try:
        order_id = kite.place_order(tradingsymbol=symbol, exchange=kite.EXCHANGE_NSE, transaction_type=kite.TRANSACTION_TYPE_BUY,
                        order_type=kite.ORDER_TYPE_LIMIT, product=kite.PRODUCT_MIS, variety=kite.VARIETY_BO, 
                                quantity=quantity, trigger_price=trigger, price=price,
                                squareoff=squareoff,  stoploss=stoploss, tag=tag )
        logger.info("Order placed. ID is: {}".format(order_id))
    except Exception as e:
        logger.info("Order placement failed: {}".format(e.message))



def sell_bo(symbol, price, trigger, stoploss, squareoff, quantity=1, tag="bot"): 
    logger.info('%12s'%"SELL BO: "+symbol+", price: "+str('%0.2f'%price)+", squareoff: "+str('%0.2f'%squareoff)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
    if papertrade:
        return
    
    try:
        order_id = kite.place_order(tradingsymbol=symbol, exchange=kite.EXCHANGE_NSE, transaction_type=kite.TRANSACTION_TYPE_SELL,
                                order_type=kite.ORDER_TYPE_LIMIT, product=kite.PRODUCT_MIS, variety=kite.VARIETY_BO,
                                quantity=quantity, trigger_price=trigger, price=price,
                                stoploss=stoploss, squareoff=squareoff,  tag=tag )
        logger.info("Order placed. ID is: {}".format(order_id))
    except Exception as e:
        logger.info("Order placement failed: {}".format(e.message))
        
def getOrders():    
    # Fetch all orders
    return pd.DataFrame(kite.orders())

def cancelOrder(orderId):
    if papertrade:
        logging.critical("In Paper Trade Mode: Order cancellation not possible")
        return
    
    try:
        kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=orderId, parent_order_id=None)    
    except Exception as e:
        logger.info("Order Cancellation failed: {}".format(e.message))
        
def squareoff(symbol=None, tag="bot"):
    logger.info('%12s'%"Squareoff: "+symbol)
    if papertrade:
        return
    
    orders_df = pd.DataFrame(kite.orders())
    if symbol != None:
        open_orders = orders_df[(orders_df['tradingsymbol']==symbol) & (orders_df['status'] == 'TRIGGER PENDING')  & (orders_df['tag'] == tag)]
    else:
        open_orders = orders_df[(orders_df['status'] == 'TRIGGER PENDING')  & (orders_df['tag'] == tag)]
        
    for index, row in open_orders.iterrows():
        print(row.order_id, row.parent_order_id)
        #kite.exit_order(variety=kite.VARIETY_AMO, order_id=row.order_id, parent_order_id=row.parent_order_id)
        kite.exit_order(variety=kite.VARIETY_BO, order_id=order_id, parent_order_id=parent_order_id)

        
def initTrade(ws):
    ws.prevtimeStamp = dt.datetime.now() - dt.timedelta(minutes=10)
    toDate = dt.datetime.now()
    
    ws.tradebook_df = pd.DataFrame()
    
    for symbol in portfolio[0]:
        temp_df = pd.DataFrame(data=[algoTrade(symbol)], index=[symbol], columns=['symbol'])
        ws.tradebook_df = ws.tradebook_df.append(temp_df)
        
    #TODO: Convert to multistock handling
    #symbol = portfolio[0].iloc[-1]
    #ws.a = algoTrade(symbol)
    
    ws.LiveStream = pd.DataFrame()
    ws.LiveStreamOHLC = pd.DataFrame()
    ws.LiveStreamOHLC = portfolioDownload(portfolio, toDate) 
    
def ticksHandler(ws, ticks):
    #timeStamp = dt.datetime.now().replace(second=0, microsecond=0)
    tick_df = pd.DataFrame(ticks)
    
    try:
        #tick_df.loc[tick_df['timestamp'].isna(), 'timestamp'] = timeStamp
        tick_df = tick_df[['timestamp','instrument_token','last_price','volume']]
        tick_df.instrument_token = tick_df.instrument_token.apply(EQSYMBOL)
        tick_df.columns = ['date','symbol','price','volume']
        tick_df.set_index(['symbol','date'], inplace=True)
        
        timeStamp = tick_df.index[0][-1].to_pydatetime()
        
    except  Exception as e:
        logging.debug("Exception: ticksHandler: "+str(e)+str(tick_df))
        
    if( (timeStamp - ws.prevtimeStamp) >= dt.timedelta(minutes=1)):
        ws.prevtimeStamp = timeStamp
        resample(ws)
    
    ws.LiveStream = ws.LiveStream.append(tick_df)
    
def orderNotification(ws,data):
    #logger.debug(data)
    order_df = pd.DataFrame.from_dict(data, orient='index')

    symbol = order_df.loc['tradingsymbol'][0]
    
    ws.tradebook_df.loc[symbol,'symbol'].update_order(order_df)
    #logger.debug(order_df)


def on_ticks(ws, ticks):
    # Callback to receive ticks.
    #logging.debug("Ticks: {}".format(ticks))
    #ticksHandler(ws, ticks)
    notification_despatcher(ws, ticks)


def on_connect(ws, response):
    initTrade(ws)
    pdebug(portfolioToken)
    # Callback on successful connect.
    # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
    #ws.subscribe(portfolioToken)

    ws.subscribe(portfolioToken)
    
    # Set RELIANCE to tick in `full` mode.
    # MODE_LTP, MODE_QUOTE, or MODE_FULL

    ws.set_mode(ws.MODE_FULL, portfolioToken)
    #ws.set_mode(ws.MODE_FULL, [225537]) 
    #ws.set_mode(ws.MODE_LTP, [225537, 3861249]) 
    #ws.set_mode(ws.MODE_MODE_QUOTE, [2714625,779521]) 

def on_close(ws, code, reason):
    # On connection close stop the main loop
    # Reconnection will not happen after executing `ws.stop()`
    ws.stop()

def on_order_update(ws, data):
    #logger.info("New Order Update")
    #orderNotification(ws,data)
    notification_despatcher(ws,data)