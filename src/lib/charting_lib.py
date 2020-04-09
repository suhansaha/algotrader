
import pandas as pd
import plotly
import plotly.graph_objs as go
from datetime import datetime as dt
from datetime import timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def candlestick(fig, price, pos=1, plot=False):
    #print(price.index)
    # Candlestick
    trace = go.Candlestick(x=price.index.astype('str'), open=price['open'], high=price['high'], low=price['low'], close=price['close'], name="Candlestick", showlegend=False)

    if plot:
        fig.append_trace(trace, pos, 1)
        fig['layout']['yaxis'+str(pos)]['title']="Candlestick"
    return price

from talib import MACD, MACDEXT, RSI, BBANDS, MACD, AROON, STOCHF, ATR, OBV, ADOSC, MINUS_DI, PLUS_DI, ADX, EMA, SMA

def macd(fig, price, pos=1, plot=False):
    #price['macd'], price['macdsignal'], price['macdhist'] = MACD(price.close, fastperiod=12, slowperiod=26, signalperiod=9)
    price['macd'], price['macdsignal'], price['macdhist'] = MACDEXT(price.close, fastperiod=12, slowperiod=26, signalperiod=9, fastmatype=1, slowmatype=1,signalmatype=1)
        
    # list of values for the Moving Average Type:  
    #0: SMA (simple)  
    #1: EMA (exponential)  
    #2: WMA (weighted)  
    #3: DEMA (double exponential)  
    #4: TEMA (triple exponential)  
    #5: TRIMA (triangular)  
    #6: KAMA (Kaufman adaptive)  
    #7: MAMA (Mesa adaptive)  
    #8: T3 (triple exponential T3)
    
    # MACD plots
    traceMACD = go.Scatter(x=price.index.astype('str'), y=price.macd, name='MACD', line=dict(color='black'),showlegend=False)
    traceMACDSignal = go.Scatter(x=price.index.astype('str'), y=price.macdsignal, name='MACD signal', line=dict(color='red'),showlegend=False)
    traceMACDHist = go.Bar(x=price.index.astype('str'), y=price.macdhist, name='MACD Hist', marker=dict(color="grey"),showlegend=False)
        
    if plot:
        fig.append_trace(traceMACD, pos, 1)
        fig.append_trace(traceMACDSignal, pos, 1)
        fig.append_trace(traceMACDHist, pos, 1)
        fig['layout']['yaxis'+str(pos)]['anchor']="x"
        fig['layout']['yaxis'+str(pos)]['side']="right"
        fig['layout']['yaxis'+str(pos)]['title']="MACD"
    
    return price

def bbands(fig, price, pos=1, plot=False, plotPrice=False):
    price['bbt'], price['bbm'], price['bbb'] = BBANDS(price.close, timeperiod=20, nbdevup=1.6, nbdevdn=1.6, matype=0)
    price['bbt2'], price['bbm2'], price['bbb2'] = BBANDS(price.close, timeperiod=20, nbdevup=2.4, nbdevdn=2.4, matype=0)
    
    tracePrice = go.Scatter(x=price.index.astype('str'), y=price.close, marker = dict(color='grey', size=2), mode='lines', name="Close Price", yaxis='y1', showlegend=False)
    traceBBT = go.Scatter(x=price.index.astype('str'), y=price['bbt'], name='BB_up',  line=dict(color='lightgrey'),showlegend=False)
    traceBBB = go.Scatter(x=price.index.astype('str'), y=price['bbb'], name='BB_low',  line=dict(color='lightgrey'), fill = 'tonexty', fillcolor="rgba(0,40,100,0.02)",showlegend=False)
    traceBBM = go.Scatter(x=price.index.astype('str'), y=price['bbm'], name='BB_mid',  line=dict(color='lightgrey'), fill = 'tonexty', fillcolor="rgba(0,40,100,0.02)",showlegend=False)
    
    traceBBT2 = go.Scatter(x=price.index.astype('str'), y=price['bbt2'], name='BB_up2',  line=dict(color='blue'),showlegend=False)
    traceBBB2 = go.Scatter(x=price.index.astype('str'), y=price['bbb2'], name='BB_low2',  line=dict(color='blue'), fill = 'tonexty', fillcolor="rgba(0,40,100,0.02)",showlegend=False)
    #traceBBM2 = go.Scatter(x=price.index.astype('str'), y=price['bbm2'], name='BB_mid2',  line=dict(color='grey'), fill = 'tonexty', fillcolor="rgba(0,40,100,0.02)",showlegend=False)
    
    
    if plot:
        if plotPrice:
            fig.append_trace(tracePrice, pos, 1)
            
        fig.append_trace(traceBBT, pos, 1)
        fig.append_trace(traceBBB, pos, 1)
        fig.append_trace(traceBBM, pos, 1)
        
        fig.append_trace(traceBBT2, pos, 1)
        fig.append_trace(traceBBB2, pos, 1)
        #fig.append_trace(traceBBM2, pos, 1)
    
    return price

def render_charts(data, symbol):
    temp_data = data
    #chart = go.Candlestick(x=price.index.astype('str'), open=price['open'], high=price['high'], low=price['low'], close=price['close'], name="Candlestick", showlegend=False)

    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, row_width=[1,1,3,1,5], vertical_spacing = 0.01)
    fig['layout']['xaxis'] = dict(rangeslider = dict(visible=False), side="bottom") #, range=[xMin,xMax])
    fig['layout'].update(height=950, plot_bgcolor='rgba(0,0,0,0)', title="Charts for "+symbol)
    #fig['layout']['yaxis']['range'] = [yMin, yMax]
    fig['layout']['yaxis']['anchor'] = 'x'
    fig['layout']['yaxis']['side'] = 'right'
    
    fig['layout']['xaxis']['rangeselector'] = dict(
                buttons=list([dict(count=1, label='1h', step='hour', stepmode='backward'),
                              dict(count=3, label='3h', step='hour', stepmode='backward'),
                              dict(count=6, label='1d', step='hour', stepmode='backward'),
                              dict(step='all')]))

    temp_data = candlestick(fig, temp_data,1,True)
    temp_data = bbands(fig, temp_data,1, True)
    temp_data = macd(fig, temp_data,3,True)

    return fig