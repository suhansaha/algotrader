import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
external_stylesheets = [dbc.themes.BOOTSTRAP]
from dash.dependencies import Input, Output, State
from datetime import datetime as dt
from datetime import timedelta
import dash_editor_components
from lib.logging_lib import redis_conn, cache_type
df = pd.read_csv('data/ind_nifty50list.csv')
import dash_table
from lib.data_model_lib import *

# Loading OHLC data from local cache
temp_file = pd.HDFStore("data/kite_cache.h5", mode="r")

# List of algos from the cache
algo_list = redis_conn.hkeys('algos')
algo_list_options = pd.DataFrame({'label':algo_list,'value':algo_list}).to_dict(orient='records')

# Helper Functions
def df_to_table(df, id, editable=False, row_deletable=False):
    trade_table = dash_table.DataTable(
        id=id,
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        editable=editable,
        row_deletable = row_deletable,
        style_table={'padding-left':'10px','width': '97%'},
        style_cell = {'text-align':'center'}
    )
    return trade_table

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Page 1", href="#")),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("More pages", header=True),
                dbc.DropdownMenuItem("Page 2", href="#"),
                dbc.DropdownMenuItem("Page 3", href="#"),
            ],
            nav=True,
            in_navbar=True,
            label="More",
        ),
    ],
    brand="Freedom",
    brand_href="#",
    color="dark",
    dark=True,
)

# Left pane for writing algo
algo_input = html.Div(dbc.FormGroup([dbc.InputGroup([dbc.InputGroupAddon(dcc.Dropdown(id='select_algo', options=algo_list_options, style={"min-width":'200px','height':'10px','font-size':'0.9em'}, value='default', clearable=False),addon_type="prepend"), dbc.Input(id="algo-name",placeholder="Filename",value="default"),dbc.InputGroupAddon(dbc.Button("Save", id="algo-save",color="secondary"), addon_type="append")],size="sm"),
                         #   dbc.Textarea(className="mb-3", style={'height':'500px'}, id='algo', value=""),
                            dash_editor_components.PythonEditor(id='algo', value='')
                        ]), style={'max-width':'700px'})

# The form to enter backtest details
cal_end_date = temp_file.get('/minute/NSE/WIPRO').index[-1].strftime("%Y-%m-%d")
cal_start_date = (temp_file.get('/minute/NSE/WIPRO').index[-1] - timedelta(days=10)).strftime("%Y-%m-%d")
freq_options = [{'label':'day', 'value':'1D'},{'label':'1min', 'value':'1T'},{'label':'3min', 'value':'3T','disabled':False},{'label':'5min', 'value':'5T','disabled':False},{'label':'10min', 'value':'10T','disabled':False},{'label':'15min', 'value':'15T','disabled':False}]
stock_options = pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records')

form_div = html.Div([
            dcc.Dropdown(id='yaxis-column', value=['TCS','WIPRO'], multi=True,  className='columns six', options=stock_options),
            dbc.Row([
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("Qty", addon_type="prepend"),dbc.Input(id="input-qty", value=10) ], size="sm"),width=2),
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("SL", addon_type="prepend"),dbc.Input(id="input-sl", placeholder="0.0", value=1),dbc.InputGroupAddon("%", addon_type="append") ], size="sm"),width=2),
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("TP", addon_type="prepend"),dbc.Input(id="input-target", placeholder="0.0", value=1),dbc.InputGroupAddon("%", addon_type="append") ], size="sm"),width=2),
                dbc.Col( dbc.InputGroup([ dcc.DatePickerRange( id='date-picker-range', end_date=cal_end_date, start_date=cal_start_date),
                                            dbc.Select(id='freq', value='1D', options=freq_options )], size="sm"), width=6, sm='12', md=5),
                dbc.Col(dbc.Button('Go', id='button', color="success", disabled=True, size='sm'),width=1),
                dbc.Col(dbc.Checklist(
                        options=[
                            {"label": "Quick", "value": 1},
                        ],
                        value=[1],
                        id="switches-input",
                        switch=True,
                    ))
            ], no_gutters=True),
        ])

chart_type_options = [{'label':'Haikin','value':'haikin'}, {'label':'Candle','value':'candle'}, {'label':'Line','value':'line'}]
chart_list_options = [{'label':'MACD','value':'macd'}, {'label':'RSI','value':'rsi'}]
chart_overlays_options = [{'label':'Bollinger','value':'BBB'}]
graph_div = dbc.FormGroup([
        dbc.InputGroup([dcc.Dropdown(id='select_chart', options=stock_options, style={'width':'150px'}),
        dcc.Dropdown(id='chart_type', value='haikin',options=chart_type_options, style={'width':'150px'}),
        dcc.Dropdown(id='chart_overlays', disabled=True, multi=True, value=['macd','RSI'],options=chart_list_options, style={'width':'200px'}),
        dcc.Dropdown(id='chart_list', disabled=True, multi=True, value='BBB',options=chart_overlays_options, style={'width':'200px'})]),
        html.Div(id='trade_stat', children='', style={'white-space': 'pre'}),
        dcc.Graph(id='example-graph'),
        html.Div(id='trade_summary', children='To be loaded...'),
        dcc.Interval( id='graph-update', interval=1000, n_intervals=0, max_intervals=-1, disabled = True)])

#trade_summary_div = html.Div(id='trade_summary', children='To be loaded...')


log_div = html.Div( id='msg', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'480px'}, children='Welcome to Freedom')

#dbc.InputGroupAddon(dcc.Dropdown(id='select_cmd', options={'label':[], 'value':[]}, style={"min-width":'200px','height':'10px','font-size':'0.9em'}, value='default', clearable=False),addon_type="prepend"),
console_div = html.Div(dbc.FormGroup([dbc.InputGroup([
        dbc.Input(id="cmd-text",placeholder="Enter command",value="pinfo('Hello World')", debounce=True),
        dbc.InputGroupAddon(dbc.Button("Go", id="cmd-btn",color="secondary"), addon_type="append")],size="sm"),
    html.Div( id='console_log', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'480px'}, children='Welcome to Freedom')
                        ]), style={'max-width':'700px'})

    

tabs_bottom = dbc.Tabs(
    [   
        dbc.Tab(graph_div, label="Trade Summary"),
       # dbc.Tab(trade_summary_div, label="Trade Summary"),
        dbc.Tab(log_div, label="Logs"),
        dbc.Tab(console_div, label="Console"),
    ], 
)

# BackTest
backtest_tab = dbc.Row([
    dbc.Col(algo_input),
    dbc.Col([form_div, tabs_bottom])]
)



# Live Trade Tab
#my_cache = cache_state(cache_type)
live_cache = cache_state('live')
df = live_cache.getValue()
pinfo(df)
try:
    df = df[['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state',
       'amount', 'price','P&L','P&L %', 'Total P&L', 'Total P&L %','low', 'sl', 'ltp', 'ltp %','tp', 'high', 'last_processed']]
except:
    pinfo('something went wrong with live table')
    df = pd.DataFrame(columns=['stock', 'qty', 'TP %', 'SL %', 'algo', 'freq', 'mode', 'state',
       'amount', 'price','P&L','P&L %', 'Total P&L', 'Total P&L %','low', 'sl', 'ltp', 'ltp %','tp', 'high', 'last_processed'])

if df.shape[0] > 0:
    trade_table = df_to_table(df, 'table-editing-simple', True, True)
else:
    trade_table = dash_table.DataTable(id='table-editing-simple', editable=True, row_deletable=True)

trade_tab = dbc.Row([
    dbc.Col( 
        [dbc.Row(dbc.Col(dcc.Dropdown(id='stock_picker_live', multi=True,  className='columns six', options=stock_options))),
         dbc.Row([dbc.Col( [dbc.Button("Start", id="live-start",color="success"),
                            #dbc.Button("Pause", id="live-pause",color="warning"),
                            dbc.Button("Stop", id="live-stop",color="danger", disabled=True)]),
                   ]),
         dbc.Row(dbc.Col(trade_table, style={'padding-left':'20px'}))
        ]
    , width=9),
    dbc.Col(html.Div( id='msg_live', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'650px'}, children='Welcome to Freedom'), width=3
)]
)

##### Layout of Page ##########
tabs_top = dbc.Tabs(
    [
        dbc.Tab(backtest_tab, label="Backtest"),
        dbc.Tab(trade_tab, label="Live Trade"),
    ]
)


layout_bootstrap = html.Div(
    [
        dbc.Row(dbc.Col(navbar)),
        dbc.Alert("Hello! I am an alert", id="alert-fade", dismissable=True,is_open=False,duration=4000),
        dbc.Row(dbc.Col(tabs_top)),
    ]
)