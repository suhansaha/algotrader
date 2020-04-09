from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

#orderManager = threadManager("orderManager", ["order_handler"], [order_handler]) 
#tradeManager = threadManager("tradeManager", ["order", "trade"], [hello_world1, hello_world2])
backtestManager = threadManager("backtestManager", ["backtest"], [backtest_handler])

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run()