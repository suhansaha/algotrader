from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, cache_id
from lib.data_model_lib import *
import pandas as pd
import datetime as dt
from threading import Lock
import sys

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



###################################################
### Kite Order functions                        ###
###################################################

def buy_limit(kite, symbol, price, quantity=1, tag='freedom_v2'): 
    pinfo("B Limit: {}[{}]=> {}".format(symbol, quantity, price))

    return
    try:
        order_id = kite.place_order(tradingsymbol=symbol,
                                exchange=kite.EXCHANGE_NSE,
                                transaction_type=kite.TRANSACTION_TYPE_BUY,
                                quantity=quantity,
                                order_type=kite.ORDER_TYPE_LIMIT,
                                product=kite.PRODUCT_MIS,
                                #trigger_price=round(trigger,1),
                                #stoploss=round(stoploss,1),
                                #trigger_price=round(price,1),
                                price=price,
                                variety=kite.VARIETY_REGULAR,
                                tag=tag
                                )
        pinfo("Order placed. ID is: {}".format(order_id))
        return order_id
    except:
        pinfo("Order placement failed: {}".format(sys.exc_info()[0]))
        return -1
        
def sell_limit(kite, symbol, price, quantity=1, tag='freedom_v2'):
    pinfo("S Limit: {}[{}]=> {}".format(symbol, quantity, price))

    return
    try:
        order_id = kite.place_order(tradingsymbol=symbol,
                            exchange=kite.EXCHANGE_NSE,
                            transaction_type=kite.TRANSACTION_TYPE_SELL,
                            quantity=quantity,
                            order_type=kite.ORDER_TYPE_LIMIT,
                            product=kite.PRODUCT_MIS,
                            #trigger_price=round(trigger,1),
                            #trigger_price=round(price,1),
                            price=price,
                            variety=kite.VARIETY_REGULAR,
                            tag=tag)
        pinfo("Order placed. ID is: {}".format(order_id))
        return order_id
    except:
        pinfo("Order placement failed: {}".format(sys.exc_info()[0]))
        return -1

def buy_bo(symbol, price, trigger, stoploss, squareoff, quantity=1, tag="bot"): 
  pinfo('%12s'%"BUY BO: "+symbol+", price: "+str('%0.2f'%price)+", squareoff: "+str('%0.2f'%squareoff)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
  
  try:
    order_id = kite.place_order(tradingsymbol=symbol, exchange=kite.EXCHANGE_NSE, transaction_type=kite.TRANSACTION_TYPE_BUY,
                    order_type=kite.ORDER_TYPE_LIMIT, product=kite.PRODUCT_MIS, variety=kite.VARIETY_BO, 
                            quantity=quantity, trigger_price=trigger, price=price,
                            squareoff=squareoff,  stoploss=stoploss, tag=tag )
    logger.info("Order placed. ID is: {}".format(order_id))
  except Exception as e:
    logger.info("Order placement failed: {}".format(e.message))



def sell_bo(symbol, price, trigger, stoploss, squareoff, quantity=1, tag="bot"): 
    pinfo('%12s'%"SELL BO: "+symbol+", price: "+str('%0.2f'%price)+", squareoff: "+str('%0.2f'%squareoff)+", stoploss: "+str('%0.2f'%stoploss)+", quantity: "+str(quantity))
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


def cancel_all(kite):
    orders_df = pd.DataFrame(kite.orders())
    
    orders_df = orders_df.loc[(orders_df['status']=='OPEN'), ['order_id','status','tradingsymbol','transaction_type','quantity']]
    for i, r in orders_df.iterrows():
            order_id = r['order_id']
            qty = r['quantity']
            transaction_type = 'SELL' if r['transaction_type'] == 'BUY' else 'BUY'
            cancelOrder(kite, order_id)
    
def cancel_order(kite, stocks=None):
    orders_df = pd.DataFrame(kite.orders())
    for stock in stocks:
        tmp_df = orders_df.loc[(orders_df['tradingsymbol']==stock) & (orders_df['status']=='OPEN'), ['order_id','status','tradingsymbol','transaction_type','quantity']]
        #print(tmp_df)
        for i, r in tmp_df.iterrows():
            order_id = r['order_id']
            qty = r['quantity']
            transaction_type = 'SELL' if r['transaction_type'] == 'BUY' else 'BUY'
            cancelOrder(kite, order_id)

def getOrders(kite):    
  # Fetch all orders
  pinfo(kite.orders())
  return pd.DataFrame(kite.orders())

def cancelOrder(kite, orderId):
    try:
        kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=orderId, parent_order_id=None)    
    except Exception as e:
        logger.info("Order Cancellation failed: {}".format(e.message))

#TODO: Modify this function for SLM     
def squareoff(symbol=None, tag="bot"):
  pinfo('%12s'%"Squareoff: "+symbol)

  orders_df = pd.DataFrame(kite.orders())
  if symbol != None:
    open_orders = orders_df[(orders_df['tradingsymbol']==symbol) & (orders_df['status'] == 'TRIGGER PENDING')  & (orders_df['tag'] == tag)]
  else:
    open_orders = orders_df[(orders_df['status'] == 'TRIGGER PENDING')  & (orders_df['tag'] == tag)]
      
  for index, row in open_orders.iterrows():
    pinfo(row.order_id, row.parent_order_id)
    kite.exit_order(variety=kite.VARIETY_BO, order_id=order_id, parent_order_id=parent_order_id)


