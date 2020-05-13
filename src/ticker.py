from lib.multitasking_lib import *

logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    tick_manager = threadManager(cache_id, ["kite_ticker_handler"], [kite_ticker_handler])
    live_cache = cache_state(cache_id)