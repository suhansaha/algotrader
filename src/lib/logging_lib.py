#setup logging
import logging
#logging.basicConfig(format='%(asctime)s:%(levelname)s:\t%(message)s', level=logging.DEBUG, datefmt='%m-%d %H:%M:%S')
#logging.basicConfig(format='%(levelname)s:\t%(message)s', datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('freedom')
logger.setLevel(logging.WARNING)
loggerT = logging.getLogger('trade')
loggerT.setLevel(25)

# Trade handlers
t_handler = logging.StreamHandler()
t_handler.setLevel(25)
t_format = logging.Formatter('TRADE: %(message)s')
t_handler.setFormatter(t_format)
loggerT.addHandler(t_handler)

c_handler = logging.StreamHandler()
c_format = logging.Formatter('%(levelname)s:\t%(message)s')
c_handler.setLevel(logging.DEBUG)
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

#f_handler = logging.FileHandler('file.log')
#f_handler.setLevel(logging.ERROR)

# Create formatters and add it to handlers
#f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#f_handler.setFormatter(f_format)

# Add handlers to the logger
#logger.addHandler(f_handler)


pdebug = lambda x: logger.debug(x)
pinfo = lambda x: logger.info(x)
perror = lambda x: logger.error(x)
pexception = lambda x: logger.critical(x)
pwarning = lambda x: logger.warning(x)
logtrade = lambda x: loggerT.log(25, x)

#DEBUG_LEVELV_NUM = 9 
#logging.addLevelName(DEBUG_LEVELV_NUM, "DEBUGV")
#def debugv(self, message, *args, **kws):
#    if self.isEnabledFor(DEBUG_LEVELV_NUM):
#        # Yes, logger takes its '*args' as 'args'.
#        self._log(DEBUG_LEVELV_NUM, message, args, **kws) 
#logging.Logger.debugv = debugv

#CRITICAL: 50
#ERROR: 40
#WARNING: 30
#INFO: 20
#DEBUG: 10
#NOTSET: 0