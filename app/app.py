#!/usr/bin/env python
"""
CoinBridge minimal web app
@author jack@tinybike.net
"""
from __future__ import division
import sys
import cdecimal
sys.modules["decimal"] = cdecimal
import os
import json
import datetime
import requests
from platform import node
from base64 import b64encode
from OpenSSL import rand
from decimal import Decimal, getcontext, ROUND_HALF_EVEN
from contextlib import contextmanager
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, MissingArgumentError, StaticFileHandler, authenticated, asynchronous
from sockjs.tornado import SockJSRouter, SockJSConnection
from jinja2 import FileSystemLoader, Environment
try:
    import psycopg2cffi as db
    import psycopg2cffi.extensions as ext
    from psycopg2cffi.extras import RealDictCursor
except:
    import psycopg2 as db
    import psycopg2.extensions as ext
    from psycopg2.extras import RealDictCursor
from redis import StrictRedis
from bridge import Bridge

# import tornadoredis
# import tornadoredis.pubsub

redis = StrictRedis()

loader = FileSystemLoader(searchpath="templates/")
env = Environment(loader=loader)

############
# Database #
############

dsnfile = os.path.join(os.path.dirname(__file__), "postgres.cfg")
with open(dsnfile) as config:
    dsn = config.read()

# Main postgres connection
conn = db.connect(dsn)
conn.set_isolation_level(ext.ISOLATION_LEVEL_REPEATABLE_READ)

# Second connection for notifications
lconn = db.connect(dsn)
lconn.set_isolation_level(ext.ISOLATION_LEVEL_AUTOCOMMIT)

@contextmanager
def cursor(cursor_factory=False):
    """Database cursor generator. Commit on context exit."""
    try:
        if cursor_factory:
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()
        yield cur
    except (db.Error, Exception) as e:
        cur.close()
        if conn:
            conn.rollback()
        print e.message
        raise
    else:
        conn.commit()
        cur.close()

##########
# Routes #
##########

class IndexHandler(RequestHandler):

    template = env.get_template("index.html")

    def get(self):
        env.globals['xsrf_form_html'] = self.xsrf_form_html
        user_id = self.get_current_user()
        if user_id is None:
            sid = self.generate_session_id()
            redis.set(sid, 0)
            html = self.template.render(sid=sid)
        else:
            sid = redis.hget(user_id, 'sid')
            if sid is None:
                sid = self.generate_session_id()
                redis.set(sid, 0)
                redis.expire(sid, 10)
                html = self.template.render(sid=sid)
            else:
                username = redis.hget(user_id, 'username')
                html = self.template.render(sid=sid,
                                            login=True,
                                            user_id=user_id,
                                            username=username)
        self.write(html)

    def generate_session_id(self, num_bytes=16):
        return b64encode(rand.bytes(num_bytes))

    def get_current_user(self):
        user_id = None
        user_json = self.get_secure_cookie("user_id")
        if user_json:
            try:
                user_id = json.loads(user_json)
            except ValueError:
                user_id = user_json
        return user_id

    def get_user_id(self):
        return self.get_secure_cookie("user_id")


###########
# Sockets #
###########

class BridgeConnection(SockJSConnection):
    
    players = set()    

    def on_open(self, info):
        self.players.add(self)

    def on_close(self):
        self.players.remove(self)

    def on_message(self, message):
        message = json.loads(message)
        name = message["name"]
        if 'sid' in message and redis.exists(message['sid']):
            if "data" in message:
                data = message['data']
                data['sid'] = message['sid']
                if name == "get-balance":
                    self.get_balance(data)
                elif name == "join-game":
                    self.join_game(data)
            else:
                sid = message['sid']
                if name == "populate-chatbox":
                    self.populate_chatbox(sid)
                elif name == "userlist":
                    self.userlist(sid)

    def emit(self, name, data, broadcast=False, types=None):
        """Socket.io-like emit function for SockJS"""
        if "sid" in data and redis.exists(data["sid"]):
            if types == "Decimal":
                message = json.dumps({
                    'name': name,
                    'data': data,
                }, cls=DecimalEncoder)
            else:
                message = json.dumps({
                    'name': name,
                    'data': data,
                })
            if broadcast:
                self.broadcast(self.players, message)
            else:
                self.broadcast([self], message)

    def userlist(self, sid):
        user_id = redis.get(sid)
        username = redis.hget(user_id, 'username')
        self.emit('user-listing', {
            'success': True,
            'sid': sid,
            'userlist': userlist
        })

    def friend_request(self, data):
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        self.emit('friend-requested', {
            'success': True,
            'sid': data['sid'],
            'requestee': requestee_name
        })


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime.timedelta) or isinstance(o, datetime.datetime):
            return str(o)
        return super(DecimalEncoder, self).default(o)


####################
# Currency/payment #
####################

def currency_precision(ticker):
    if ticker.upper() in ('USD', 'EUR', 'NXT'):
        precision = '.01'
    elif ticker.upper() == 'XRP':
        precision = '.000001'
    else:
        precision = '.00000001'
    return precision

def currency_codes(currency, convert_from="ticker", convert_to="name"):
    """Convert between currencies and their ticker symbols"""
    if convert_from == "name" and convert_to == "name":
        convert_to = "ticker"
    query = """SELECT {convert_to} FROM currencies
    WHERE upper({convert_from}) = upper(%s)""".format(convert_to=convert_to, 
                                                      convert_from=convert_from)
    with cursor() as cur:
        cur.execute(query, (currency,))
        if cur.rowcount:
            return cur.fetchone()[0]
    print "Warning: could not convert from", currency
    return None

BridgeRouter = SockJSRouter(BridgeConnection, '/bridge')

application = Application([
        (r"/", IndexHandler),
        (r"/(bridge\.css)", StaticFileHandler, {"path": "./static/css/"})
    ] + BridgeRouter.urls,
    debug = node() != 'loopy',
    cookie_secret="3sjDo1ilRmS6xKsFLrVQIjR7",
    login_url="/login",
    template_path=os.path.join(os.path.dirname(__file__), "templates"),
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    xsrf_cookies=True
)

if __name__ == "__main__":
    if node() == 'loopy':
        application.listen(8080, "0.0.0.0")
    else:
        application.listen(5000, no_keep_alive=True)
    io_loop = IOLoop.instance()
    io_loop.start()
