from lib.multitasking_lib import *

logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    live_manager = threadManager(cache_id, ["ohlc_tick_handler"], [ohlc_tick_handler])