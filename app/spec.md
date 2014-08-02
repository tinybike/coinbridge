<center><h2>CoinFish<br /><small>Functional Specification</small></h2>

Jack Peterson<br />
Last Updated: August 1, 2014

**- CONFIDENTIAL -**

&copy; 2014 Dyffy, Inc.  All Rights Reserved.</center>

## Overview

**CoinFish** (<http://coin.fish>) is a *gateway* service that converts Bitcoin deposits to either Bitcoin IOUs, or to the native currencies of the Ripple and/or Stellar financial networks.

**This is a draft specification.**  Multiple revisions of the wording and content are expected before it is finalized.  The user interfaces and screen layouts are shown here for illustration.  The actual look and feel will be created iteratively, driven by input from users and/or designers.

This spec covers the user's experience when they interact with **CoinFish**.  Technical implementation details are not discussed here.

## Use Cases

Jimmy-Ray is a new entrant to the Stellar network.  He wants to convert his Bitcoins to *Stellars* (STR), the Stellar network's internal currency.  Stellar launched on July 31 and no other gateways exist yet.  Therefore, Jimmy-Ray's only options are to buy from a private seller, or to use **CoinFish**.  Private sales are a hassle to set up, and Jimmy-Ray knows that, as a non-technical user, his likelihood of being cheated is high.  So, he goes to the **CoinFish** website.

1. First, Jimmy-Ray goes to the **CoinFish** website and enters his Stellar address.  This is immediately saved by **CoinFish**, which creates a new account/address within its `bitcoind`, matching this Stellar address.

2. Next, he copies the newly-generated **CoinFish** Bitcoin address to his Bitcoin client, enters the amount that he wants to deposit, then he clicks "Send".

3. **CoinFish** receives a notification from `bitcoind` that the deposit has occurred, which is now displayed as *pending* on the website.

4. **CoinFish** detects that Jimmy-Ray's Bitcoin deposit has received 6 confirmations.  This usually takes 30 minutes to an hour.  The pending label is removed from his deposited Bitcoins, and they are available for use.

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

    *Stellar-address labeled account/address created in bitcoind*

    Send the Bitcoins you want to convert to Stellars to this address:
    1E6Z1qQ8yPMFU4LSPqorwXw1FPwSX3H8NX

    *User sends 1 Bitcoin*

    Your deposit has been received!  Once it has received 6 confirmations, your Bitcoins will be converted to Stellars.  (Click here to cancel this conversion, if you meant to do something else!)

    
    

## What We're Not Doing

**CoinFish** does *not* include, or intend to include, support for deposits from or withdrawls to fiat currencies, such as U.S. dollars.  This exclusion is made primarily for legal/regulatory reasons.

## Things We'd Like To Add After Launch
