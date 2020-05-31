from app import app
#!/usr/bin/python
from lib.multitasking_lib import *
logger.setLevel(logging.INFO)

cache = cache_state(cache_type)
cache.set('done'+cache_type,1)

if __name__ == "__main__":
    app.run(debug=False)