import threading
from threading import Semaphore
import time
import pandas as pd
import math
from queue import Queue
from redis import Redis
import multiprocessing
import numpy as np
from lib.logging_lib import *
from lib.data_model_lib import *
import sys
import json
import ast
from datetime import datetime, timedelta
import time
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker

from lib.multitasking_lib import *

if __name__ == "__main__":
    live_manager = threadManager(cache_id, ["ohlc_tick_handler","order_handler"], [ohlc_tick_handler, order_handler])