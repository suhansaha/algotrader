from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

pinfo("================================")
pinfo("***   Starting New Session   ***")
pinfo("================================")

cache = cache_state(cache_type)
cache.set('done'+cache_type,1)

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run(debug=False)