/**
 * @fileoverview CoinBridge web app front-end core
 * @author jack@tinybike.net
 */
var BRIDGE = (function (my, $) {
    /**
     * Module pattern: exports from BRIDGE
     */
    var _exports = my._exports = my._exports || {};
    _exports.headline_coins = ['Bitcoin', 'Litecoin', 'Dogecoin'];
    _exports.headline_tickers = ['BTC', 'LTC', 'DOGE'];
    _exports.chart_data_loaded = false;
    var _seal = my._seal = my._seal || function () {
        delete my._exports;
        delete my._seal;
        delete my._unseal;
    };    
    var _unseal = my._unseal = my._unseal || function () {
        my._exports = _exports;
        my._seal = _seal;
        my._unseal = _unseal;
    };
    var sync_interval = 10000; // milliseconds
    var timesync = false;
    var reconnected = 0;
    /**
     * SockJS wrapper with some semantic sugar to make it look more like
     * socket.io. Supports socket.emit and socket.on.
     * @param namespace {String | null} Route/namespace to link with
     */
    var sockjs = function (namespace) {
        this._events = {};
        this._url = window.location.protocol + '//' + window.location.host;
        this._sockjs = null;
        this._namespace = namespace || "";
        this.reconnect = true;
        this.transports = [
            "websocket",
            "xhr-streaming",
            "iframe-eventsource",
            "iframe-htmlfile",
            "xhr-polling",
            "iframe-xhr-polling",
            "jsonp-polling"
        ];
        this.timeout = 10;
    };
    /**
     * Bind a function to an event from the server by matching the function
     * to the message's "name" field.
     * @param name {String} Message type
     * @param fct {Function} Event callback function
     * @param scope {Object | null} Callback scope
     */
    sockjs.prototype.on = function (name, fct, scope) {
        var fn = fct;
        if (scope) {
            fn = function () { fct.apply(scope, arguments); };
        }
        if(!this._events[name]) {
            this._events[name] = [];
        }
        this._events[name].push(fct);
    };
    /**
     * Send a named message to the server.
     * @param name {String} Message type
     * @param data {Object} Stringifiable, to be attached to the message
     */
    sockjs.prototype.emit = function (name, data) {
        var data;
        if (window.sid) {
            data = { name: name, data: data, sid: window.sid };
            if (this._sockjs.readyState == SockJS.OPEN) {
                if (typeof(data) === "string") {
                    this._sockjs.send(data);
                } else {
                    try {
                        this._sockjs.send(JSON.stringify(data));
                    } catch (e) {
                        console.error(e);
                        try {
                            this._sockjs.send(data.toString())
                        } catch (e) {
                            console.log("Unable to serialize data");
                            console.log(data);
                            console.error(e);
                        }
                    }
                }
            }
        }
    };
    /**
     * Connect to server.
     */
    sockjs.prototype.connect = function () {
        if (reconnected > 10) {
            this.disconnect();
        }
        if (this._sockjs) {
            var temp = this.reconnect;
            this.disconnect();
            this.reconnect = temp;
            reconnected += 1;
        }
        var socket_url = this._url + '/' + this._namespace;
        var sckt = new SockJS(socket_url);//, null, {debug: false, devel: false});
        var _this = this;
        /**
         * Parse and dispatch incoming message from the server.
         * @param response {Object} The data from server side
         */
        function _catchEvent(response) {
            var parsed, func, f;
            if (response.type === "message" && response.data) {
                parsed = JSON.parse(response.data);
                func = _this._events[parsed.name];
                if (func && parsed.data.success) {
                    delete parsed.data.success;
                    for (var i = 0, len = func.length; i < len; ++i) {
                        f = func[i];
                        // console.log("Dispatch to: " + parsed.name);
                        if (typeof(f) === "function") {
                            (function (callback) {
                                setTimeout(function () {
                                    callback(parsed.data);
                                }, 0);
                            })(f);
                        }
                    }
                }
            }
        };
        // Catch open
        sckt.onopen = function () {
            _catchEvent({
                name: "open",
                data : {}
            });
        };
        sckt.onmessage = function (data) {
            _catchEvent(data);
        };
        // Catch close, and reconnect
        sckt.onclose = function () {
            _catchEvent({
                name: "close",
                data : {}
            });
            if(_this.reconnect) {
                _this.connect();
            }
        };
        // Link to server
        this._sockjs = sckt;
        // Wait for ready signal
        this.readycheck();
    };
    /**
     * Ping the socket's readyState until it is open.
     */
    sockjs.prototype.readycheck = function () {
        var _this = this;
        if (this._sockjs.readyState != SockJS.OPEN) {
            setTimeout(function () { _this.readycheck(); }, this.timeout);
        } else {
            cab.init_sockets();
        }
    };
    /**
     * Disconnect from server
     */
    sockjs.prototype.disconnect = function () {
        this.reconnect = false;
        if (!this._socket) {
            return;
        }
        this._socket.close();
        this._socket = null;
    };

    /**
     * @param {number|string} n
     * @param {number} d
     */
    function round_to(n, d) {
        if (typeof n !== 'number') {
            try {
                n = parseFloat(n);
            } catch (e) {
                console.log("Rounding error:", e);
                return n;
            }
        }
        var m = Math.pow(10, d);
        return Math.round(n * m) / m;
    }
    /**
     * @param {number} min
     * @param {number} max
     */
    function get_random_int(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    /**
     * Create modal alert window using Foundation reveal
     * @param {string|null} bodytext
     * @param {string|null} bodytag
     * @param {string|null} headertext
     */
    function modal_alert(bodytext, bodytag, headertext) {
        var modal_body;
        if (headertext) {
            $('#modal-header').empty().text(headertext);
        }
        if (bodytext) {
            modal_body = (bodytag) ? $('<' + bodytag + ' />') : $('<p />');
            $('#modal-body').empty().append(
                modal_body.addClass('modal-error-text').text(bodytext)
            );
        }
        $('#modal-ok-box').show();
        $('#modal-dynamic').foundation('reveal', 'open');
    }
    function modal_select(select, bodytag, headertext) {
        var modal_body;
        if (headertext) {
            $('#modal-header').empty().html(headertext);
        }
        if (select) {
            modal_body = (bodytag) ? $('<' + bodytag + ' />') : $('<p />');
            $('#modal-body').empty().append(
                modal_body
                    .addClass('modal-error-text')
                    .append(select)
            );
        }
        $('#modal-ok-box').show();
        $('#modal-dynamic').foundation('reveal', 'open');
    }
    /**
     * All listeners/event handlers are registered here,
     * including DOM manipulation and websockets events.
     *
     * @constructor
     */
    function Cab() {
        var self = this;
        this.chatbox_populated = false;
        this.scribble_populated = false;
        this.predict_market = "Bitcoin";
        this.digits = 8;
        if (login) {
            this.default_game_duration = (user_id == 1) ? 15 : 900;
        }
    }
    /**
     * DOM manipulation, visual tweaks, and event handlers that do not
     * involve websockets.
     */
    Cab.prototype.tweaks = function () {
        var self = this;
        if (login) {
            $("body").attr('style', 'none');
            $("body").css('background-color', '#f8f8f8');
            $('.sidebar').height(
                $(window).height() - $('.top-bar').height()
            );
            $('#main-block').height(
                $(window).height() - $('.top-bar').height()
            );
            $(document).resize(function () {
                $('.sidebar').height(
                    $(window).height() - $('.top-bar').height()
                );
                $('#main-block').height(
                    $(window).height() - $('.top-bar').height()
                );
            });
            $(window).resize(function () {
                $('.sidebar').height(
                    $(window).height() - $('.top-bar').height()
                );
                $('#main-block').height(
                    $(window).height() - $('.top-bar').height()
                );
            });
        }
        if ($('#startup').text() == "True") {
            self.setup_lightbox();
        }
        $('#modal-ok-button').click(function (event) {
            event.preventDefault();
            $('#modal-ok-box').hide();
            $('#modal-dynamic').foundation('reveal', 'close');
        });
        $('#BTC-USD-chart-button').click(function (event) {
            event.preventDefault();
            hide_chart = false;
            self.charts(null, 'BTC', 'USD');
        });
        $('#USD-XRP-chart-button').click(function (event) {
            event.preventDefault();
            hide_chart = false;
            self.charts(null, 'USD', 'XRP');
        });
        $('#BTC-XRP-chart-button').click(function (event) {
            event.preventDefault();
            hide_chart = false;
            self.charts(null, 'BTC', 'XRP');
        });
        $('#hide-chart-button').click(function (event) {
            event.preventDefault();
            hide_chart = true;
            self.charts(this);
        });
        $('#change-market').click(function (event) {
            var opt, select, coin_list, ticker_list, is_selected;
            event.preventDefault();
            coin_list = _exports.headline_coins;
            ticker_list = _exports.headline_tickers;
            select = $('<select />').attr('id', 'select-market');
            for (var i = 0, len = coin_list.length; i < len; ++i) {
                opt = $('<option />').val(coin_list[i])
                                     .text(coin_list[i])
                                     .attr("ticker", ticker_list[i]);
                if (coin_list[i] == self.predict_market) {
                    opt = opt.attr('selected', 'selected');
                    is_selected = true;
                }
                select.append(opt);
            }
            if (!is_selected) {
                opt = $('<option />').val(self.predict_market)
                                     .text(self.predict_market)
                                     .attr('selected', 'selected');
                select.append(opt);
            }
            modal_select(select, 'h5', 'Select market');
            $('#more-coins').click(function (event) {
                event.preventDefault();
                socket.emit('get-coin-list');
            });
            $('#select-market').change(function () {
                var market = $('#select-market').children(':selected').text();
                $('.selected-market').empty().text(market);
                $('#modal-ok-box').hide();
                $('#modal-dynamic').foundation('reveal', 'close');
                self.predict_market = market;
                console.log("Attempting to join game for " + market);
                socket.emit('join-game', {
                    game_type: 'altcoin-up-or-down',
                    market: market,
                    duration: self.default_game_duration
                });
            });
        });
        if (window.page === "index") {
            self.predict_market = $('.selected-market').first().text();
            if (login) {
                $('.select-currency').each(function () {
                    check_issuer(this);
                    $(this).change(function () {
                        check_issuer(this);
                    });
                });
                $('#predict-tab').click(function () {
                    self.predict_market = $('.selected-market').first().text();
                });
            }
        }
        return this;
    };
    Cab.prototype.setup_lightbox = function () {
        $('.close-link').each(function () {
            $(this).on('click', function (event) {
                event.preventDefault();
                $('#registration-successful-lightbox').trigger('close');
            });
        });
        $('#registration-successful-lightbox').lightbox_me({centered: true});
        return this;
    };
    /**
     * Outgoing websocket signals.  Event handlers that send messages to
     * the server via websocket as part of their callback are registered here.
     */
    Cab.prototype.exhaust = function () {
        var self = this;
        function place_bet(bet_direction) {
            var amount, error_text, bet_parameters;
            direction_text = (bet_direction == '+') ? "up" : "down";
            amount = $('#bet-input-' + direction_text).val();
            if (!isNaN(amount)) {
                amount = parseFloat(amount);
                // Make sure we've got enough funds to make the bet
                if (self.dyf_balance && amount <= self.dyf_balance) {
                    $('#bet-input-' + direction_text).val(null);
                    bet_parameters = {
                        game_id: game_id,
                        user_id: user_id,
                        username: username,
                        amount: amount,
                        bet_direction: bet_direction,
                        bet_ticker: $('#bet-denomination-' + direction_text).val()
                    };
                    socket.emit('place-bet', bet_parameters);
                } else {
                    error_text = "You do not have enough funds in your account to place this bet.";
                    modal_alert(error_text, 'h5', 'Betting error');
                }
            } else {
                error_text = "You must enter a number!";
                modal_alert(error_text, 'h5', 'Betting error');
            }
        }
        if (login) {
            socket.emit("join-game", {
                game_type: 'altcoin-up-or-down',
                market: self.predict_market || "Bitcoin",
                duration: self.default_game_duration
            });
            socket.emit('get-friend-requests', {sent: false});
            socket.emit('get-friend-list');
            socket.emit('userlist');
            if (admin) {
                $('#admin-end-round').click(function (event) {
                    event.preventDefault();
                    socket.emit('admin-end-round', {game_id: game_id});
                    self.sync();
                });
            }
            switch (window.page) {
                case 'index':
                    if (!this.chatbox_populated) {
                        socket.emit('populate-chatbox');
                        this.chatbox_populated = true;
                    }
                    $('form#broadcast').submit(function (event) {
                        event.preventDefault();
                        socket.emit('chat', {
                            data: $('#broadcast_data').val()
                        });
                        $('#broadcast_data').val('');
                    });
                    $('form#bet-down').submit(function (event) {
                        event.preventDefault();
                        place_bet('-');
                    });
                    $('form#bet-up').submit(function (event) {
                        event.preventDefault();
                        place_bet('+');
                    });
                    break;
                case 'profile':
                    if (!this.scribble_populated) {
                        socket.emit('populate-scribble', {
                            scribblee: window.profile_name
                        });
                        this.scribble_populated = true;
                    }
                    $('form#scribble-broadcast').submit(function (event) {
                        event.preventDefault();
                        socket.emit('scribble', {
                            data: $('#scribble_data').val(),
                            scribblee_name: window.profile_name,
                            scribblee_id: window.profile_id
                        });
                        $('#scribble_data').val('');
                    });
                    if (window.profile_id.toString() !== user_id.toString()) {
                        socket.emit('get-friend-requests', {sent: true});
                        if (!window.friend_request_pending) {
                            $('#add-friend-button').click(function (event) {
                                event.preventDefault();
                                socket.emit('friend-request', {
                                    requester_name: window.profile_name,
                                    requester_id: window.profile_id
                                });
                            });
                        }
                    } else {
                        $('#edit-profile-button').click(function (event) {
                            event.preventDefault();
                            $('#vitals').hide();
                            $('#profile-pic').hide();
                            $('#edit-vitals').show();
                            $('#edit-profile-pic').show();
                        });
                    }
                    socket.emit('get-awards-list');
                    break;
            }
        }
        return this;
    };
    /**
     * Listeners for incoming websocket signals.
     */
    Cab.prototype.intake = function () {
        var self = this;
        socket.on('joined-game', function (res) {
            window.game_id = res.game_id;
            timesync = false;
            self.sync(1);
        });
        socket.on('notify', function (res) {
            $('#live-feed').text(res.feed);
            self.sync();
            var clear_feed = setTimeout(function () {
                $('#live-feed').hide();
            }, 10000);
        });
        socket.on('coin-list', function (res) {
            var select;
            if (res.coin_list && res.coin_list.length) {
                select = $('#select-market').empty();
                for (var i = 0, len = res.coin_list.length; i < len; ++i) {
                    select.append(
                        $('<option />').val(res.coin_list[i])
                                       .text(res.coin_list[i])
                                       .attr("ticker", res.ticker_list[i])
                    );
                }
            }
        });
        socket.on('balance', function (res) {
            var balance;
            for (var key in res) {
                if (res.hasOwnProperty(key)) {
                    balance = Number(parseFloat(res[key]).toFixed(self.digits)) + " " + key;
                    if (key == 'DYF') {
                        self.dyf_balance = res[key];
                    }
                    $("#" + key + "-balance").empty().html(balance).show();
                }
            }
        });
        socket.on('chat-populate', function (msg) {
            var timestamp = msg.timestamp.split('.')[0];
            $('#babble').append('<br />' + msg.user + ' <span class="timestamp">[' + moment(timestamp).fromNow() + ']</span>: ' + msg.comment);
        });
        socket.on('chat-response', function (msg) {
            var now = new Date();
            $('#babble').append('<br />' + msg.user + ' <span class="timestamp">[' + moment(now).fromNow() + ']</span>: ' + msg.data);
            var cb = document.getElementById('chat-box');
            cb.scrollTop = cb.scrollHeight;
        });
        return this;
    };
    /**
     * Set up socket listeners on ready signal.
     */
    Cab.prototype.init_sockets = function () {
        if (login) {
            this.intake().exhaust().charts();
        }
    };
    _exports.init = function () {
        $(document).ready(function () {
            cab = new Cab();
            window.socket = new sockjs('bet', true);
            socket.connect();
            if (login) cab.tweaks();
            socket.on('facebook-login-response', function (res) {
                if (res && res.sid) {
                    $('#fb_sid').attr('value', res.sid);
                    $('#fb_user_id').attr('value', res.fb_user_id);
                    $('#fb_token').attr('value', res.token);
                    $('#fb-login-form').submit();
                }
            });
        });
    };
    /**
     * Facebook JS SDK
     */
    $('#facebook-login-button').click(function (event) {
        event.preventDefault();
        window.fbAsyncInit = function () {
            var graph_url, picture_large;
            graph_url = window.location.protocol + '//graph.facebook.com/';
            picture_large = '/picture?type=large';
            FB.init({
                appId      : '807459499283753',
                status     : true, // check login status
                cookie     : true, // enable cookies
                xfbml      : true  // parse XFBML
            });
            // FB Graph API reference:
            // https://developers.facebook.com/docs/graph-api/reference/v2.0
            FB.Event.subscribe('auth.authResponseChange', function (res) {
                var uid, accessToken, getToken;
                if (res.status === 'connected') {
                    uid = res.authResponse.userID;
                    accessToken = res.authResponse.accessToken;
                    getToken = '//graph.facebook.com/oauth/access_token?client_id=' + uid + '&client_secret=' + accessToken + '&grant_type=client_credentials';
                    // Get user info from FB graph
                    FB.api('/me', function (response) {
                        // Login integration
                        socket.emit('facebook-login', {
                            uid: uid,
                            token: accessToken,
                            username: response.username || response.id,
                            first_name: response.first_name,
                            last_name: response.last_name,
                            gender: response.gender,
                            location_id: response.location.id,
                            location_name: response.location.name,
                            bio: response.bio,
                            link: response.link,
                            picture: graph_url + response.id + picture_large
                        });
                    });
                } else {
                    FB.login();
                }
            });
            FB.getLoginStatus(function (res) {
                console.log('FB.getLoginStatus: ' + res.status);
            });
        };
        // Load the Facebook SDK asynchronously
        (function(d){
            var js, id = 'facebook-jssdk', ref = d.getElementsByTagName('script')[0];
            if (d.getElementById(id)) {return;}
            js = d.createElement('script'); js.id = id; js.async = true;
            js.src = "//connect.facebook.net/en_US/all.js";
            ref.parentNode.insertBefore(js, ref);
        }(document));
    });
    return _exports;
}(BRIDGE || {}, jQuery));
