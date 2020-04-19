from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

logger.setLevel(logging.INFO)
loggerT.setLevel(21)

pinfo("================================")
pinfo("***   Starting New Session   ***")
pinfo("================================")
#orderManager = threadManager("orderManager", ["order_handler"], [order_handler]) 
#tradeManager = threadManager("tradeManager", ["order", "trade"], [hello_world1, hello_world2])
freedom = threadManager("freedom_init", 
                ["backtest", "kite_simulator", "trade_handler", "order_handler"], 
                [backtest_handler, kite_simulator, trade_handler, order_handler])

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run()