from lib.multitasking_lib import *

live_cache = cache_state(cache_id)

live_cache.set('Kite_Status','closed')
live_cache.xtrim('msgBufferQueue'+cache_type,0,False)

if __name__ == "__main__":
    backtest_manager = threadManager(cache_type, ["kite_simulator","ohlc_tick_handler"], [kite_simulator, ohlc_tick_handler])