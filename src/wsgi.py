from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

logger.setLevel(logging.DEBUG)
#logger.setLevel(1)
loggerT.setLevel(21)

pinfo("================================")
pinfo("***   Starting New Session   ***")
pinfo("================================")

#freedom = threadManager("freedom_init", 
#                ["kite_simulator", "trade_handler", "order_handler"], 
#                [kite_simulator, trade_handler, order_handler])

freedom = threadManager("freedom", ["freedom_init"], [freedom_init])

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run()