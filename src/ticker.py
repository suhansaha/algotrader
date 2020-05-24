from lib.multitasking_lib import *

if __name__ == "__main__":
    tick_manager = threadManager(cache_id, ["kite_ticker_handler"], [kite_ticker_handler])
    live_cache = cache_state(cache_id)

    live_cache.set('Kite_Status','closed')
    #live_cache.xtrim('msgBufferQueue'+cache_id,0,False)
    
    while True:
        if live_cache.get('Kite_Status') == 'connected':
            pinfo('Breaking INIT loop')
            #live_cache.publish('ohlc_tick_handler'+cache_id,'start')
            break
        live_cache.publish('kite_ticker_handler'+cache_id,'INIT')
        time.sleep(60)


