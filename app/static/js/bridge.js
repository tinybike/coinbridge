/**
 * @fileoverview CoinBridge web app front-end core
 * @author jack@tinybike.net
 */
var BRIDGE = (function (my, $) {
    /**
     * Module pattern: exports from BRIDGE
     */
    var _exports = my._exports = my._exports || {};
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
    /**
     * All listeners/event handlers are registered here,
     * including DOM manipulation and websockets events.
     *
     * @constructor
     */
    function Cab() {
        var self = this;
        this.digits = 8;
    }
    /**
     * DOM manipulation, visual tweaks, and event handlers that do not
     * involve websockets.
     */
    Cab.prototype.tweaks = function () {
        var self = this;
        $("body").attr('style', 'none');
        $("body").css('background-color', '#f8f8f8');
        $('#modal-ok-button').click(function (event) {
            event.preventDefault();
            $('#modal-ok-box').hide();
            $('#modal-dynamic').foundation('reveal', 'close');
        });
        return this;
    };
    /**
     * Outgoing websocket signals.  Event handlers that send messages to
     * the server via websocket as part of their callback are registered here.
     */
    Cab.prototype.exhaust = function () {
        var self = this;
        return this;
    };
    /**
     * Listeners for incoming websocket signals.
     */
    Cab.prototype.intake = function () {
        var self = this;
        socket.on('notify', function (res) {
            $('#live-feed').text(res.feed);
            self.sync();
            var clear_feed = setTimeout(function () {
                $('#live-feed').hide();
            }, 10000);
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
        });
    };
    return _exports;
}(BRIDGE || {}, jQuery));
