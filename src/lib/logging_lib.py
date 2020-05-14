#setup logging
import logging
from redis import Redis
#logging.basicConfig(filemode='w+')
#logging.basicConfig(format='%(levelname)s:\t%(message)s', datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('freedom')
logger.setLevel(logging.DEBUG)

# Stream handlers
c_handler = logging.StreamHandler()
c_format = logging.Formatter('%(asctime)s %(levelname)s:\t%(message)s')
c_handler.setLevel(7)
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

logfile = 'freedom.log'

logger.debug(logfile)

# File handlers
f_handler = logging.FileHandler('log/'+logfile, mode='w')
f_handler.setLevel(7)
#f_format = logging.Formatter('%(levelname)s - %(message)s')
f_handler.setFormatter(c_format)
logger.addHandler(f_handler)

###### Logging trade ######
loggerT = logging.getLogger('trade')
loggerT.setLevel(25)

# LogTrade: Stream handlers
t_handler = logging.StreamHandler()
t_handler.setLevel(25)
t_format = logging.Formatter('TRADE: %(message)s')
t_handler.setFormatter(t_format)
loggerT.addHandler(t_handler)


# LogTrade: File handlers
ft_handler = logging.FileHandler('log/freedom_trade.log', mode='w')
ft_handler.setLevel(25)
ft_handler.setFormatter(t_format)
loggerT.addHandler(ft_handler)


pdebug = lambda x: logger.debug(x)
pdebug1 = lambda x: logger.log(1, x) # Tick: Very heavy logging
pdebug5 = lambda x: logger.log(5, x) # Print datadownload
pdebug7 = lambda x: logger.log(7, x) # Print flow of tick msg
pinfo = lambda x: logger.info(x)
perror = lambda x: logger.error(x)
pexception = lambda x: logger.critical(x)
pwarning = lambda x: logger.warning(x)

cache_type = "backtest_web"
cache_id = 'live'
redis_conn = Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
#def logtrade(x):
#    global cache_type
    #try:
    #    msg_bug = redis_conn.get('logMsg'+cache_type)
    #    msg_bug = msg_bug + '\n' + x
    #    redis_conn.set('logMsg'+cache_type,msg_bug)
    #except:
    #    pass
    #finally:
    #    loggerT.log(25, x)


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

# 7: test flow of packets