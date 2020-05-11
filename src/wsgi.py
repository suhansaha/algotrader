from app import app
#!/usr/bin/python
from lib.multitasking_lib import *

pinfo("================================")
pinfo("***   Starting New Session   ***")
pinfo("================================")

freedom = threadManager("freedom", ["freedom_init"], [freedom_init])
redis_conn.publish('freedom_initfreedom','backtest:start')

instruments_df = pd.read_hdf('data/instruments.h5',key='instruments')
eq_nse = instruments_df.loc[(instruments_df['exchange']=='NSE') & (instruments_df['segment']=='NSE')  & (instruments_df['instrument_type']=='EQ'), ['instrument_token','tradingsymbol']]
redis_conn.hmset('eq_token',eq_nse.set_index('instrument_token').transpose().to_dict(orient='records')[0])
redis_conn.hmset('eq_token',eq_nse.set_index('tradingsymbol').transpose().to_dict(orient='records')[0])

# Initializes multiple worker threads and AppServer
if __name__ == "__main__":
    app.run(debug=False)