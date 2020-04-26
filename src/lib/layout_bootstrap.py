import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
external_stylesheets = [dbc.themes.BOOTSTRAP]
from dash.dependencies import Input, Output, State
from datetime import datetime as dt
from datetime import timedelta

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

algo_input = dbc.FormGroup(
    [dbc.InputGroup(
            [
                dbc.Input(placeholder="Filename"),
                dbc.Button("Save", color="secondary", className="mr-1"),
            ]),
        dbc.Textarea(className="mb-3", style={'height':'500px'}, id='algo', value="")
    ]
)

log_div = html.Div( id='msg', style={'font-size':'0.8em','border':'1px solid olivegreen','overflow-y': 'scroll',
'white-space': 'pre', 'background':'darkslategray','color':'lightgray','padding':'20px','height':'350px'}, children='Welcome to Freedom')

graph_div = html.Div([dcc.Graph(id='example-graph'),
        dcc.Interval( id='graph-update', interval=1000, n_intervals=0, max_intervals=-1, disabled = True)])

btn_div = html.Div([dcc.Dropdown(id='yaxis-column', value=['TCS','WIPRO'], multi=True,  className='columns six',
                        options=pd.DataFrame({'label':df['Symbol'],'value':df['Symbol']}).to_dict(orient='records')),

        dcc.DatePickerRange( id='date-picker-range', className='columns five', end_date_placeholder_text='Select a date!',
                end_date=temp_file.get('/minute/NSE/WIPRO').index[-1].strftime("%Y-%m-%d"),
                start_date=(temp_file.get('/minute/NSE/WIPRO').index[-1] - timedelta(days=10)).strftime("%Y-%m-%d")),
        
        html.Label("Qty:", className='columns one'),
        dcc.Input(id='input-qty', type='text', className='columns two', value='10'),
        
        html.Label("SL:", className='columns one'),
        dcc.Input(id='input-sl', type='text', className='columns one', value='1'),
        
        html.Label("Target:", className='columns one'),
        dcc.Input(id='input-target', type='text', className='columns one', value='2'),
        dcc.Dropdown(id='freq', style={'margin-left':'10px'}, value='day', multi=False,  className='columns two',
                        options=[{'label':'day', 'value':'day'},{'label':'1min', 'value':'1min'}] ),
        html.Button('BackTest: Start', id='button', disabled=True, className='columns three')])

tabs_bottom = dbc.Tabs(
    [
        dbc.Tab(graph_div, label="Trade Charts"),
        dbc.Tab(log_div, label="Trade Logs"),
        dbc.Tab("Console", label="Console"),
    ], 
)

backtest_tab = dbc.Row([
    dbc.Col(algo_input),
    dbc.Col([btn_div,tabs_bottom])]
)

tabs_top = dbc.Tabs(
    [
        dbc.Tab(backtest_tab, label="Backtest"),
        dbc.Tab("PaperTrade", label="Paper Trade"),
        dbc.Tab("LiveTrade", label="Live Trade"),
    ]
)


layout_bootstrap = html.Div(
    [
        dbc.Row([dbc.Col(navbar)]),
        dbc.Row(dbc.Col([tabs_top])),
    ]
)


freedom_index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}: Suhan</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <script>setTimeout(function(){ var myCodeMirror = CodeMirror.fromTextArea(document.getElementById('algo'),
        {
            lineNumbers: true, theme:'dracula',mode:'python'
        }); }, 3000);</script>
    </body>
</html>
'''