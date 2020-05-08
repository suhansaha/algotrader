import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo, cache_type, redis_conn
from lib.algo_lib import *
from lib.data_model_lib import *

scatter = lambda df, key, title, c, fill='none', fillcolor="rgba(0,40,100,0.02)": go.Scatter(x=df.index.astype('str'), y=df[key], name=title, mode='lines', line=dict(color=c),showlegend=False, fill = fill, fillcolor=fillcolor)
bar =  lambda df, key, title, c: go.Bar(x=df.index.astype('str'), y=df[key], name=title, marker=dict(color=c),showlegend=False)

def plot_2_lines_1_bar(fig, df, d1, t1='', c1='black', d2=None, t2='', c2='red', d3=None, t3='', c3='grey', pos = 1):
    trace1 = scatter(df, d1, t1, c1)
    fig.append_trace(trace1, pos, 1)
    
    if d2:
        trace2 = scatter(df, d2, t2, c2)
        fig.append_trace(trace2, pos, 1)
    if d3:
        trace3 = bar(df, d3, t3, c3)
        fig.append_trace(trace3, pos, 1)
    
    return fig

def plot_3_lines(fig, df, d1, t1='', c1='black', d2=None, t2='', c2='red', d3=None, t3='', c3='grey', pos = 1, fill=False, fillcolor="rgba(0,40,100,0.02)"):
    trace1 = scatter(df, d1, t1, c1)
    fig.append_trace(trace1, pos, 1)
    
    filltonexty = "none"
    if fill==True:
        filltonexty = 'tonexty'
    
    if d2:
        trace2 = scatter(df, d2, t2, c2, fill=filltonexty, fillcolor=fillcolor)
        fig.append_trace(trace2, pos, 1)
        
    if d3:
        trace3 = scatter(df, d3, t3, c3, fill=filltonexty, fillcolor=fillcolor)
        fig.append_trace(trace3, pos, 1)
    
    return fig


plot_candle = lambda fig, df, pos = 1: fig.append_trace( go.Candlestick(x=df.index.astype('str'), open=df.open, high=df.high, low=df.low, close=df.close, name="Candlestick", showlegend=False), pos, 1)
plot_macd = lambda fig, df, pos = 1: plot_2_lines_1_bar(fig, df, 'macd', 'MACD' ,'black', 'macdsignal','MACD Signal', 'red', 'macdhist','MACD Histogram', 'grey', pos)
plot_rsi =  lambda fig, df, pos = 1: plot_2_lines_1_bar(fig, df, 'rsi', 'RSI' ,'black', pos=pos)
plot_bbb =  lambda fig, df, pos = 1, fill=True, fillcolor="rgba(0,40,100,0.02)": plot_3_lines(fig, df, 'bbt', 'Top' ,'lightgrey', 'bbb','Bottom', 'lightgrey', 'bbm','Middle', 'lightgrey', pos, fill, fillcolor)


def plot_trade(fig, df, toffset, pos=1):
    if "buy" in df:
        fig.append_trace(go.Scatter(x=df.index.astype('str'), y=df['buy']*toffset ,  mode='markers', marker=dict(color='green'),showlegend=False, hovertext=df['buy']), pos, 1)
    
    if "sell" in df:
        fig.append_trace(go.Scatter(x=df.index.astype('str'), y=df['sell']*toffset,  mode='markers', marker=dict(color='red'),showlegend=False, hovertext=df['sell']), pos, 1)
    return fig



def render_charts(data, trade, symbol, chart_type='haikin'): 
    price = data

    if data.shape[0] == 0:
        return ''

    xaxis_len = data.shape[0] - 95
    #pinfo(price.tail(1).index)
    #pinfo(price.tail(30).head(1).index)

    #x_min = price.tail(30).head(1).index
    #x_max = price.tail(1).index

    range_min = min(80, xaxis_len)
    xMin = data.index[-1*range_min]
    xMax = data.index[-1]

    yMin = data.iloc[-1*range_min:-1]['low'].min()-10
    yMax = data.iloc[-1*range_min:-1]['high'].max()

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_width=[3,1,5], vertical_spacing = 0.01)
    fig['layout']={'xaxis':{'rangeselector': {'buttons': [{'count': 1, 'label': '1h', 'step': 'hour', 'stepmode': 'backward'},
                                            {'count': 2, 'label': '2h', 'step': 'hour', 'stepmode': 'backward'},
                                            {'count': 3, 'label': '3h', 'step': 'hour', 'stepmode': 'backward'},
                                            {'count': 7, 'label': '1d', 'step': 'hour', 'stepmode': 'backward'},
                                           # {'count': 7, 'label': '1w', 'step': 'day', 'stepmode': 'backward'},
                                            {'count': 1, 'label': '1m', 'step': 'month', 'stepmode': 'backward'},
                                            {'count': 3, 'label': '3m', 'step': 'month', 'stepmode': 'backward'},
                                           # {'count': 6, 'label': '6m', 'step': 'month', 'stepmode': 'backward'},
                                                {'step': 'all'}]},
                'rangeslider': {'visible': False}, 'side': 'bottom', 'range':[xMin, xMax], 'constrain':'domain'}, 
                'xaxis2': {'anchor': 'y2', 'domain': [0.0, 1.0], 'matches': 'x', 'showticklabels': False},
                'xaxis3': {'anchor': 'y3', 'domain': [0.0, 1.0], 'matches': 'x', 'showticklabels': True},
                'yaxis' : {'anchor': 'x', 'domain': [0.45, 1.0], 'side': 'right', 'linecolor':'black', 'ticks':'inside', 'range':[yMin, yMax]},
                'yaxis2': {'anchor': 'x2', 'domain': [0.2, 0.43], 'side': 'right', 'linecolor':'black', 'ticks':'inside'},
                'yaxis3': {'anchor': 'x3', 'domain': [0.0, 0.19], 'side': 'right', 'range':[0,100], 'tickvals':[0,30,70,100], 'ticks':'inside','gridcolor':'black', 'showgrid':True, 'linecolor':'black'},
                'height': 750, 'plot_bgcolor': 'rgba(0,0,0,0)','title': {'text': 'Charts for '+symbol}}



    #fig.update_xaxes(range=[x_min, x_max])
    try:

        pha = pd.DataFrame()
        pha['open'], pha['high'],pha['low'],pha['close'] = HAIKINASI(price)

        price['macd'], price['macdsignal'], price['macdhist'] = MACDEXT(price.close, fastperiod=12, slowperiod=26, signalperiod=9, fastmatype=1, slowmatype=1,signalmatype=1)
        price['rsi'] = RSI(price.close, timeperiod=14)
        price['bbt'], price['bbm'], price['bbb'] = BBANDS(price.close, timeperiod=20, nbdevup=1.6, nbdevdn=1.6, matype=0)
     
        if chart_type=='haikin':
            plot_candle(fig, pha.tail(xaxis_len), 1)
        elif chart_type=='candle' :
            plot_candle(fig, price.tail(xaxis_len), 1)
        else:
            fig = plot_3_lines(fig, price.tail(xaxis_len), 'close')
        
        fig = plot_bbb(fig, price.tail(xaxis_len), 1)
        fig = plot_macd(fig, price.tail(xaxis_len), 2)
        fig = plot_rsi(fig, price.tail(xaxis_len), 3)

        #price['buy'] = []
        #price['sell'] = []
        freq = redis_conn.hget(symbol+cache_type, 'freq')
        toffset = 1.005
        if freq == "1D":
            toffset = 1.1

        if 'buy' in trade:
            price['buy'] = trade['buy']
        
        if 'sell' in trade:
            price['sell'] = trade['sell']
        fig = plot_trade(fig, price.tail(xaxis_len), toffset, 1)
    except:
        perror("Exception in plotting")
        pass

    return fig


def freedom_chart(symbol, chart_type='haikin'):
    if not redis_conn.exists(symbol):
        return ""

    my_cache = cache_state(cache_type)

    dfohlc = my_cache.getOHLC(symbol)
    #pinfo('OHLC: {}'.format(dfohlc.shape[0]))

    #ohlc_df = pd.read_json(redis_conn.get(symbol), orient='columns')

    #pinfo('ohlc_df: {}'.format(ohlc_df.shape[0]))

    #ohlc_df.index.rename('date', inplace=True)
    trade_df = pd.read_json(redis_conn.get(symbol+cache_type+'Trade'), orient='columns')

    trade_df = trade_df.tail(500) # safety for algo on longer durations
    dfohlc = dfohlc.tail(500)

    #pinfo(trade_df)

    return render_charts(dfohlc, trade_df, symbol, chart_type)
