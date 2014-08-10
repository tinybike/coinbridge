# CoinFish
### Functional Specification

Jack Peterson

Last Updated: August 1, 2014

**- CONFIDENTIAL -**

&copy; 2014 Dyffy, Inc.  All Rights Reserved.

## Overview

**CoinFish** (<http://coin.fish>) is a *gateway* service that converts Bitcoin deposits to either Bitcoin IOUs, or to the native currencies of the Ripple and/or Stellar financial networks.

**This is a draft specification.**  Multiple revisions of the wording and content are expected before it is finalized.  The user interfaces and screen layouts are shown here for illustration.  The actual look and feel will be created iteratively, driven by input from users and/or designers.

This spec covers the user's experience when they interact with **CoinFish**.  Technical implementation details are not discussed here.

## Use Cases

Jimmy-Ray is a new entrant to the Stellar network.  He wants to convert his Bitcoins to *Stellars* (STR), the Stellar network's internal currency.  Stellar launched on July 31 and no other gateways exist yet.  Therefore, Jimmy-Ray's only options are to buy from a private seller, or to use **CoinFish**.  Private sales are a hassle to set up, and Jimmy-Ray knows that, as a non-technical user, his likelihood of being cheated is high.  So, he goes to the **CoinFish** website.

1. First, Jimmy-Ray goes to the **CoinFish** website and enters his Stellar address.  This is immediately saved by **CoinFish**, which creates a new account/address within its `bitcoind`, matching this Stellar address.

2. Next, he copies the newly-generated **CoinFish** Bitcoin address to his Bitcoin client, enters the amount that he wants to deposit, then he clicks "Send".

3. **CoinFish** receives a notification from `bitcoind` that the deposit has occurred, which is now displayed as *pending* on the website.

4. **CoinFish** detects that Jimmy-Ray's Bitcoin deposit has received 6 confirmations.  This usually takes 30 minutes to an hour.  The pending label is removed from his deposited Bitcoins, the Bitcoins are converted to Stellars (by us, at our specified conversion rate), and Jimmy-Ray's Stellars are immediately credited to his account.  The Stellars are now available for use anywhere on the Stellar network!

An equivalent use-case exists for converting Bitcoins to and from Ripple's internal currency, *Ripples* (XRP).  The principal difference is that a variety of gateways exist for Ripple, so Ripple traffic is expected to be secondary.

## Website Flowchart

    Splash Screen -> Home Page/Walkthrough -> Conversion-With-Handholding

Note that **CoinFish** is a single-page application, so to the user, these "screens" all occur at the same address, <http://coin.fish>.

## Screen-by-Screen Specification

### Splash Screen

Pretty marketing screen with the **CoinFish** logo.

### Home Page/Walkthrough

The user is presented with four buttons:

- Convert Bitcoins to Stellars
- Convert Bitcoins to Ripples
- Convert Stellars to Bitcoins
- Convert Ripples to Bitcoins

### Conversion-With-Handholding

#### Convert Bitcoins to Stellars

    Enter your Stellar address: ___________________

*Stellar-address labeled account/address created in bitcoind: 1E6Z1qQ8yPMFU4LSPqorwXw1FPwSX3H8NX*

    Send the Bitcoins you want to convert to Stellars to this Bitcoin address:
    1E6Z1qQ8yPMFU4LSPqorwXw1FPwSX3H8NX

*User sends 1 Bitcoin*

    Your deposit of 1 BTC has been received!  Once it has received 6 confirmations, your Bitcoins will be converted to Stellars.  (Click here to cancel this conversion, if you meant to do something else!)

*Waiting for confirmations*

    Stellar Wallet
    --------------
    0 STR
    1 BTC (pending, 0 confirmations) [cancel conversion to STR]

*6 confirmations received!  User's BTC deposit is moved into CoinFish's Bitcoin account.  10000 STR (or whatever the appropriate number is) is moved from CoinFish's Stellar account into the user's Stellar account.*

    Stellar Wallet
    --------------
    10000 STR
    0 BTC

The Stellars are now accessible anywhere on the Stellar network, not just from CoinFish.

#### Convert Bitcoins to Ripples

The same as the above section, except with XRP instead of STR.

#### Convert Stellars to Bitcoins

    Enter your Bitcoin address: ______________________

*Our Postgres database creates an association between this Bitcoin address and a newly-generated Stellar address, gN4b4vksvgwqCEuxuinuP6pU5i8FUAa9Uo*

    Send the Stellars you want to convert to Bitcoins to this Stellar address:
    gN4b4vksvgwqCEuxuinuP6pU5i8FUAa9Uo

*User sends 10000 STR.  CoinFish calculates that the user should receive 0.995 BTC after the conversion.*

    Your deposit of 10000 STR has been received!  Are you sure you want to convert this deposit to 0.995 BTC and send it to <your BTC address>?
    [Yes] [No]

#### Convert Ripples to Bitcoins

The same as above, except with XRP instead of STR.

## What We're Not Doing

**CoinFish** does *not* include, or intend to include, support for deposits from or withdrawls to fiat currencies, such as U.S. dollars.  This exclusion is made primarily for legal/regulatory reasons.

For security reasons, **CoinFish** does *not* store Bitcoins for users.  **CoinFish** accepts Bitcoin deposits solely to convert them immediately to Ripples/Stellars, which are credited to the depositor's account on the Ripple/Stellar networks.  **CoinFish** never holds BTC/XRP/STR in a user's name.  In the event that **CoinFish** ever suffers a security breach, the only funds at risk of being stolen are those owned by the company itself.

## Things We'd Like To Add After Launch

1. Ripple and Stellar exchanges

2. Social networking features: friends, profiles, Facebook connect, etc.

## Open Issues

1. Should we take a cut of deposits?  Withdrawals?  Both?

2. This all assumes we use (abuse?) the Ripple and Stellar public websockets, `wss://s1.ripple.com` and `wss://live.stellar.org`, respectively. If it's possible to get `stellard` running on our server, we would have completely decentralized accounting.

3. Do we want to support Ripple gateway actions at all, or just Stellars initially?  These communities are probably somewhat hostile to each other.
