#setup logging
import logging
#logging.basicConfig(format='%(asctime)s:%(levelname)s:\t%(message)s', level=logging.DEBUG, datefmt='%m-%d %H:%M:%S')
logging.basicConfig(format='%(levelname)s:\t%(message)s', level=logging.DEBUG, datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('simple_example')
#logger.setLevel(logging.DEBUG)

pdebug = lambda x: logger.debug(x)
pinfo = lambda x: logger.info(x)
perror = lambda x: logger.error(x)
pexception = lambda x: logger.critical(x)
pwarning = lambda x: logger.warning(x)