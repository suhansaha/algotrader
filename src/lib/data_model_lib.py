import pandas as pd
import numpy as np
from redis import Redis
from datetime import datetime, timedelta
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, create_engine, select, and_
from sqlalchemy.orm import sessionmaker
import os
database_url = os.environ.get('DATABASE_URL')

engine = create_engine(database_url, echo=False)
#Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()
conn = session.bind
       
to_tick = lambda df, delta: pd.DataFrame( data = df.values, index =  df.index+timedelta(seconds=delta), columns=['ltp']  )
def ohlc_to_tick(df):
    ohlc_df = pd.DataFrame()
    #pinfo(df)
    tmp_df = to_tick(df['open'], 1)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['close'], 50)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['high'], 10)
    ohlc_df = ohlc_df.append(tmp_df)
    tmp_df = to_tick(df['low'], 20)
    ohlc_df = ohlc_df.append(tmp_df)

    #pinfo(ohlc_df)
    return ohlc_df

def resample(df, freq = '1T'):
    tmp_df = pd.DataFrame()    
    tmp_df = df.resample(freq,label='left').agg(['last','max','min','first']).dropna()
    tmp_df.columns = ['close', 'high', 'low', 'open']
    #print(tmp_df.head(5))
    return tmp_df


# Wrapper for Redis cache
class cache_state(Redis):
    def __init__(self, postfix='backtest'):
        Redis.__init__(self, host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
        pdebug5("Cache Pointing to: "+postfix)
        self.hash_postfix = postfix
        
    def add(self, key, reset=False):
        hash_key = key+self.hash_postfix
        
        if self.hlen(hash_key) == 0 or reset == True:
            pinfo('Reset Cache for: {}'.format(hash_key))
            self.hmset(hash_key, {'stock':'', 'qty':0, 'SL %':0.0, 'TP %':0.0, 'amount':0,'price':0.0,'P&L':0.0,'P&L %':0.0,'Total P&L':0.0,'Total P&L %':0.0,
                                       'low':0.0,'sl':0.0,'ltp':0.0,'ltp %':0.0,'tp':0.0,'high':0.0,'last_processed':0,
                                       'state':'INIT','mode':'PAUSE','algo':'', 'freq':'1T','hdf_freq':'minute', 'order_id':0})
            # Trade Log: [{timestamp, buy, sale, amount, profit, cum_profit, W_L, Mode}]
            # Amount: -ve for Buy, +ve for sale; W_L: +1 for Win, -1 for Loss; Mode: EN|EX|SL|TP|F
            self.set(hash_key+'Trade', pd.DataFrame().to_json(orient='columns'))
            self.set(hash_key+'OHLC', pd.DataFrame().to_json(orient='columns'))
            self.set(hash_key+'TICK', pd.DataFrame().to_json(orient='columns'))
            with pd.HDFStore('data/'+hash_key+'TICK', mode="w") as f:
                pd.DataFrame().to_hdf(f, format='t', key=hash_key+'TICK')
            with pd.HDFStore('data/'+hash_key+'Trade', mode="w") as f:
                pd.DataFrame().to_hdf(f, format='t', key=hash_key+'Trade')
        self.sadd(self.hash_postfix, key)

        pinfo('{}=>{}'.format(hash_key, self.hgetall(hash_key)))
 
    
    def pushCache(self, hash_key, df):
        #cache_buff = pd.read_json(self.get(hash_key))
        #pinfo(cache_buff.tail())
        #pinfo(df.head())
        #cache_buff = cache_buff.append(df)
        #try:
        #    self.setCache(hash_key, cache_buff)
        #except:
        #    pass
        with pd.HDFStore('data/'+hash_key, mode="r+") as f:
            df.to_hdf(f,append=True, mode='r+', format='t', key=hash_key)

    def setCache(self, hash_key, df):
        with pd.HDFStore('data/'+hash_key, mode="w") as f:
            df.to_hdf(f, format='t', key=hash_key)

            #self.set(hash_key, df.to_json(orient='columns'))

    def getTrades(self, key):
        #hash_key = key+self.hash_postfix+'Trade'
        #df = pd.read_json(self.get(hash_key))
        #with pd.HDFStore('data/'+hash_key, mode="r", key=hash_key) as f:
        #    df = pd.read_hdf(f)

        job_id = self.getValue(key,'job_id')
        stock = self.getValue(key,'stock')
        job = session.query(Jobs).filter(Jobs.job_id==job_id).first().id

        trades = session.query(Trades).filter(Trades.job_id==job)

        tmp_df = pd.read_sql(select([Trades]).where(and_(Trades.job_id==job, Trades.stock==stock)), conn)

        tmp_df["buy"] = tmp_df[tmp_df['buy_or_sell']=='B'].price
        tmp_df["sell"] = tmp_df[tmp_df['buy_or_sell']=='S'].price
        tmp_df1 = tmp_df.drop(columns=['id', 'stock', 'price', 'qty', 'buy_or_sell',
            'order_id', 'job_id'])
        tmp_df1.columns = ['date','mode','buy','sell']
        tmp_df1 = tmp_df1.set_index('date')
        tmp_df1.index = pd.to_datetime(tmp_df1.index)
        return tmp_df1
    
    def pushTrade(self, key, df):
        hash_key = key+self.hash_postfix+'Trade'
        self.pushCache(hash_key, df)

    def getOHLC(self, key, freq='1D'):
        freq = self.getValue(key, 'freq')

        #hash_key = key+self.hash_postfix+'OHLC'
        hash_key1 = key+self.hash_postfix+'TICK'
        #df = pd.read_json(self.get(hash_key))
        #df1 =  pd.read_json(self.get(hash_key1))

        with pd.HDFStore('data/'+hash_key1, mode="r", key=hash_key1) as f:
            df1 = pd.read_hdf(f)

        tmp_df = df1
        if not tmp_df.empty:
            resample_df = resample(tmp_df['ltp'], freq)
            return resample_df
        
        return tmp_df
    
    def setOHLC(self, key, df):
        # Overwrites existing content
        #self.setCache(key+self.hash_postfix+'OHLC', df)
        self.setCache(key+self.hash_postfix+'TICK', ohlc_to_tick(df))
        return df

    def pushTICK(self, key, df):
        #pdebug1("{}=>{}".format(key,df))
        self.pushCache(key+self.hash_postfix+'TICK', df)
        return df

    def pushOHLC(self, key, df):
        #self.pushCache(key+self.hash_postfix+'OHLC', df)
        self.pushCache(key+self.hash_postfix+'TICK', ohlc_to_tick(df))
        
    def getValue(self, key='', field=''):
        hash_key = key+self.hash_postfix
        if key == '':
            df = pd.DataFrame()
            for key in self.smembers(self.hash_postfix):
                hash_key = key+self.hash_postfix
                tmp_df = pd.DataFrame([self.hgetall(hash_key)])
                df = df.append(tmp_df, ignore_index=True)
            return df
            
        elif field == '': # return all
            return pd.DataFrame([self.hgetall(hash_key)])
        else:
            return self.hget(hash_key,field)
    
    def setValue(self, key, field, value):
        hash_key = key+self.hash_postfix
        return self.hset(hash_key, field, value)
   
    def remove(self, key=''):
        if key == '':
            for key in self.smembers(self.hash_postfix):
                hash_key = key+self.hash_postfix
                for field in self.hkeys(hash_key):
                    self.hdel(hash_key, field)

                self.srem(self.hash_postfix, key)
            
        else:
            hash_key = key+self.hash_postfix
            for field in self.hkeys(hash_key):
                self.hdel(hash_key, field)

            self.srem(self.hash_postfix, key)
            
    def reset(self, key=''):
        if key == '':
            for key in self.smembers(self.hash_postfix):
                self.add(key,True)
        else:
            self.add(key,True)
            
    def getKeys(self):
        return self.smembers(self.hash_postfix)


# Postgres
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

db = SQLAlchemy()

class User(UserMixin, db.Model, Base):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(512))
    name = db.Column(db.String(100))
    mobile = db.Column(db.String(25), unique=True)
    broker_id = db.Column(db.String(25), unique=True)
    broker_name = db.Column(db.String(50))
    api_key = db.Column(db.String(512), unique=True)
    api_secret = db.Column(db.String(512), unique=True)
    api_token = db.Column(db.String(512), unique=True)
    session_id = db.Column(db.String(512), unique=True)
    algos = relationship("Algos", back_populates="users")
    is_active = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    portfolios = relationship("Portfolios", back_populates="users")
    jobs = relationship("Jobs", back_populates="users")


class Algos(db.Model, Base):
    __tablename__ = 'algos'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    title = db.Column(db.String(100))
    algo = db.Column(db.Text())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    users = relationship("User", back_populates="algos")


class Portfolios(db.Model, Base):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    title = db.Column(db.String(100), index=True)
    stock = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    users = relationship("User", back_populates="portfolios")


class Jobs(db.Model, Base):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    job_id = db.Column(db.String(100), unique=True)
    job_type = db.Column(db.String(25))
    job_status = db.Column(db.String(25))
    job_info = db.Column(db.Text())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    users = relationship("User", back_populates="jobs")
    trades = relationship("Trades", back_populates="jobs")


class Trades(db.Model, Base):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    timestamp  = db.Column(db.String(100))
    stock = db.Column(db.String(20), index=True)
    price = db.Column(db.Float)
    qty = db.Column(db.Float)
    buy_or_sell = db.Column(db.String(20))
    en_or_ex = db.Column(db.String(20))
    order_id = db.Column(db.String(100))
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), index=True)
    jobs = relationship("Jobs", back_populates="trades")


class OHLC(db.Model, Base):
    __tablename__ = 'ohlc'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    stock = db.Column(db.String(20), index=True)
    timestamp  = db.Column(db.Integer)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Float)



def update_algo_db(name, algo_str, user_id):
    algo = Algos.query.filter(Algos.title==name, Algos.user_id==user_id).first()
    if algo == None:
        new_algo = Algos(title=name, algo=algo_str, user_id=user_id)
        db.session.add(new_algo)
        db.session.commit()
    else:
        algo.algo = algo_str
        db.session.commit()

def get_algo_list(user_id):
    algos = Algos.query.filter(Algos.user_id==user_id).all()
    return [alg.title for alg in algos]

#conn = session.bind

def update_trade_log(t, s, p, q, b, e, j):

    #pinfo("update_trade_log # 1")
    job = session.query(Jobs).filter(Jobs.job_id==j).first()
    #pinfo(job.job_id)
    #pdebug("{},{},{},{},{},{},{}".format(t,s,p,q,b,e,j))
    job.trades.append(Trades(timestamp=t, stock=s, price=p, qty=q, buy_or_sell=b, en_or_ex=e, order_id=""))
    #session.add(trade)
    try:
        session.commit()
        #pinfo("update_trade_log # 2")
    except Exception as e:
        pinfo(e)

