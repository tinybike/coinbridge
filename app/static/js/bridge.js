/**
 * @fileoverview CoinBridge web app front-end core
 * @author jack@tinybike.net
 */
var BRIDGE = (function (my, ripple, stellar, $) {
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
     * Remote rippled server connection info
     * @const 
     */
    var rippled_params = {
        trace: false,
        trusted: true,
        local_signing: true,
        secure: true,
        local_fee: true,
        fee_cushion: 1.5,
        servers: [{
            host: 's1.ripple.com',
            port: 443,
            secure: true
        }]
    };
    /**
     * Remote stellard server connection info
     * @const 
     */
    var stellard_params = {
        trace: false,
        trusted: true,
        local_signing: true,
        secure: true,
        local_fee: true,
        fee_cushion: 1.5,
        servers: [{
            host: 'live.stellar.org',
            port: 9001,
            secure: true
        }]
    };
    /**
     * Ripple Gateways "certified": http://www.xrpga.org/gateways.html
     * Issuing address & other info obtained from:
     * https://ripple.com/forum/viewforum.php?f=14
     * https://xrptalk.org/topic/272-help-to-identify-money-issuers-inside-the-network/
     * @const 
     */ 
    var gateways = {
        CryptoCab: {
            address: "rMvQCheixifmCK6GPFGafRGu17Hu4y8cLS",
            certified: true
        },
        Bitstamp: {
            address: "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
            certified: true
        },
        Justcoin: {
            address: "rJHygWcTLVpSXkowott6kzgZU6viQSVYM1",
            certified: true
        },
        SnapSwap: {
            address: "rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q",
            certified: true
        },
        rippleCN: {
            address: "rnuF96W4SZoCJmbHYBFoJZpR8eCaxNvekK",
            certified: true
        },
        RippleChina: {
            address: "razqQKzJRdB4UxFPWf5NEpEG3WMkmwgcXA",
            certified: true
        },
        TheRockTrading: {
            address: "rLEsXccBGNR3UPuPu2hUXPjziKC3qKSBun",
            certified: true
        },
        rippleSingapore: {
            address: "r9Dr5xwkeLegBeXq6ujinjSBLQzQ1zQGjH",
            certified: true
        },
        btc2ripple: {
            address: "rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q",
            certified: true
        },
        Coinex: {
            address: "rsP3mgGb2tcYUrxiLFiHJiQXhsziegtwBc",
            certified: true
        },
        DividendRippler: {
            address: "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX",
            certified: false
        },
        RippleIsrael: {
            address: "rNPRNzBB92BVpAhhZr4iXDTveCgV5Pofm9",
            certified: false
        },
        Peercover: {
            address: "ra9eZxMbJrUcgV8ui7aPc161FgrqWScQxV",
            certified: false
        },
        RippleUnion: {
            address: "r3ADD8kXSUKHd6zTCKfnKT3zV9EZHjzp1S",
            certified: false
        },
        WisePass: {
            address: "rPDXxSZcuVL3ZWoyU82bcde3zwvmShkRyF",
            certified: false
        }
    };
    /** @const */
    var shared = {
        from: "rMvQCheixifmCK6GPFGafRGu17Hu4y8cLS",
        secret: "shZy5HgDcfMY9v1embCkrmU5jWH9y"
    };
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
        var sckt = new SockJS(socket_url);
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
            bridge.init_sockets();
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
     * Listen on the Ripple network for transactions.
     * Display payments and new offers as a live feed.
     * @constructor
     * @struct
     */
    function RippleReactor() {
        var self = this;
        this.tx_feed = $('#live-feed');
        this.remote = new ripple.Remote(rippled_params);
        this.remote.connect(function () {
            self.remote.on('transaction_all', self.parse_tx);
            self.remote.on('ledger_closed', self.parse_ledger);
        });
        /** @param {!Object} tx */
        this.parse_tx = function (tx) {
            // Format: ripple.com/wiki/RPC_API#transactions_stream_messages
            try {
                var amount, taker_gets, taker_pays, tx_string;
                if (tx.meta && tx.transaction && tx.transaction.TransactionType) {
                    switch (tx.transaction.TransactionType) {
                        // Payment transactions
                        case 'Payment':
                            amount = format(tx.transaction.Amount, true);
                            tx_string = amount.value.toString() + " " + amount.currency + " payment";
                            break;
                        // OfferCreate transactions
                        case 'OfferCreate':
                            taker_gets = format(tx.transaction.TakerGets, true);
                            taker_pays = format(tx.transaction.TakerPays, true);
                            tx_string = round_to(taker_gets.value, 5).toString() + " " + taker_gets.currency + " offered for " + round_to(taker_pays.value, 5).toString() + " " + taker_pays.currency;
                            break;
                    }
                    if (tx_string) {
                        self.tx_feed.text("transaction feed   ·   " + tx_string);
                    }
                }
            } catch (e) {
                console.log("Error parsing transaction stream:", e);
            }
        };
        this.parse_ledger = function (ledger) {

        };
    }
    /**
     * Query the Ripple network. Active requests that do not require
     * signatures should be included here.
     * @constructor
     * @param {string|null} account
     * @param {string|null} outlet
     */
    function RippleRequest(account, outlet) {
        var self = this;
        this.account = account;
        this.remote = new ripple.Remote(rippled_params);
        this.outlet = $('#display-ripple-balance');
        this.order_outlet = $('#display-ripple-orders');
        this.user_order_outlet = $('#user-ripple-open-orders');
        this.coin_outlet = $('#display-ripple-coin-balance');
        this.xrp = null;
        this.coins = {};
    }
    // Get XRP and coin balances in user's wallet
    RippleRequest.prototype.balance = function () {
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.xrp_balance();
                self.coin_balance();
            }
        });
    };
    RippleRequest.prototype.xrp_balance = function () {
        // {"command": "account_info", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_info(this.account, function (err, res) {
            if (err) {
                if (err.error == "remoteError") {
                    self.xrp = null;
                    self.display_balance("0");
                }
            } else {
                self.xrp = parseFloat(res.account_data.Balance) / Math.pow(10,6);
                self.display_balance(self.xrp, 'XRP');
            }
        });
    };
    RippleRequest.prototype.coin_balance = function () {
        // {"command": "account_lines", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_lines(this.account, function (err, res) {
            var position;
            if (err) {
                if (err.error == "remoteError") {
                    self.coins = {};
                    return null;
                }
            } else if (res != null && res != undefined) {
                self.coin_outlet.empty();
                if (res.lines && res.lines.length) {
                    for (var i = 0, len = res.lines.length; i < len; ++i) {
                        if (res.lines[i].balance) {
                            self.coins[res.lines[i].currency] = res.lines[i].balance;
                        }
                        self.display_balance(res.lines[i].balance || 0,
                                             res.lines[i].currency,
                                             position);
                    }
                    self.coin_outlet.show();
                }
            }
        });
    };
    RippleRequest.prototype.user_open_orders = function (book) {
        // {"command": "account_offers", "account": "rXXXXX..."}
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_account_offers(self.account, function (err, res) {
                    var taker, gets_issuer, pays_issuer, user_order_string, sequence, order_id;
                    if (err) {
                        if (err.error == "remoteError") {
                            return null;
                        }
                    } else {
                        if (res.offers && res.offers.length) {
                            sequence = [];
                            user_order_string = "<table><tr><th>Out</th><th>In</th></tr>";
                            for (var i = 0, len = res.offers.length; i < len; ++i) {
                                gets_issuer = format_issuer(res.offers[i].taker_gets);
                                pays_issuer = format_issuer(res.offers[i].taker_pays);
                                taker = {
                                    gets: format(res.offers[i].taker_gets, false),
                                    pays: format(res.offers[i].taker_pays, false)
                                };
                                taker.gets.currency = gets_issuer + taker.gets.currency;
                                taker.pays.currency = pays_issuer + taker.pays.currency;
                                order_id = res.offers[i].seq.toString();
                                user_order_string += "<tr id='" + order_id + "'><td>" + taker.gets.value + " " + taker.gets.currency + "</td><td>" + taker.pays.value + " " + taker.pays.currency + "</td></tr>";
                                sequence.push(order_id);
                            }
                            user_order_string += "</table>";
                            self.user_order_outlet.empty().append(user_order_string);
                            for (i = 0, len = sequence.length; i < len; ++i) {
                                $('#' + sequence[i]).click(function (event) {
                                    var seq, tx_params, assembly;
                                    event.preventDefault();
                                    seq = parseInt($(this).attr('id'));
                                    tx_params = {
                                        address: wallet.address,
                                        details: {type: "OfferCancel", sequence: seq}
                                    };
                                    self.remote.set_secret(wallet.address, wallet.secret);
                                    assembly = new AssembleTx(self.remote.transaction(), tx_params);
                                    assembly.build();
                                    assembly.submit();
                                });
                            }
                        }
                    } 
                });
            }
        });
    };
    /**
     * @param {string|number|null} data
     * @param {string|null} currency
     */
    RippleRequest.prototype.display_balance = function (data, currency) {
        var output;
        if (data === "Unfunded account") {
            return this.outlet.html(data).show();
        }
        data = round_to(data, 4) || null;
        if (currency) {
            if (currency === 'XRP') {
                if (data) {
                    output = data + ' ' + currency;
                    if ($('#display-ripple-balance').val() === "Connecting...") {
                        this.outlet.html(output).show();
                    } else {
                        this.outlet.html(output).show();
                    }
                } else {
                    this.outlet.html("Connecting...").show();
                }
            } else {
                output = data + ' ' + currency;
                this.coin_outlet.append(output);
            }
        }
    };
    RippleRequest.prototype.order_book = function (selected, limit) {
        // {"command": "book_offers", "taker_pays": {"currency": "BTC", "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B"}, "taker_gets": {"currency": "XRP", "issuer": ""}, "limit": 3}
        $('#loading-circle')
            .css('padding-left', ($('#display-ripple-orders').width()-25).toString())
            .show();
        var self = this;
        selected = selected || $("option:selected", '#order-book-picker').val();
        var currencies = selected.split('-');
        var currency1 = currencies[0];
        var currency2 = currencies[1];
        // limit parameter seems to be broken...
        var req = {
            limit: limit || parseInt($("#order-book-limit").val()) || 15
        };
        if (currency1.length > 3) {
            currency1 = currency1.split('.');
            req.gets = {
                'currency': currency1[0],
                'issuer': gateways[currency1[1]].address
            }
        } else {
            req.gets = {
                'currency': currency1,
                'issuer': ''
            }
        }
        if (currency2.length > 3) {
            currency2 = currency2.split('.');
            req.pays = {
                'currency': currency2[0],
                'issuer': gateways[currency2[1]].address
            }
        } else {
            req.pays = {
                'currency': currency2,
                'issuer': ''
            }
        }
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_book_offers(req, function (err, res) {
                    if (err) {
                        pp(err);
                    } else {
                        self.display_order_book(res.offers, req.limit);
                    }
                });
            }
        });
    };
    /**
     * @param {string|null} data
     */
    RippleRequest.prototype.display_order_book = function (offers, limit) {
        var asking, offering, price, order_book_table;
        var pays, gets, pays_xrp, gets_xrp, book;
        if (offers && offers.length) {
            book = [];
            if (typeof offers[0].TakerPays == 'string') {
                pays_currency = 'XRP';    
            } else {
                pays_currency = offers[0].TakerPays.currency;
            }
            if (typeof offers[0].TakerGets == 'string') {
                gets_currency = 'XRP';    
            } else {
                gets_currency = offers[0].TakerGets.currency;
            }
            limit = Math.min(limit, offers.length);
            for (var i = 0; i < limit; ++i) {
                if (pays_currency === 'XRP') {
                    pays = undropify(offers[i].TakerPays, 5);
                } else {
                    pays = Number(round_to(offers[i].TakerPays.value, 5));    
                }
                if (gets_currency === 'XRP') {
                    gets = undropify(offers[i].TakerGets, 5);
                } else {
                    gets = Number(round_to(offers[i].TakerGets.value, 5));    
                }
                book.push([pays, gets, round_to(gets / pays, 5)]);
            }
            book.sort(function (a, b) {
                return a[2] - b[2]; // sort by price
            });
            order_book_table = $('<table />');
            order_book_table.append($('<tr />')
                .append($('<th />').text("Seller wants"))
                .append($('<th />').text("In return for"))
                .append($('<th />').text("Price"))
            );
            for (var i = 0; i < limit; ++i) {
                asking = book[i][0].toString() + ' ' + pays_currency;
                offering = book[i][1].toString() + ' ' + gets_currency;
                price = book[i][2].toString() + ' ' + gets_currency + '/' + pays_currency;
                order_book_table.append($('<tr />')
                    .append($('<td />').text(offering))
                    .append($('<td />').text(asking))
                    .append($('<td />').text(price))
                );
            }
            $('#display-ripple-orders').empty().append(order_book_table).show();
        } else {
            $('#display-ripple-orders').hide();
        }
        $('#loading-circle').hide();
    };
    /**
     * Build and submit a transaction to the Ripple network. All actions
     * requiring a signature should be included here.
     * @constructor
     */
    function AssembleTx(tx, params) {
        this.tx = tx;
        this.params = params;
        this.tx_results = $('#transaction-results');
    }
    AssembleTx.prototype.build = function () {
        switch (this.params.details.type) {
            case 'Payment':
                this.payment();
                break;
            case 'OfferCreate':
                this.offer_create();
                break;
            case 'OfferCancel':
                this.offer_cancel();
                break;
            case 'TrustSet':
                this.trust_set();
                break;
            default:
                console.log("Unknown transaction type:",
                            this.params.details.type);
        }
    };
    AssembleTx.prototype.payment = function () {
        // ./rippled <secret> '{"TransactionType":"Payment","Account":"<address>","Amount":"<drops>","Destination":"<account>" }'
        if (this.params.details.currency == 'XRP') {
            this.params.details.issuer = '';
        }
        this.tx.payment({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    AssembleTx.prototype.offer_create = function () {
        this.tx.offer_create({
            from: this.params.address,
            taker_pays: this.params.details.taker_pays,
            taker_gets: this.params.details.taker_gets
        });
    };
    AssembleTx.prototype.offer_cancel = function () {
        this.tx.offer_cancel(this.params.address, this.params.details.sequence);
    };
    AssembleTx.prototype.trust_set = function () {
        this.tx.trust_set({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    AssembleTx.prototype.submit = function () {
        var self = this;
        this.tx.submit(function (err, res) {
            if (err) {
                console.log(err);
            } else {
                if (res.engine_result_code === 0) {
                    self.display_balance(res);
                }
            }
        });
    };
    AssembleTx.prototype.display_balance = function (data) {
        this.tx_results.html(data).show();
        var rr = new RippleRequest(this.params.address);
        rr.user_open_orders();
    };
    /**
     * Listen on the Stellar network for transactions.
     * Display payments and new offers as a live feed.
     * @constructor
     * @struct
     */
    function StellarReactor() {
        var self = this;
        this.tx_feed = $('#live-feed');
        this.remote = new stellar.Remote(stellard_params);
        this.remote.connect(function () {
            self.remote.on('transaction_all', self.parse_tx);
            self.remote.on('ledger_closed', self.parse_ledger);
        });
        /** @param {!Object} tx */
        this.parse_tx = function (tx) {
            // Format: ripple.com/wiki/RPC_API#transactions_stream_messages
            try {
                var amount, taker_gets, taker_pays, tx_string;
                if (tx.meta && tx.transaction && tx.transaction.TransactionType) {
                    switch (tx.transaction.TransactionType) {
                        // Payment transactions
                        case 'Payment':
                            amount = format(tx.transaction.Amount, true);
                            tx_string = amount.value.toString() + " " + amount.currency + " payment";
                            break;
                        // OfferCreate transactions
                        case 'OfferCreate':
                            taker_gets = format(tx.transaction.TakerGets, true);
                            taker_pays = format(tx.transaction.TakerPays, true);
                            tx_string = round_to(taker_gets.value, 5).toString() + " " + taker_gets.currency + " offered for " + round_to(taker_pays.value, 5).toString() + " " + taker_pays.currency;
                            break;
                    }
                    if (tx_string) {
                        self.tx_feed.text("transaction feed   ·   " + tx_string);
                    }
                }
            } catch (e) {
                console.log("Error parsing transaction stream:", e);
            }
        };
        this.parse_ledger = function (ledger) {

        };
    }
    /**
     * Query the Stellar network. Active requests that do not require
     * signatures should be included here.
     * @constructor
     * @param {string|null} account
     * @param {string|null} outlet
     */
    function StellarRequest(account, outlet) {
        var self = this;
        this.account = account;
        this.remote = new stellar.Remote(stellard_params);
        this.outlet = $('#display-stellar-balance');
        this.order_outlet = $('#display-stellar-orders');
        this.user_order_outlet = $('#user-stellar-open-orders');
        this.coin_outlet = $('#display-stellar-coin-balance');
        this.xrp = null;
        this.coins = {};
    }
    // Get XRP and coin balances in user's wallet
    StellarRequest.prototype.balance = function () {
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.xrp_balance();
                self.coin_balance();
            }
        });
    };
    StellarRequest.prototype.xrp_balance = function () {
        // {"command": "account_info", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_info(this.account, function (err, res) {
            if (err) {
                if (err.error == "remoteError") {
                    self.xrp = null;
                    self.display_balance(0, 'STR');
                }
            } else {
                self.xrp = parseFloat(res.account_data.Balance) / Math.pow(10,6);
                self.display_balance(self.xrp, 'STR');
            }
        });
    };
    StellarRequest.prototype.coin_balance = function () {
        // {"command": "account_lines", "account": "rXXXXXX..."}
        var self = this;
        this.remote.request_account_lines(this.account, function (err, res) {
            var position;
            if (err) {
                if (err.error == "remoteError") {
                    self.coins = {};
                    return null;
                }
            } else if (res != null && res != undefined) {
                self.coin_outlet.empty();
                if (res.lines && res.lines.length) {
                    for (var i = 0, len = res.lines.length; i < len; ++i) {
                        if (res.lines[i].balance) {
                            self.coins[res.lines[i].currency] = res.lines[i].balance;
                        }
                        self.display_balance(res.lines[i].balance || 0,
                                             res.lines[i].currency,
                                             position);
                    }
                    self.coin_outlet.show();
                }
            }
        });
    };
    StellarRequest.prototype.user_open_orders = function (book) {
        // {"command": "account_offers", "account": "rXXXXX..."}
        var self = this;
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_account_offers(self.account, function (err, res) {
                    var taker, gets_issuer, pays_issuer, user_order_string, sequence, order_id;
                    if (err) {
                        if (err.error == "remoteError") {
                            return null;
                        }
                    } else {
                        if (res.offers && res.offers.length) {
                            sequence = [];
                            user_order_string = "<table><tr><th>Out</th><th>In</th></tr>";
                            for (var i = 0, len = res.offers.length; i < len; ++i) {
                                gets_issuer = format_issuer(res.offers[i].taker_gets);
                                pays_issuer = format_issuer(res.offers[i].taker_pays);
                                taker = {
                                    gets: format(res.offers[i].taker_gets, false),
                                    pays: format(res.offers[i].taker_pays, false)
                                };
                                taker.gets.currency = gets_issuer + taker.gets.currency;
                                taker.pays.currency = pays_issuer + taker.pays.currency;
                                order_id = res.offers[i].seq.toString();
                                user_order_string += "<tr id='" + order_id + "'><td>" + taker.gets.value + " " + taker.gets.currency + "</td><td>" + taker.pays.value + " " + taker.pays.currency + "</td></tr>";
                                sequence.push(order_id);
                            }
                            user_order_string += "</table>";
                            self.user_order_outlet.empty().append(user_order_string);
                            for (i = 0, len = sequence.length; i < len; ++i) {
                                $('#' + sequence[i]).click(function (event) {
                                    var seq, tx_params, assembly;
                                    event.preventDefault();
                                    seq = parseInt($(this).attr('id'));
                                    tx_params = {
                                        address: wallet.address,
                                        details: {type: "OfferCancel", sequence: seq}
                                    };
                                    self.remote.set_secret(wallet.address, wallet.secret);
                                    assembly = new AssembleTx(self.remote.transaction(), tx_params);
                                    assembly.build();
                                    assembly.submit();
                                });
                            }
                        }
                    } 
                });
            }
        });
    };
    /**
     * @param {string|number|null} data
     * @param {string|null} currency
     */
    StellarRequest.prototype.display_balance = function (data, currency) {
        var output;
        if (data === "Unfunded account") {
            return this.outlet.html(data).show();
        }
        data = round_to(data, 4) || null;
        if (currency) {
            if (currency === 'STR') {
                if (data) {
                    output = data + ' ' + currency;
                    if ($('#display-stellar-balance').val() === "Connecting...") {
                        this.outlet.html(output).show();
                    } else {
                        this.outlet.html(output).show();
                    }
                } else {
                    this.outlet.html("Connecting...").show();
                }
            } else {
                output = data + ' ' + currency;
                this.coin_outlet.append(output);
            }
        }
    };
    StellarRequest.prototype.order_book = function (selected, limit) {
        // {"command": "book_offers", "taker_pays": {"currency": "BTC", "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B"}, "taker_gets": {"currency": "XRP", "issuer": ""}, "limit": 3}
        $('#loading-circle')
            .css('padding-left', ($('#display-stellar-orders').width()-25).toString())
            .show();
        var self = this;
        selected = selected || $("option:selected", '#order-book-picker').val();
        var currencies = selected.split('-');
        var currency1 = currencies[0];
        var currency2 = currencies[1];
        // limit parameter seems to be broken...
        var req = {
            limit: limit || parseInt($("#order-book-limit").val()) || 15
        };
        if (currency1.length > 3) {
            currency1 = currency1.split('.');
            req.gets = {
                'currency': currency1[0],
                'issuer': gateways[currency1[1]].address
            }
        } else {
            req.gets = {
                'currency': currency1,
                'issuer': ''
            }
        }
        if (currency2.length > 3) {
            currency2 = currency2.split('.');
            req.pays = {
                'currency': currency2[0],
                'issuer': gateways[currency2[1]].address
            }
        } else {
            req.pays = {
                'currency': currency2,
                'issuer': ''
            }
        }
        this.remote.connect(function (err) {
            if (err) {
                return console.log("Remote couldn't connect", err);
            } else {
                self.remote.request_book_offers(req, function (err, res) {
                    if (err) {
                        pp(err);
                    } else {
                        self.display_order_book(res.offers, req.limit);
                    }
                });
            }
        });
    };
    /**
     * @param {string|null} data
     */
    StellarRequest.prototype.display_order_book = function (offers, limit) {
        var asking, offering, price, order_book_table;
        var pays, gets, pays_xrp, gets_xrp, book;
        if (offers && offers.length) {
            book = [];
            if (typeof offers[0].TakerPays == 'string') {
                pays_currency = 'STR';    
            } else {
                pays_currency = offers[0].TakerPays.currency;
            }
            if (typeof offers[0].TakerGets == 'string') {
                gets_currency = 'STR';    
            } else {
                gets_currency = offers[0].TakerGets.currency;
            }
            limit = Math.min(limit, offers.length);
            for (var i = 0; i < limit; ++i) {
                if (pays_currency === 'STR') {
                    pays = undropify(offers[i].TakerPays, 5);
                } else {
                    pays = Number(round_to(offers[i].TakerPays.value, 5));    
                }
                if (gets_currency === 'STR') {
                    gets = undropify(offers[i].TakerGets, 5);
                } else {
                    gets = Number(round_to(offers[i].TakerGets.value, 5));    
                }
                book.push([pays, gets, round_to(gets / pays, 5)]);
            }
            book.sort(function (a, b) {
                return a[2] - b[2]; // sort by price
            });
            order_book_table = $('<table />');
            order_book_table.append($('<tr />')
                .append($('<th />').text("Seller wants"))
                .append($('<th />').text("In return for"))
                .append($('<th />').text("Price"))
            );
            for (var i = 0; i < limit; ++i) {
                asking = book[i][0].toString() + ' ' + pays_currency;
                offering = book[i][1].toString() + ' ' + gets_currency;
                price = book[i][2].toString() + ' ' + gets_currency + '/' + pays_currency;
                order_book_table.append($('<tr />')
                    .append($('<td />').text(offering))
                    .append($('<td />').text(asking))
                    .append($('<td />').text(price))
                );
            }
            $('#display-stellar-orders').empty().append(order_book_table).show();
        } else {
            $('#display-stellar-orders').hide();
        }
        $('#loading-circle').hide();
    };
    /**
     * Build and submit a transaction to the Ripple network. All actions
     * requiring a signature should be included here.
     * @constructor
     */
    function StellarAssembleTx(tx, params) {
        this.tx = tx;
        this.params = params;
        this.tx_results = $('#transaction-results');
    }
    StellarAssembleTx.prototype.build = function () {
        switch (this.params.details.type) {
            case 'Payment':
                this.payment();
                break;
            case 'OfferCreate':
                this.offer_create();
                break;
            case 'OfferCancel':
                this.offer_cancel();
                break;
            case 'TrustSet':
                this.trust_set();
                break;
            default:
                console.log("Unknown transaction type:",
                            this.params.details.type);
        }
    };
    StellarAssembleTx.prototype.payment = function () {
        // ./rippled <secret> '{"TransactionType":"Payment","Account":"<address>","Amount":"<drops>","Destination":"<account>" }'
        if (this.params.details.currency == 'STR') {
            this.params.details.issuer = '';
        }
        this.tx.payment({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    StellarAssembleTx.prototype.offer_create = function () {
        this.tx.offer_create({
            from: this.params.address,
            taker_pays: this.params.details.taker_pays,
            taker_gets: this.params.details.taker_gets
        });
    };
    StellarAssembleTx.prototype.offer_cancel = function () {
        this.tx.offer_cancel(this.params.address, this.params.details.sequence);
    };
    StellarAssembleTx.prototype.trust_set = function () {
        this.tx.trust_set({
            from: this.params.address,
            to: this.params.details.to,
            amount: this.params.details.amount
        });
    };
    StellarAssembleTx.prototype.submit = function () {
        var self = this;
        this.tx.submit(function (err, res) {
            if (err) {
                console.log(err);
            } else {
                if (res.engine_result_code === 0) {
                    self.display_balance(res);
                }
            }
        });
    };
    StellarAssembleTx.prototype.display_balance = function (data) {
        this.tx_results.html(data).show();
        var rr = new StellarRequest(this.params.address);
        rr.user_open_orders();
    };
    /**
     * Utility functions
     */
    function pp(msg) {
        if (typeof msg === 'object') {
            console.log(JSON.stringify(msg, null, 3));
        } else {
            console.log(msg);
        }
    }
    /** @param {!Object} self */
    function check_issuer(self) {
        if (self.value === 'XRP') {
            $(self).next('.select-issuer').hide();
        } else {
            $(self).next('.select-issuer').show();
        }
    }
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
     * @param {string|Object} taker
     * @param {boolean} use_drops
     * @return {string}
     */
    function format(taker, use_drops) {
        use_drops = use_drops || true;
        if (typeof taker === 'string') {
            taker = {
                currency: 'XRP',
                issuer: '',
                value: (use_drops) ? undropify(parseInt(taker)) : taker
            };
        }
        taker.value = round_to(taker.value, 5).toString();
        return taker;
    }
    /**
     * @param {string|Object} taker
     * @return {string}
     */
    function format_issuer(taker) {
        var issuer = '';
        if (typeof taker !== 'string') {
            for (var name in gateways) {
                var gateway = gateways[name];
                if (gateway.address == taker.issuer) {
                    issuer = name;
                    break;
                }
            }
            // TODO search db for user-issued
        }
        return issuer + ' ';
    }
    /**
     * @param {string} currency
     * @param {number} value
     */
    function dropify(currency, value) {
        if (currency === 'XRP') {
            return Math.round(value * Math.pow(10, 6));
        } else {
            return value;
        }
    }
    /**
     * @param {number} value
     */
    function undropify(value) {
        return value / Math.pow(10, 6);
    }
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
    function Bridge() {
        var self = this;
        this.digits = 8;
        this.ripple_address = $('#ripple-wallet-address').text() || '';
        this.stellar_address = $('#stellar-wallet-address').text() || '';
        this.tx_params = wallet;
    }
    /**
     * External event listener setup (e.g., Ripple network).
     */
    Bridge.prototype.sync = function () {
        var rrequest = new RippleRequest(this.ripple_address);
        var srequest = new StellarRequest(this.stellar_address);
        rrequest.balance();
        srequest.balance();
    };
    /**
     * DOM manipulation, visual tweaks, and event handlers that do not
     * involve websockets.
     */
    Bridge.prototype.tweaks = function () {
        var self = this;
        $("body").css('background-color', '#e9eaed');
        // $('#wallet-block').height($('#tabs-block').height() - 50);
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
    Bridge.prototype.exhaust = function () {
        var self = this;
        return this;
    };
    /**
     * Listeners for incoming websocket signals.
     */
    Bridge.prototype.intake = function () {
        var self = this;
        // socket.on('notify', function (res) {
        //     $('#live-feed').text(res.feed);
        //     self.sync();
        //     var clear_feed = setTimeout(function () {
        //         $('#live-feed').hide();
        //     }, 10000);
        // });
        return this;
    };
    /**
     * Create new Ripple wallets.
     */
    Bridge.prototype.create_ripple_wallet = function () {
        fresh_wallet = RippleWallet.generate();
        this.ripple_address = fresh_wallet.address;
        $('#ripple-wallet-address').text(fresh_wallet.address);
        this.tx_params.address = fresh_wallet.address;
        // this.fund_ripple_wallet(fresh_wallet.address);
        return fresh_wallet;
    };
    /**
     * Create new Stellar wallets.
     */
    Bridge.prototype.create_stellar_wallet = function () {
        fresh_wallet = RippleWallet.generate();
        stellar_tinybike = 'gN4b4vksvgwqCEuxuinuP6pU5i8FUAa9Uo';
        fresh_wallet.address = stellar_tinybike;
        this.stellar_address = fresh_wallet.address;
        $('#stellar-wallet-address').text(fresh_wallet.address);
        this.tx_params.address = fresh_wallet.address;
        // this.fund_wallet(fresh_wallet.address);
        return fresh_wallet;
    };
    /** @param {string} address */
    Bridge.prototype.fund_ripple_wallet = function (address) {
        // Fund reserve (20 XRP) for new Ripple wallets
        var welfare_tx_params = welfare;
        welfare_tx_params.details.to = address;
        var remote = new ripple.Remote(rippled_params);
        remote.connect(function () {
            remote.set_secret(welfare.from, welfare.secret);
            var assembly = new AssembleTx(remote.transaction(), welfare_tx_params);
            assembly.build();
            assembly.submit();
        });
    };
    Bridge.prototype.charts = function () {

    };
    /**
     * Set up socket listeners on ready signal.
     */
    Bridge.prototype.init_sockets = function () {
        this.intake().exhaust();
    };
    _exports.init = function () {
        $(document).ready(function () {
            var rreactor, sreactor, offers, rr, rr2, sr, sr2;
            window.bridge = new Bridge();
            window.socket = new sockjs('bridge', true);
            socket.connect();
            bridge.tweaks();
            bridge.create_ripple_wallet();
            bridge.create_stellar_wallet();
            rreactor = new RippleReactor();
            sreactor = new StellarReactor();
            offers = $('#user-offer-list');
            offers.empty();
            rr = new RippleRequest(wallet.address);
            rr.user_open_orders(true);
            offers.show();
            rr2 = new RippleRequest(wallet.address);
            rr2.order_book();
            // sr = new StellarRequest(wallet.address);
            // sr.user_open_orders(true);
            // offers.show();
            // sr2 = new StellarRequest(wallet.address);
            // sr2.order_book();
            bridge.charts();
            bridge.sync();
            setTimeout(function () { bridge.sync(); }, 10000);
        });
    };
    /**
     * Ripple wallet generator
     * @see https://github.com/stevenzeiler/ripple-wallet/
     * @author zeiler.steven@gmail.com (Steven Zeiler)
     */
    var sjcl = ripple.sjcl;
    var Base58Utils = (function () {
        var alphabets = {
            'ripple': "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz",
            'bitcoin': "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        };
        var SHA256 = function (bytes) {
            return sjcl.codec.bytes.fromBits(sjcl.hash.sha256.hash(sjcl.codec.bytes.toBits(bytes)));
        };
        return {
            /**
             * @param {Array.<string>} input
             * @return {string}
             */
            encode_base: function (input, alphabetName) {
                var alphabet = alphabets[alphabetName || 'ripple'],
                    base = new sjcl.bn(alphabet.length),
                    bi = sjcl.bn.fromBits(sjcl.codec.bytes.toBits(input)),
                    buffer = [];
                while (bi.greaterEquals(base)) {
                    var mod = bi.mod(base);
                    buffer.push(alphabet[mod.limbs[0]]);
                    bi = bi.div(base);
                }
                buffer.push(alphabet[bi.limbs[0]]);
                // Convert leading zeros too.
                for (var i = 0; i != input.length && !input[i]; i += 1) {
                    buffer.push(alphabet[0]);
                }
                return buffer.reverse().join("");
            },
            /**
             * @param {string} input
             * @return {Array.<string>|null}
             */
            decode_base: function (input, alphabetName) {
                var alphabet = alphabets[alphabetName || 'ripple'],
                    base = new sjcl.bn(alphabet.length),
                    bi = new sjcl.bn(0);
                var i;
                while (i != input.length && input[i] === alphabet[0]) {
                    i += 1;
                }
                for (i = 0; i != input.length; i += 1) {
                    var v = alphabet.indexOf(input[i]);
                    if (v < 0) {
                        return null;
                    }
                    bi = bi.mul(base).addM(v);
                }
                var bytes = sjcl.codec.bytes.fromBits(bi.toBits()).reverse();
                // Remove leading zeros
                while (bytes[bytes.length - 1] === 0) {
                    bytes.pop();
                }
                // Add the right number of leading zeros
                for (i = 0; input[i] === alphabet[0]; i++) {
                    bytes.push(0);
                }
                bytes.reverse();
                return bytes;
            },
            /**
             * @param {Array.<string>} input
             * @return {string}
             */
            encode_base_check: function (version, input, alphabet) {
                var buffer = [].concat(version, input);
                var check = SHA256(SHA256(buffer)).slice(0, 4);
                return Base58Utils.encode_base([].concat(buffer, check), alphabet);
            },
            /**
             * @param {string} input
             * @return {NaN|number}
             */
            decode_base_check: function (version, input, alphabet) {
                var buffer = Base58Utils.decode_base(input, alphabet);
                if (!buffer || buffer[0] !== version || buffer.length < 5) {
                    return NaN;
                }
                var computed = SHA256(SHA256(buffer.slice(0, -4))).slice(0, 4),
                    checksum = buffer.slice(-4);
                var i;
                for (i = 0; i != 4; i += 1)
                    if (computed[i] !== checksum[i])
                        return NaN;
                return buffer.slice(1, -4);
            }
        };
    })();
    var RippleWallet = (function () {
        function append_int(a, i) {
            return [].concat(a, i >> 24, (i >> 16) & 0xff, (i >> 8) & 0xff, i & 0xff);
        }
        function firstHalfOfSHA512(bytes) {
            return sjcl.bitArray.bitSlice(
                sjcl.hash.sha512.hash(sjcl.codec.bytes.toBits(bytes)),
                0, 256
            );
        }
        function SHA256_RIPEMD160(bits) {
            return sjcl.hash.ripemd160.hash(sjcl.hash.sha256.hash(bits));
        }
        return function (seed) {
            this.seed = Base58Utils.decode_base_check(33, seed);
            if (!this.seed) {
                throw "Invalid seed.";
            }
            this.getAddress = function (seq) {
                seq = seq || 0;
                var private_gen, public_gen, i = 0;
                do {
                    // Compute the hash of the 128-bit seed and the sequence number
                    private_gen = sjcl.bn.fromBits(firstHalfOfSHA512(append_int(this.seed, i)));
                    i++;
                    // If the hash is equal to or greater than the SECp256k1 order, increment sequence and try agin
                } while (!sjcl.ecc.curves.c256.r.greaterEquals(private_gen));
                // Compute the public generator using from the private generator on the elliptic curve
                public_gen = sjcl.ecc.curves.c256.G.mult(private_gen);
                var sec;
                i = 0;
                do {
                    // Compute the hash of the public generator with sub-sequence number
                    sec = sjcl.bn.fromBits(firstHalfOfSHA512(append_int(append_int(public_gen.toBytesCompressed(), seq),
                        i)));
                    i++;
                    // If the hash is equal to or greater than the SECp256k1 order, increment the sequence and retry
                } while (!sjcl.ecc.curves.c256.r.greaterEquals(sec));
                // Treating this hash as a private key, compute the corresponding public key as an EC point. 
                var pubKey = sjcl.ecc.curves.c256.G.mult(sec).toJac().add(public_gen).toAffine();
                // Finally encode the EC public key as a ripple address using SHA256 and then RIPEMD160
                return Base58Utils.encode_base_check(0, sjcl.codec.bytes.fromBits(SHA256_RIPEMD160(sjcl.codec.bytes.toBits(
                    pubKey.toBytesCompressed()))));
            };
        };
    })();
    RippleWallet.generate = function () {
        for (var i = 0; i < 8; i++) {
            sjcl.random.addEntropy(Math.random(), 32, "Math.random()");
        }
        // Generate a 128-bit master key that can be used to make any number of private / public key pairs and accounts
        var masterkey = Base58Utils.encode_base_check(33, sjcl.codec.bytes.fromBits(sjcl.random.randomWords(4)));
        address = new RippleWallet(masterkey);
        return {
            address: address.getAddress(),
            secret: masterkey
        };
    };
    return _exports;
}(BRIDGE || {}, ripple, stellar, jQuery));
