# Credit: https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from lib.data_model_lib import User, db, cache_state
from flask_login import login_user, logout_user, login_required, login_manager
from lib.logging_lib import pdebug, pdebug1, pdebug5, perror, pinfo,  cache_type, cache_id
from kiteconnect import KiteConnect
import json
from datetime import date, datetime
from decimal import Decimal

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    #pinfo(request.args.get('next'))
    return render_template('login.html')

@auth.route('/signup')
def signup():
    return render_template('signup.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index', _scheme='https',_external=True))

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('auth.signup', _scheme='https',_external=True))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login', _scheme='https',_external=True))

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password) or not user.is_active == True:
        flash('Please check your login details and try again. Reach out to suhansaha@gmail.com for assistance.')
        return redirect(url_for('auth.login', _scheme='https',_external=True)) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('main.profile', _scheme='https',_external=True))

################## OAUTH - Zerodha ####################


#logging.basicConfig(level=logging.DEBUG)

# Base settings
#PORT = 5010
HOST = "127.0.0.1"

serializer = lambda obj: isinstance(obj, (date, datetime, Decimal)) and str(obj)  # noqa

# Kite Connect App settings. Go to https://developers.kite.trade/apps/
# to create an app if you don't have one.
kite_api_key = 'b2w0sfnr1zr92nxm'
kite_api_secret = 'jtga2mp2e5fn29h8w0pe2kb722g3dh1q'

# Create a redirect url
redirect_url = "https://{host}/login".format(host=HOST)

# Login url
login_url = "https://kite.trade/connect/login?api_key={api_key}".format(api_key=kite_api_key)

# Kite connect console url
console_url = "https://developers.kite.trade/apps/{api_key}".format(api_key=kite_api_key)


def get_kite_client():
    """Returns a kite client object
    """
    kite = KiteConnect(api_key=kite_api_key)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    return kite

# Templates
index_template = """
    <div>Make sure your app with api_key - <b>{api_key}</b> has set redirect to <b>{redirect_url}</b>.</div>
    <div>If not you can set it from your <a href="{console_url}">Kite Connect developer console here</a>.</div>
    <a href="{login_url}"><h1>Login to generate access token.</h1></a>"""

login_template = """
    <h2 style="color: green">Success</h2>
    <div>Access token: <b>{access_token}</b></div>
    <h4>User login data</h4>
    <pre>{user_data}</pre>
    <a target="_blank" href="/holdings.json"><h4>Fetch user holdings</h4></a>
    <a target="_blank" href="/orders.json"><h4>Fetch user orders</h4></a>
    <a target="_blank" href="https://localhost"><h4>Start Trading with Freedom</h4></a>"""


@auth.route("/oauth")
@login_required
def oauth():
    return index_template.format(
        api_key=kite_api_key,
        redirect_url=redirect_url,
        console_url=console_url,
        login_url=login_url
    )

@auth.route("/oauth_status")
def oauth_status():
    request_token = request.args.get("request_token")

    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""

    kite = get_kite_client()
    data = kite.generate_session(request_token, api_secret=kite_api_secret)
    access_token = data["access_token"]
    session["access_token"] = access_token
    cache_live = cache_state(cache_id)
    cache_live.set('access_token', access_token)
    kite.set_access_token(access_token)

    return login_template.format(
        access_token=access_token,
        user_data=json.dumps(
            data,
            indent=4,
            sort_keys=True,
            default=serializer
        )
    )

@auth.route("/holdings.json")
@login_required
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())


@auth.route("/orders.json")
@login_required
def orders():
    kite = get_kite_client()
    return jsonify(orders=kite.orders())