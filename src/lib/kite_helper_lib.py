from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, cache_id
from lib.data_model_lib import *
import pandas as pd
import datetime as dt
from threading import Lock

#TODO: Replace with redis cache
def getInstruments(exchange='NSE'):
  instruments_df = pd.DataFrame(data=kite.instruments(exchange))
  instruments_df = instruments_df.set_index('tradingsymbol')
  return instruments_df

def downloadData(symbol="HDFC", fromDate= dt.datetime.now() - dt.timedelta(days = 1), toDate=dt.datetime.now(), freq="minute"):
  symbolToken = instruments_df.loc[symbol,'instrument_token']
  
  if type(symbolToken).__name__ == 'Series':
    symbolToken = symbolToken[symbol].values[0]
  
  pdebug5(freq)
  raw_data = pd.DataFrame(data=kite.historical_data(symbolToken, fromDate, toDate, freq, continuous=False))
  raw_data = raw_data.set_index('date').tz_localize(None)
  return raw_data

kite_cache_path = 'data/kite_cache_day.h5'
kite_cache_path = 'data/kite_cache.h5'
hdf_cache_lock = Lock()

def getData(symbol, fromDate, toDate, exchange="NSE", freq="minute", force=False, symbolToken=''):
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
    hdf_cache_lock.acquire()
    temp_file = pd.HDFStore(kite_cache_path, mode="r")
    rDate = temp_file.get(key).tail(1).index
    lDate = temp_file.get(key).head(1).index
    
    #temp_file.close()
    
    #print(fromDate,toDate, lDate, rDate)
    raw_data = pd.read_hdf(temp_file, key=key)

    if   (fromDate < lDate ) and (toDate <= rDate):
      pdebug5("Downloading data from fromDate to lDate")
      temp_data = downloadData(symbol,  fromDate, lDate, freq)
      temp_data = temp_data.append(raw_data.tail(-1))
  #            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")
    elif (fromDate >=lDate ) and (toDate <= rDate):
      pdebug5("Using cache: Not downloading data")
      temp_data = raw_data
    elif (fromDate >= lDate ) and (toDate > rDate):
      pdebug5("Downloading data from rDate to toDate")
      temp_data = downloadData(symbol,  rDate, toDate, freq)
      temp_data = raw_data.append(temp_data.tail(-1))
  #            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")
    elif (fromDate < lDate ) and (toDate > rDate):
      pdebug5("Downloading data from fromDate to lDate")
      temp_data = downloadData(symbol,  fromDate, lDate, freq)
      temp_data = temp_data.append(raw_data.tail(-1))
      pdebug5("Downloading data from rDate to toDate")
      temp_data2 = downloadData(symbol,  rDate, toDate, freq)
      temp_data = temp_data.append(temp_data2.tail(-1))
  #            temp_data.to_hdf("kite_data/kite_cache.h5", key=key, mode="a", format="table")

  except Exception as e:
    perror(e)
    temp_data = downloadData(symbol, fromDate, toDate, freq)
  finally:
    #temp_data.to_hdf(temp_file, key=key, mode="a")
    temp_file.close()
    
    hdf_cache_lock.release()
    return temp_data[(temp_data.index >= fromDate) & (temp_data.index <= toDate)]
    
def portfolioDownload(stocklist, toDate):
  stocklist_df = pd.DataFrame()
  for index, row in stocklist.iterrows():
    symbol = row[0]
    pdebug5("Downloading data for: "+symbol)
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
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
#import platform
#import re
#nifty50 = pd.read_csv("data/ind_nifty50list.csv")
#niftynext50 = pd.read_csv("data/ind_niftynext50list.csv")
#midcap50 = pd.read_csv("data/ind_niftymidcap50list.csv")

#downloadlist = nifty50['Symbol']
#industry = niftynext50['Industry'].unique()

#KiteAPIKey = "b2w0sfnr1zr92nxm"
#KiteAPISecret = "jtga2mp2e5fn29h8w0pe2kb722g3dh1q"

#TODO: Note required: Delete
def orderNotification(ws,data):
  #logger.debug(data)
  order_df = pd.DataFrame.from_dict(data, orient='index')
  symbol = order_df.loc['tradingsymbol'][0]
  ws.tradebook_df.loc[symbol,'symbol'].update_order(order_df)
  #logger.debug(order_df)