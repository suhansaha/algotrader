from app import app
#!/usr/bin/python
from lib.multitasking_lib import *
logger.setLevel(logging.INFO)

# Live Order Handler
live_cache = cache_state(cache_id)
live_cache.xtrim('notificationQueuelivenew',0,False)
order_manager = threadManager(cache_id, ["order_handler","order_notification_handler"], [order_handler, order_notification_handler])

# Live Trading Manager
instruments_df = pd.read_hdf('data/instruments.h5',key='instruments')
eq_nse = instruments_df.loc[(instruments_df['exchange']=='NSE') & (instruments_df['segment']=='NSE')  & (instruments_df['instrument_type']=='EQ'), ['instrument_token','tradingsymbol']]
redis_conn.hmset('eq_token',eq_nse.set_index('instrument_token').transpose().to_dict(orient='records')[0])
redis_conn.hmset('eq_token',eq_nse.set_index('tradingsymbol').transpose().to_dict(orient='records')[0])
redis_conn.set('last_id_msg'+cache_id,0)
live_manager = threadManager(cache_id, ["ohlc_tick_handler"], [ohlc_tick_handler])

# Backtest Manager
live_cache.xtrim('msgBufferQueue'+cache_type,0,False)
live_cache.set('last_id_msg'+cache_type, 0)
backtest_manager = threadManager(cache_type, ["kite_simulator","ohlc_tick_handler","order_handler"], [kite_simulator, ohlc_tick_handler, order_handler])

if __name__ == "__main__":
    app.run(debug=False)