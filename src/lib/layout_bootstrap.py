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

df = pd.read_csv('data/ind_nifty50list.csv')

# Loading OHLC data from local cache
temp_file = pd.HDFStore("data/kite_cache.h5", mode="r")
# Loading OHLC data for a stock for initial render
#data = temp_file.get('/day/NSE/WIPRO').tail(100)['close']


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

algo_input = html.Div(dbc.FormGroup([dbc.InputGroup([dbc.Input(placeholder="Filename"),dbc.InputGroupAddon(dbc.Button("Save", color="secondary"), addon_type="append")],size="sm"),
                         #   dbc.Textarea(className="mb-3", style={'height':'500px'}, id='algo', value=""),
                            dash_editor_components.PythonEditor(id='algo', value='')
                        ]), style={'max-width':'700px'})

log_div = html.Div( id='msg', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'350px'}, children='Welcome to Freedom')




cal_end_date = temp_file.get('/minute/NSE/WIPRO').index[-1].strftime("%Y-%m-%d")
cal_start_date = (temp_file.get('/minute/NSE/WIPRO').index[-1] - timedelta(days=10)).strftime("%Y-%m-%d")
freq_options = [{'label':'day', 'value':'day'},{'label':'1min', 'value':'1min'},{'label':'5min', 'value':'5min','disabled':True},{'label':'10min', 'value':'10min','disabled':True},{'label':'15min', 'value':'15min','disabled':True}]
stock_options = pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records')

graph_div = dbc.FormGroup([
        dcc.Dropdown(id='select_chart', options=stock_options),
        dcc.Graph(id='example-graph'),
        dcc.Interval( id='graph-update', interval=1000, n_intervals=0, max_intervals=-1, disabled = True)])

form_div = html.Div([
            dcc.Dropdown(id='yaxis-column', value=['TCS','WIPRO'], multi=True,  className='columns six', options=stock_options),
            dbc.Row([
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("Qty", addon_type="prepend"),dbc.Input(id="input-qty", value=10) ], size="sm"),width=2),
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("SL", addon_type="prepend"),dbc.Input(id="input-sl", placeholder="0.0", value=1),dbc.InputGroupAddon("%", addon_type="append") ], size="sm"),width=2),
                dbc.Col(dbc.InputGroup([ dbc.InputGroupAddon("Target", addon_type="prepend"),dbc.Input(id="input-target", placeholder="0.0", value=1),dbc.InputGroupAddon("%", addon_type="append") ], size="sm"),width=2),
                dbc.Col( dbc.InputGroup([ dcc.DatePickerRange( id='date-picker-range', end_date=cal_end_date, start_date=cal_start_date),
                                            dbc.Select(id='freq', value='day', options=freq_options )], size="sm"), width=6, sm='12', md=5),
                dbc.Col(dbc.Button('Go', id='button', color="success", disabled=True, size='sm'),width=1)
            ], no_gutters=True),
        ])

tabs_bottom = dbc.Tabs(
    [
        dbc.Tab(graph_div, label="Trade Charts"),
        dbc.Tab("Trade Summary: collapse", label="Trade Summary"),
        dbc.Tab(log_div, label="Logs"),
        dbc.Tab("Console", label="Console"),
    ], 
)

backtest_tab = dbc.Row([
    dbc.Col(algo_input),
    dbc.Col([form_div,tabs_bottom])]
)

trade_tab = dbc.Row([
    dbc.Col(dcc.Dropdown(id='stock_picker_live', value=['TCS','WIPRO'], multi=True,  className='columns six', options=stock_options), width=8),
    dbc.Col(html.Div( id='msg_live', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'650px'}, children='Welcome to Freedom'), width=4
)]
)

tabs_top = dbc.Tabs(
    [
        dbc.Tab(backtest_tab, label="Backtest"),
        dbc.Tab(trade_tab, label="Live Trade"),
    ]
)


layout_bootstrap = html.Div(
    [
        dbc.Row(dbc.Col(navbar)),
        dbc.Row(dbc.Col(tabs_top)),
    ]
)