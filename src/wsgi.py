from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

pinfo("================================")
pinfo("***   Starting New Session   ***")
pinfo("================================")

freedom = threadManager("freedom", ["freedom_init"], [freedom_init])

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run()