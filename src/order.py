from lib.multitasking_lib import *

if __name__ == "__main__":
    order_manager = threadManager(cache_id, ["order_handler"], [order_handler])