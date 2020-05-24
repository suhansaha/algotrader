from lib.multitasking_lib import *

live_cache = cache_state(cache_id)
live_cache.xtrim('notificationQueuelivenew',0,False)

if __name__ == "__main__":
    order_manager = threadManager(cache_id, ["order_handler","order_notification_handler"], [order_handler, order_notification_handler])