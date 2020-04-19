import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from lib.algo_lib import *

scatter = lambda df, key, title, c, fill='none', fillcolor="rgba(0,40,100,0.02)": go.Scatter(x=df.index.astype('str'), y=df[key], name=title, line=dict(color=c),showlegend=False, fill = fill, fillcolor=fillcolor)
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


def plot_trade(fig, df, pos=1):
    fig.append_trace(go.Scatter(x=df.index.astype('str'), y=df['buy']*1.05 ,  mode='markers', marker=dict(color='green'),showlegend=False, hovertext=df['buy']), pos, 1)
    fig.append_trace(go.Scatter(x=df.index.astype('str'), y=df['sell']*1.05,  mode='markers', marker=dict(color='red'),showlegend=False, hovertext=df['sell']), pos, 1)
    return fig



def render_charts(data, trade, symbol):
    #temp_data = data
    #chart = go.Candlestick(x=price.index.astype('str'), open=price['open'], high=price['high'], low=price['low'], close=price['close'], name="Candlestick", showlegend=False)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_width=[3,1,5], vertical_spacing = 0.01)
    fig['layout']={'xaxis':{'rangeselector': {'buttons': [{'count': 1, 'label': '1h', 'step': 'hour', 'stepmode': 'backward'},
                                            {'count': 3, 'label': '3h', 'step': 'hour', 'stepmode': 'backward'},
                                            {'count': 6, 'label': '1d', 'step': 'hour', 'stepmode': 'backward'},
                                                {'step': 'all'}]},
                'rangeslider': {'visible': False}, 'side': 'bottom'}, 
                'xaxis2': {'anchor': 'y2', 'domain': [0.0, 1.0], 'matches': 'x', 'showticklabels': False},
                'xaxis3': {'anchor': 'y3', 'domain': [0.0, 1.0], 'matches': 'x', 'showticklabels': True},
                'yaxis' : {'anchor': 'x', 'domain': [0.45, 1.0], 'side': 'right', 'linecolor':'black', 'ticks':'inside'},
                'yaxis2': {'anchor': 'x2', 'domain': [0.2, 0.43], 'side': 'right', 'linecolor':'black', 'ticks':'inside'},
                'yaxis3': {'anchor': 'x3', 'domain': [0.0, 0.19], 'side': 'right', 'range':[0,100], 'tickvals':[0,30,70,100], 'ticks':'inside','gridcolor':'black', 'showgrid':True, 'linecolor':'black'},
                'height': 750, 'plot_bgcolor': 'rgba(0,0,0,0)','title': {'text': 'Charts for '+symbol}}


    price = data

    pha = pd.DataFrame()
    pha['open'], pha['high'],pha['low'],pha['close'] = HAIKINASI(price)

    price['macd'], price['macdsignal'], price['macdhist'] = MACDEXT(price.close, fastperiod=12, slowperiod=26, signalperiod=9, fastmatype=1, slowmatype=1,signalmatype=1)
    price['rsi'] = RSI(price.close, timeperiod=14)
    price['bbt'], price['bbm'], price['bbb'] = BBANDS(price.close, timeperiod=20, nbdevup=1.6, nbdevdn=1.6, matype=0)

    #price['buy'] = ohlc_data['close'][30:40]
    #price['sell'] = ohlc_data['close'][50:51]
        
    #plot_candle(fig, price, 1)
    plot_candle(fig, pha, 1)
    try:
        price['buy'] = trade['buy']
        price['sell'] = trade['sell']
        fig = plot_trade(fig, price, 1)
    except:
        pass
    fig = plot_bbb(fig, price, 1)
    fig = plot_macd(fig, price, 2)
    fig = plot_rsi(fig, price, 3)


    return fig