#!/usr/bin/env python
"""
Minimal web app for CoinBridgery
@author jack@tinybike.net
"""
import sys
import cdecimal
sys.modules["decimal"] = cdecimal
from __future__ import division
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
from bridge import Bridge

import tornadoredis
import tornadoredis.pubsub

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

def login_user(sid, user_id, username, remember=False, expiry=3600):
    redis.set(sid, user_id)
    redis.hmset(user_id, {'sid': sid, 'username': username})
    if remember:
        redis.persist(sid)
        redis.persist(user_id)
    else:
        redis.expire(sid, expiry)
        redis.expire(user_id, expiry)

class BaseHandler(RequestHandler):

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


class IndexHandler(BaseHandler):
    
    template = env.get_template("index.html")


class RegisterHandler(BaseHandler):

    template = env.get_template("register.html")
    
    def post(self):
        sid = self.get_argument("sid")
        if not redis.exists(sid):
            print "Invalid token"
            self.redirect("/register")
        else:
            username = self.get_argument("username")
            password = self.get_argument("password")
            email = self.get_argument("email")
            if not self.check_username_taken(username):
                user_id = self.insert_user(username, password, email)
                if user_id is not None:
                    self.set_secure_cookie("user_id", str(user_id))
                    login_user(sid, user_id, username, remember=False)
                    redirect = env.get_template("index.html")
                    html = redirect.render(login=True,
                                           user_id=user_id,
                                           username=username,
                                           sid=sid,
                                           registration_ok=True)
                    self.write(html)
                else:
                    print "Fail"
                    self.redirect("/")
            else:
                print "Username", username, "taken"
                self.redirect("/")

    def check_username_taken(self, requested_username):
        taken = False
        with cursor() as cur:
            cur.execute("SELECT count(*) FROM users WHERE username = %s",
                        (requested_username,))
            if cur.rowcount and cur.fetchone()[0] > 0:
                taken = True
        return taken

    def insert_user(self, username, password, email):
        password_hash = guard.bcrypt_digest(password.encode('utf-8'))
        insert_user_parameters = {
            'username': username,
            'password': password_hash,
            'email': email,
        }
        insert_user_query = (
            "INSERT INTO users "
            "(username, password, email) "
            "VALUES "
            "(%(username)s, %(password)s, %(email)s) "
            "RETURNING user_id"
        )
        insert_result = None
        with cursor() as cur:
            cur.execute(insert_user_query, insert_user_parameters)
            if cur.rowcount:
                insert_result = cur.fetchone()[0]
        return insert_result


class LoginHandler(BaseHandler):

    template = env.get_template("login.html")

    def post(self):
        try:
            try:
                sid = self.get_argument("fb_sid")            
            except:
                sid = self.get_argument("sid")
            if not redis.exists(sid):
                self.redirect("/login")
            else:
                login = False
                # Try facebook login first
                try:
                    fb_user_id = self.get_argument("fb_user_id")
                    query = "SELECT user_id, username, email, admin, password FROM users WHERE user_fb_id = %s"
                    with cursor(1) as cur:
                        cur.execute(query, (fb_user_id,))
                        for row in cur:
                            stored_token = row['password']
                            # if self.get_argument("fb_token") == stored_token:
                            user_id = row["user_id"]
                            username = row["username"]
                            admin = row["admin"]
                            email = row["email"]
                            login = True
                except:
                    username = self.get_argument("username")
                    query = (
                        "SELECT user_id, password, email, admin FROM users "
                        "WHERE username = %s"
                    )
                    with cursor(1) as cur:
                        cur.execute(query, (username,))
                        for row in cur:
                            stored_password_digest = row["password"]
                            entered_password = self.get_argument("password").encode("utf-8")
                            if guard.check_password(entered_password,
                                                    stored_password_digest):
                                user_id = row["user_id"]
                                admin = row["admin"]
                                email = row["email"]
                                login = True
                if not login:
                    print "Username or password is invalid"
                    self.redirect("/login")
                else:
                    with cursor() as cur:
                        active_query = "UPDATE users SET active = now() WHERE user_id = %s"
                        cur.execute(active_query, (user_id,))
                    self.set_secure_cookie("user_id", str(user_id))
                    try:
                        remember = self.get_argument('remember') == 'Y'
                    except:
                        remember = False
                    login_user(sid, user_id, username, remember=remember)
                    redirect = env.get_template("index.html")
                    html = redirect.render(login=True,
                                           user_id=user_id,
                                           username=username,
                                           admin=admin,
                                           sid=sid)
                    self.write(html)
        except MissingArgumentError:
            self.redirect("/login")


class LogoutHandler(BaseHandler):
    
    template = env.get_template("index.html")

    def get(self):
        user_id = self.get_current_user()
        if user_id is not None:
            if redis.exists(user_id):
                sid = redis.hget(user_id, 'sid')
                redis.delete(sid)
                redis.delete(user_id)
            self.clear_cookie("user_id")
        self.write(self.template.render(logout=True))


class ProfileHandler(BaseHandler):
    
    template = env.get_template("profile.html")

    # @authenticated
    def get(self, *args, **kwargs):
        env.globals['xsrf_form_html'] = self.xsrf_form_html
        user_id = self.get_current_user()
        if user_id is None:
            self.redirect('/')
        else:
            sid = redis.hget(user_id, 'sid')
            if sid is None:
                sid = self.generate_session_id()
                redis.set(sid, 0)
                redis.expire(sid, 10)
                html = self.template.render(sid=sid)
            else:
                username = redis.hget(user_id, 'username')
            profile_username = self.request.uri.split('/')[2]
            data = {'profile_pic': 'cyclicoin.png'}
            env.globals['xsrf_form_html'] = self.xsrf_form_html
            query = "SELECT * FROM users WHERE username = %s"
            with cursor(1) as cur:
                cur.execute(query, (profile_username,))
                user_info = cur.fetchone()
            if user_info['firstname'] is not None and user_info['lastname'] is not None:
                full_name = user_info['firstname'] + ' ' + user_info['lastname']
            else:
                full_name = None
            if user_info is not None:
                profile_pic = user_info['profile_pic'] if user_info['profile_pic'] is not None else 'cyclicoin.png'
                data = {
                    'profile_user_id': user_info['user_id'],
                    'profile_username': profile_username,
                    'full_name': full_name,
                    'gender': user_info['gender'],
                    'birthday': user_info['birthday'],
                    'age': user_info['age'],
                    'location': user_info['location'],
                    'linkedin_url': user_info['linkedin'],
                    'facebook_url': user_info['facebook'],
                    'twitter_url': user_info['twitter'],
                    'google_url': user_info['googleplus'],
                    'biography': user_info['biography'],
                    'profile_pic': profile_pic,
                    'joined': str(user_info['joined']).split(' ')[0],
                    'active': str(user_info['active']).split(' ')[0],
                }
            html = self.template.render(login=True,
                                        user_id=user_id,
                                        username=username,
                                        sid=sid,
                                        **data)
            self.write(html)

###########
# Sockets #
###########

class GameConnection(SockJSConnection):
    
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
                elif name == "get-start-price":
                    self.get_start_price(data)
                elif name == "get-existing-bets":
                    self.get_existing_bets(data)
                elif name == "place-bet":
                    self.place_bet(data)
                elif name == "create-game":
                    self.create_game(data)
                elif name == "get-time-remaining":
                    self.get_time_remaining(data)
                elif name == "ping-oracle":
                    self.ping_oracle(data)
                elif name == "chat":
                    self.chat(data)
                elif name == "get-friend-requests":
                    self.get_friend_requests(data)
                elif name == "admin-end-round":
                    self.admin_end_round(data)
                elif name == "populate-scribble":
                    self.populate_scribble(data)
                elif name == "scribble":
                    self.scribble(data)
                elif name == "friend-request":
                    self.friend_request(data)
                elif name == "friend-accept":
                    self.friend_accept(data)
                elif name == "facebook-profile-data":
                    self.facebook_profile_data(data)
                elif name == "record-facebook-friends":
                    self.record_facebook_friends(data)
                elif name == "facebook-login":
                    self.facebook_login(data)
            else:
                sid = message['sid']
                if name == "populate-chatbox":
                    self.populate_chatbox(sid)
                elif name == "userlist":
                    self.userlist(sid)
                elif name == "get-friend-list":
                    self.get_friend_list(sid)
                elif name == "get-awards-list":
                    self.get_awards_list(sid)

    def facebook_login(self, data):
        user_id = None
        register = False
        select_query = "SELECT count(*) FROM users WHERE user_fb_id = %s"
        with cursor() as cur:
            cur.execute(select_query, (data["uid"],))
            if cur.fetchone()[0] == 0:
                register = True
        if register:
            query = """INSERT INTO users
                (username, password, firstname, lastname,
                gender, location, facebook,
                user_fb_id, user_fb_name,
                profile_pic, biography)
                VALUES
                (%(username)s, %(password)s, %(firstname)s, %(lastname)s,
                %(gender)s, %(location)s, %(facebook)s,
                %(user_fb_id)s, %(user_fb_name)s,
                %(profile_pic)s, %(biography)s)
                RETURNING user_id"""
            gender = 'M' if data['gender'] == 'male' else 'F'
            username = data['username']
            parameters = {
                'username': username,
                'password': data['token'],
                'firstname': data['first_name'],
                'lastname': data['last_name'],
                'gender': gender,
                'location': data['location_name'],
                'facebook': data['link'],
                'user_fb_id': data['uid'],
                'user_fb_name': data['username'],
                'profile_pic': data['uid'] + ".jpg",
                'biography': data['bio'],
            }
            response = requests.get(data['picture'])
            if response.status_code == 200:
                uploadpath = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                          "static", "uploads", data['uid'] + ".jpg")
                with open(uploadpath, 'w') as upfile:
                    upfile.write(response.content)
            with cursor() as cur:
                cur.execute(query, parameters)
                if cur.rowcount:
                    user_id = cur.fetchone()[0]
        else:
            query = "SELECT user_id, username FROM users WHERE user_fb_id = %s"
            with cursor() as cur:
                cur.execute(query, (data["uid"],))
                user_id, username = cur.fetchone()
        if user_id is not None:
            login_user(data['sid'], user_id, username, remember=False)
            self.emit("facebook-login-response", {
                "success": True,
                "sid": data["sid"],
                "user_id": user_id,
                "fb_user_id": data["uid"],
                "token": data['token'],
            })
        else:
            self.emit("facebook-login-response", {
                "success": False,
                "sid": data["sid"],
            })

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

    def chat(self, data):
        if redis.exists(data['sid']):
            user_id = redis.get(data['sid'])
            username = redis.hget(user_id, 'username')
        else:
            user_id = None
            username = "Guest"
        content = {
            'user_id': user_id,
            'username': username,
            'comment': data['data'],
        }
        query = (
            "INSERT INTO chatbox (user_id, username, comment) "
            "VALUES (%(user_id)s, %(username)s, %(comment)s)"
        )
        with cursor() as cur:
            cur.execute(query, content)
        if data['data']:
            self.emit('chat-response', {
                'success': True,
                'sid': data['sid'],
                'data': data['data'],
                'user': username,
            }, broadcast=True)

    def populate_chatbox(self, sid):
        with cursor(1) as cur:
            query = (
                "SELECT * FROM ("
                "SELECT username, time_sent, comment FROM chatbox "
                "ORDER BY time_sent DESC LIMIT 6) s "
                "ORDER BY time_sent ASC"
            )
            cur.execute(query)
            for row in cur:
                self.emit('chat-populate', {
                    'success': True,
                    'sid': sid,
                    'user': row['username'],
                    'timestamp': str(row['time_sent']),
                    'comment': row['comment'],
                })

    def populate_scribble(self, data):
        with cursor(1) as cur:
            query = (
                "SELECT scribbler_name, time_sent, scribble FROM scribble "
                "WHERE scribblee_name = %s "
                "ORDER BY time_sent DESC LIMIT 25"
            )
            cur.execute(query, (data['scribblee'],))
            for row in cur:
                self.emit('scribble-populate', {
                    'success': True,
                    'sid': data['sid'],
                    'user': row['scribbler_name'],
                    'timestamp': str(row['time_sent']),
                    'comment': row['scribble'],
                })

    def scribble(self, data):
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        content = {
            'scribbler_id': user_id,
            'scribbler_name': username,
            'scribblee_id': data['scribblee_id'],
            'scribblee_name': data['scribblee_name'],
            'scribble': data['data'],
        }
        query = (
            "INSERT INTO scribble "
            "(scribbler_id, scribblee_id, scribbler_name, "
            "scribblee_name, time_sent, scribble) "
            "VALUES "
            "(%(scribbler_id)s, %(scribblee_id)s, %(scribbler_name)s, "
            "%(scribblee_name)s, now(), %(scribble)s) "
            "RETURNING scribbler_name"
        )
        with cursor() as cur:
            cur.execute(query, content)
        if data['data']:
            self.emit('scribble-response', {
                'success': True,
                'sid': data['sid'],
                'data': data['data'],
                'user': content['scribbler_name'],
            }, broadcast=True)

    def get_balance(self, data):
        """Get user's balance from wallet"""
        # print "get-balance", data
        wallet = {}
        query = "SELECT balance, ticker FROM wallets WHERE user_id = %s"
        with cursor() as cur:
            cur.execute(query, (redis.get(data['sid']),))
            if cur.rowcount:
                for row in cur:
                    balance, ticker = row
                    digits = Decimal(currency_precision(ticker))
                    balance = Decimal(balance).quantize(digits,
                                                        rounding=ROUND_HALF_EVEN)
                    wallet[ticker] = balance
        wallet["success"] = True
        wallet["sid"] = data["sid"]
        self.emit("balance", wallet, types="Decimal")

    def join_game(self, data):
        """
        Join a game for the selected coin.  If there isn't one
        going yet, then create one.
        """
        game_id = None
        if "ticker" not in data:
            data["ticker"] = currency_codes(data["market"],
                                            convert_from="name",
                                            convert_to="ticker")
        query = """SELECT game_id, started FROM games
            WHERE ticker = %s AND finished IS NULL"""
        with cursor() as cur:
            cur.execute(query, (data["ticker"],))
            if cur.rowcount:
                game_id, started = cur.fetchone()
        # Create a new game if there isn't one running already
        if game_id is None:
            self.create_game(data)
        # Otherwise, join an existing game
        else:
            # If the game hasn't started yet, start it
            if started is None:
                user_id = redis.get(data['sid'])
                redis.hset(user_id, 'game_id', game_id)
                with cursor() as cur:
                    cur.execute("SELECT start_game(%s::bigint)", (game_id,))
                self.emit('joined-game', {
                    "success": True,
                    "sid": data["sid"],
                    'game_id': game_id,
                })
            # Otherwise, just join
            join_query = "SELECT join_game(%s::bigint, %s::bigint)"
            with cursor() as cur:
                cur.execute(join_query, (game_id, redis.get(data['sid'])))
            user_id = redis.get(data['sid'])
            redis.hset(user_id, 'game_id', game_id)
            self.emit('joined-game', {
                "success": True,
                "sid": data["sid"],
                'game_id': game_id,
            })

    def create_game(self, data):
        """Create a new game"""
        game_id = None
        query = """SELECT create_game(%(game_type)s::varchar,
            %(ticker)s::varchar, %(duration)s::numeric, 'f'::boolean)"""
        with cursor() as cur:
            cur.execute(query, data)
            game_id = cur.fetchone()[0]
        if game_id is not None:
            user_id = redis.get(data['sid'])
            redis.hset(user_id, 'game_id', game_id)
            with cursor() as cur:
                cur.execute("SELECT start_game(%s::bigint)", (game_id,))
            self.emit('joined-game', {
                "success": True,
                "sid": data["sid"],
                'game_id': game_id,
            })

    def get_start_price(self, data):
        """Get the starting price for this game"""
        query = "SELECT start_price, ticker FROM games WHERE game_id = %s"
        with cursor() as cur:
            cur.execute(query, (data["game_id"],))
            if cur.rowcount:
                start_price, ticker = cur.fetchone()
                self.emit('start-price', {
                    "success": True,
                    "sid": data["sid"],
                    'start_price': start_price,
                    'ticker': ticker,
                }, types="Decimal")

    def get_existing_bets(self, data):
        """Get existing bets for this game"""
        query = "SELECT * FROM get_existing_bets(%s::bigint)"
        bets_up, bets_down = [], []
        with cursor() as cur:
            cur.execute(query, (data["game_id"],))
            for bet in cur:
                if bet[0] == '+':
                    b = list(bet[1:])
                    b[-1] = str(b[-1])
                    bets_up.append(b)
                elif bet[0] == '-':
                    b = list(bet[1:])
                    b[-1] = str(b[-1])
                    bets_down.append(b)
        existing_bets = {
            "success": True,
            "sid": data["sid"],
            "game_id": data["game_id"],
            "bets_up": bets_up,
            "bets_down": bets_down,
        }
        self.emit("existing-bets", existing_bets, types="Decimal")

    def place_bet(self, data):
        # print "place-bet:", data
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        # print "redis:", user_id, username
        time_of_bet = None
        target_ticker = None
        ticker_query = "SELECT ticker FROM games WHERE game_id = %s"
        with cursor() as cur:
            cur.execute(ticker_query, (data["game_id"],))
            if cur.rowcount:
                target_ticker = cur.fetchone()[0]
        if target_ticker is not None:
            bet_ticker = data['bet_ticker'].upper()
            precision = currency_precision(bet_ticker)
            amount = Decimal(data['amount']).quantize(Decimal(precision),
                                                      rounding=ROUND_HALF_EVEN)
            conn.set_isolation_level(ext.ISOLATION_LEVEL_SERIALIZABLE)
            query = """SELECT place_bet(%(game_id)s::bigint, %(user_id)s::bigint,
                %(username)s::varchar, %(target_ticker)s::varchar,
                %(amount)s::numeric, %(bet_ticker)s::varchar,
                %(bet_direction)s::char(1))"""
            parameters = {
                'game_id': data['game_id'],
                'user_id': user_id,
                'username': username,
                'target_ticker': target_ticker,
                'amount': amount,
                'bet_ticker': bet_ticker,
                'bet_direction': data['bet_direction'],
            }
            cur = conn.cursor()
            try:
                cur.execute(query, parameters)
                if cur.rowcount:
                    time_of_bet = cur.fetchone()[0]
                    conn.commit()
                else:
                    conn.rollback()
            except Exception as e:
                print e.message
                conn.rollback()
            cur.close()
            conn.set_isolation_level(ext.ISOLATION_LEVEL_REPEATABLE_READ)
            bet_response = {
                'success': True,
                "sid": data["sid"],
                'time_of_bet': str(time_of_bet),
                'target_ticker': target_ticker,
                'amount': amount,
                'bet_ticker': bet_ticker,
                'bet_direction': data['bet_direction'],
            }
            if time_of_bet:
                self.emit('bet-response', bet_response, types="Decimal")
            else:
                self.emit('bet-response', {'success': False, "sid": data["sid"]})
        else:
            self.emit('bet-response', {'success': False, "sid": data["sid"]})

    def get_time_remaining(self, data):
        """Amount of time remaining in the specified game"""
        time_remaining = None
        with cursor() as cur:
            cur.execute("SELECT time_remaining(%s::bigint)", (data["game_id"],))
            if cur.rowcount:
                time_remaining = cur.fetchone()[0]
        if time_remaining is not None:
            time_remaining -= datetime.timedelta(0, 0, time_remaining.microseconds)
            payload = {
                "success": True,
                "sid": data["sid"],
                'time_remaining': str(time_remaining),
                'show_hours': time_remaining >= datetime.timedelta(hours=1),
            }
            self.emit('time-remaining', payload)

    def ping_oracle(self, data):
        """Latest price data (collected by MarketDataTracker)"""
        report = None
        game_query = "SELECT * FROM latest_data_for_game(%s::bigint)"
        with cursor(1) as cur:
            cur.execute(game_query, (data["game_id"],))
            if cur.rowcount:
                report = cur.fetchone()
        report['success'] = True
        report["sid"] = data["sid"]
        self.emit('oracle-report', report, types="Decimal")

    def userlist(self, sid):
        user_id = redis.get(sid)
        username = redis.hget(user_id, 'username')
        userlist = []
        if user_id:
            select_users_query = """
            SELECT username, profile_pic FROM users 
            WHERE username NOT IN (
            (SELECT username1 FROM friends 
            WHERE userid1 = %s or userid2 = %s) 
            UNION 
            (SELECT username2 FROM friends 
            WHERE userid1 = %s OR userid2 = %s)
            ) ORDER BY active DESC LIMIT 12
            """
            with cursor() as cur:
                cur.execute(select_users_query, (user_id,)*4)
                for row in cur:
                    if row[0] != username:
                        userlist.append(row)
        # else:
        #     select_users_query = (
        #         "SELECT username, profile_pic FROM users "
        #         "ORDER BY active DESC LIMIT 12"
        #     )
        #     with cursor() as cur:
        #         cur.execute(select_users_query)
        #         for row in cur:
        #             userlist.append(row)
        self.emit('user-listing', {
            'success': True,
            'sid': sid,
            'userlist': userlist
        })

    def get_friend_requests(self, data):
        friend_requests = []
        sent = False
        user_id = redis.get(data['sid'])
        if data['sent']:
            sent = True
            select_friend_requests_query = (
                "SELECT DISTINCT requestee_id, requestee_name "
                "FROM friend_requests WHERE requester_id = %s"
            )
        else:
            select_friend_requests_query = (
                "SELECT DISTINCT requester_id, requester_name, requester_icon "
                "FROM friend_requests WHERE requestee_id = %s"
            )
        with cursor() as cur:
            cur.execute(select_friend_requests_query, (user_id,))
            for row in cur:
                friend_requests.append(row)
        self.emit('friend-requests', {
            'success': True,
            'sid': data['sid'],
            'friend_requests': friend_requests,
            'sent': sent
        })

    def get_friend_list(self, sid):
        user_id = redis.get(sid)
        username = redis.hget(user_id, 'username')
        friends = []
        select_friends_query = (
            "SELECT username1, icon1, username2, icon2 FROM friends "
            "WHERE userid1 = %s OR userid2 = %s"
        )
        with cursor(1) as cur:
            cur.execute(select_friends_query, (user_id, user_id))
            for row in cur:
                if row['username1'] == username:
                    friends.append([row['username2'], row['icon2']])
                else:
                    friends.append([row['username1'], row['icon1']])
        self.emit('friend-list', {
            'success': True,
            'sid': sid,
            'friends': friends
        })

    def friend_request(self, data):
        """Make a new friend request (called by the requester)"""
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        friend_request_query = (
            "INSERT INTO friend_requests "
            "(requester_id, requester_name, requester_icon, "
            "requestee_id, requestee_name, request_time) "
            "VALUES "
            "(%(requester_id)s, %(requester_name)s, %(requester_icon)s, "
            "%(requestee_id)s, %(requestee_name)s, now()) "
            "RETURNING requestee_name"
        )
        friend_request_parameters = {
            'requester_id': user_id,
            'requester_name': username,
            'requestee_id': data['requester_id'],
            'requestee_name': data['requester_name'],
        }
        select_icon_query = "SELECT profile_pic FROM users WHERE user_id = %s"
        with cursor() as cur:
            cur.execute(select_icon_query, (user_id,))
            for row in cur:
                friend_request_parameters['requester_icon'] = row[0]
            cur.execute(friend_request_query, friend_request_parameters)
            for row in cur:
                requestee_name = row[0]
        self.emit('friend-requested', {
            'success': True,
            'sid': data['sid'],
            'requestee': requestee_name
        })

    def friend_accept(self, data):
        """Accept an existing friend request (called by the requestee)"""
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        tracking_category = 'friends'
        won_awards = None
        insert_friend_parameters = {
            'userid1': user_id,
            'userid2': data['user_id'],
            'username1': username,
        }
        select_icon_query = "SELECT profile_pic, username FROM users WHERE user_id = %s"
        with cursor() as cur:
            cur.execute(select_icon_query, (user_id,))
            for row in cur:
                insert_friend_parameters['icon1'] = row[0]
            cur.execute(select_icon_query, (data['user_id'],))
            for row in cur:
                insert_friend_parameters['icon2'] = row[0]
                insert_friend_parameters['username2'] = row[1]
        insert_friend_query = (
            "INSERT INTO friends "
            "(userid1, username1, icon1, userid2, "
            "username2, icon2, friends_since) "
            "VALUES "
            "(%(userid1)s, %(username1)s, %(icon1)s, %(userid2)s, "
            "%(username2)s, %(icon2)s, now()) "
            "RETURNING username2"
        )
        delete_friend_request_query = (
            "DELETE FROM friend_requests "
            "WHERE (requester_id = %s AND requestee_id = %s) "
            "OR (requestee_id = %s AND requester_id = %s)"
        )
        update_tracking_query = (
            "UPDATE award_tracking "
            "SET number_completed = number_completed + 1, "
            "last_completion = now() "
            "WHERE user_id = %s AND category = %s "
            "RETURNING number_completed"
        )
        next_award_query = (
            "SELECT requirement, award_id, award_name FROM awards "
            "WHERE category = %s AND requirement >= %s "
            "LIMIT 1"
        )
        with cursor() as cur:
            cur.execute(insert_friend_query, insert_friend_parameters)
            for row in cur:
                requester_name = row[0]
            cur.execute(delete_friend_request_query, (user_id,
                                                      data['user_id'],
                                                      user_id,
                                                      data['user_id']))
            for user_id in (user_id, data['user_id']):
                cur.execute(update_tracking_query, (user_id, tracking_category))
                number_completed = 0
                for row in cur:
                    number_completed = str(row[0])
                cur.execute(next_award_query, (tracking_category, number_completed))
                for row in cur:
                    next_award = int(row[0])
                    next_award_id = row[1]
                    next_award_name = row[2]
                    if next_award == number_completed:
                        insert_award_winner_query = (
                            "INSERT INTO award_winners "
                            "(award_id, award_name, category, user_id, won_on) "
                            "VALUES "
                            "(%s, %s, %s, %s, now()) "
                            "RETURNING award_name"
                        )
                        insert_award_winner_parameters = {
                            'award_id': next_award_id,
                            'award_name': next_award_name,
                            'category': tracking_category,
                            'user_id': user_id,
                        }
                        cur.execute(insert_award_winner_query,
                                    insert_award_winner_parameters)
                        for row in cur:
                            won_awards = row[0]
        self.emit('friend-accepted', {
            'success': True,
            'sid': data['sid'],
            'requester': requester_name,
            'won_awards': won_awards
        })

    def charts(self, data):
        user_id = redis.get(sid)
        username = redis.hget(user_id, 'username')
        freq = data['freq']
        currency1 = data['currency1']
        currency2 = data['currency2']
        time_series = []
        with cursor() as cur:
            # No resampled table -- use historical data from CCC
            query = (
                "SELECT starttime, open1, high1, low1, close1 "
                "FROM resampled "
                "WHERE freq = %s AND currency1 = %s AND currency2 = %s"
            )
            cur.execute(query, (freq, currency1, currency2))
            for row in cur:
                time_series.append([float(r) if i else r for i, r in enumerate(row)])
            query2 = "SELECT name FROM currencies WHERE symbol = %s"
            named_currency = currency1 if currency1 != 'USD' else currency2
            cur.execute(query2, (named_currency,))
            for row in cur:
                currency_name = row[0]
        self.emit('chart-data', {
            'success': True,
            'sid': data['sid'],
            'data': time_series,
            'name': currency_name
        })

    def get_awards_list(self, sid):
        user_id = redis.get(sid)
        awards = []
        query = (
            "SELECT award_name, category, points, award_description, icon "
            "FROM awards"
        )
        with cursor(1) as cur:
            cur.execute(query)
            if cur.rowcount:
                for row in cur:
                    awards.append(row)
        self.emit('awards-list', {
            'success': True,
            'sid': sid,
            'awards': awards
        })

    def admin_end_round(self, data):
        with cursor() as cur:
            cur.execute("SELECT game_over(%s::bigint)", (data['game_id'],))

    def get_game_results(self, data):
        if 'sid' in data:
            user_id = redis.get(data['sid'])
        elif 'notify' in data:
            user_id = data['user_id']
            print "Notify triggered game results report"
        query = """SELECT game_id, win, sum(amount_won_or_lost)
        FROM game_results
        WHERE user_id = %s
        AND game_id = %s
        GROUP BY win"""
        # GROUP BY game_id, win
        # ORDER BY game_id"""
        win_loss = Decimal('0')
        with cursor(1) as cur:
            cur.execute(query, (data['user_id'], data['game_id']))
            if cur.rowcount:
                for row in cur:
                    if row['win']:
                        win_loss += row['amount_won_or_lost']
                    else:
                        win_loss -= row['amount_won_or_lost']
        if 'sid' in data:
            self.emit('game-results', {
                'success': True,
                'sid': data['sid'],
                'amount': win_loss,
            }, types="Decimal")
        elif 'notify' in data:
            message = json.dumps({
                "name": "game-result-notify",
                "data": {"success": True, "result": win_loss},
            }, cls=DecimalEncoder)
            self.broadcast([self], message)

    def facebook_profile_data(self, data):
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        update_users_query = (
            "UPDATE users "
            "SET firstname = %(firstname)s, lastname = %(lastname)s, "
            "gender = %(gender)s, location = %(location)s, "
            "biography = %(biography)s, facebook_url = %(facebook_url)s, "
            "profile_pic = %(profile_pic)s, user_fb_id = %(user_fb_id)s, "
            "user_fb_name = %(user_fb_name)s "
            "WHERE username = %(username)s AND user_fb_id IS NULL"
        )
        gender = 'M' if data['gender'] == 'male' else 'F'
        response = requests.get(data['picture'])
        if response.status_code == 200:
            uploadpath = os.path.join(os.path.dirname(__file__),
                                      "static", "uploads")
            with open(uploadpath) as upfile:
                upfile.write(response.content)
        update_users_parameters = {
            'user_fb_id': data['id'],
            'user_fb_name': data['username'],
            'firstname': data['first_name'],
            'lastname': data['last_name'],
            'gender': gender,
            'location': data['location_name'],
            'biography': data['bio'],
            'facebook_url': data['link'],
            'profile_pic': data['picture_file'],
            'username': username,
        }
        with cursor() as cur:
            cur.execute(update_users_query, update_users_parameters)

    def record_facebook_friends(self, data):
        user_id = redis.get(data['sid'])
        username = redis.hget(user_id, 'username')
        select_friends_query = (
            "SELECT friend_fb_id FROM facebook_friends WHERE username = %s"
        )
        with cursor_context() as cur:
            cur.execute(select_friends_query, (username,))
            existing_friends = [str(row[0]) for row in cur.fetchall()]
        insert_friend_query = (
            "INSERT INTO facebook_friends "
            "(username, "
            "friend_fb_id, friend_fb_name) "
            "VALUES "
            "(%(username)s, "
            "%(friend_fb_id)s, %(friend_fb_name)s)"
        )
        with cursor() as cur:
            for friend in data['friends']:
                if friend['id'] not in existing_friends:
                    insert_friend_parameters = {
                        'username': username,
                        'friend_fb_id': friend['id'],
                        'friend_fb_name': friend['name'],
                    }
                    cur.execute(insert_friend_query, insert_friend_parameters)



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

GameRouter = SockJSRouter(GameConnection, '/bet')

application = Application([
        (r"/", IndexHandler),
        (r"/register", RegisterHandler),
        (r"/login", LoginHandler),
        (r"/auth", AuthHandler),
        (r"/logout", LogoutHandler),
        (r"/profile/(.*)", ProfileHandler),
        (r"/(cab\.css)", StaticFileHandler, {"path": "./static/css/"})
    ] + GameRouter.urls, # + SockJSRouter(MessageHandler, '/sockjs').urls,
    debug = node() != 'loopy',
    cookie_secret="3sjDo1ilRmS6xKsFLrVQIjR7",
    login_url="/login",
    template_path=os.path.join(os.path.dirname(__file__), "templates"),
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    xsrf_cookies=True,
    facebook_api_key="807459499283753",
    facebook_secret="3a82b21a79bf8fcea78d29c00555513e"
)

if __name__ == "__main__":
    if node() == 'loopy':
        application.listen(8080, "0.0.0.0")
    else:
        application.listen(5000, no_keep_alive=True)
    io_loop = IOLoop.instance()
    io_loop.add_handler(lconn.fileno(), receive, io_loop.READ)
    listen("game")
    io_loop.start()
