from lib.multitasking_lib import *

logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    backtest_manager = threadManager(cache_type, ["kite_simulator","ohlc_tick_handler"], [kite_simulator, ohlc_tick_handler])