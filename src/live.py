from lib.multitasking_lib import *

instruments_df = pd.read_hdf('data/instruments.h5',key='instruments')
eq_nse = instruments_df.loc[(instruments_df['exchange']=='NSE') & (instruments_df['segment']=='NSE')  & (instruments_df['instrument_type']=='EQ'), ['instrument_token','tradingsymbol']]
redis_conn.hmset('eq_token',eq_nse.set_index('instrument_token').transpose().to_dict(orient='records')[0])
redis_conn.hmset('eq_token',eq_nse.set_index('tradingsymbol').transpose().to_dict(orient='records')[0])
redis_conn.set('last_id_msg'+cache_id,0)

if __name__ == "__main__":
    live_manager = threadManager(cache_id, ["ohlc_tick_handler","order_notification_handler"], [ohlc_tick_handler, order_notification_handler])