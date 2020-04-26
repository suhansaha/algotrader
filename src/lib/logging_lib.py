#setup logging
import logging
#logging.basicConfig(filemode='w+')
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

f_handler = logging.FileHandler('log/freedom.log', mode='w')
f_handler.setLevel(logging.DEBUG)
#f_format = logging.Formatter('%(levelname)s - %(message)s')
f_handler.setFormatter(c_format)


ft_handler = logging.FileHandler('log/freedom_trade.log', mode='w')
ft_handler.setLevel(logging.DEBUG)
ft_handler.setFormatter(t_format)

# Add handlers to the logger
logger.addHandler(f_handler)
loggerT.addHandler(ft_handler)


pdebug = lambda x: logger.debug(x)
pdebug1 = lambda x: logger.log(1, x) # Tick: Very heavy logging
pdebug5 = lambda x: logger.log(5, x) # Print dataframes
pinfo = lambda x: logger.info(x)
perror = lambda x: logger.error(x)
pexception = lambda x: logger.critical(x)
pwarning = lambda x: logger.warning(x)

from redis import Redis
cache = Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
def logtrade(x):
    try:
        msg_bug = cache.get('logMsg')
        msg_bug = msg_bug + '\n' + x
        cache.set('logMsg',msg_bug)
    except:
        pass
    finally:
        loggerT.log(25, x)

#logtrade = lambda x: loggerT.log(25, x)

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