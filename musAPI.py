#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musAPI.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#

import cCoap


def musepa_get_loop():
    return cCoap.global_loop

def musepa_get_context():
    return cCoap.global_context

def musepa_query(address, payload, loop=cCoap.global_loop, context=cCoap.global_context):
    """
    address: target musepa query address
    payload: byte array coming from file, or from string
    
    loop: usually 
            asyncio.get_event_loop()
        My suggestion is to provide one manually -> see cCoap.py file
    context: usually is an 
            await Context.create_client_context()
        My suggestion is to provide one manually -> see cCoap.py file
    """
    return cCoap.coapCall(address, payload=payload, loop=loop, context=context)

def musepa_update(address, payload, loop=cCoap.global_loop, context=cCoap.global_context):
    """
    address: target musepa update address
    payload: byte array coming from file, or from string
    
    loop: usually 
            asyncio.get_event_loop()
        My suggestion is to provide one manually -> see cCoap.py file
    context: usually is an 
            await Context.create_client_context()
        My suggestion is to provide one manually -> see cCoap.py file
    """
    return cCoap.coapCall(address, verb="POST", payload=payload, loop=loop, context=context)

def musepa_subscribe(address, payload, loop=cCoap.global_loop, context=cCoap.global_context):
    """
    address: target musepa subscription address
    payload: byte array coming from file, or from string
    
    loop: usually 
            asyncio.get_event_loop()
        My suggestion is to provide one manually -> see cCoap.py file
    context: usually is an 
            await Context.create_client_context()
        My suggestion is to provide one manually -> see cCoap.py file
    """
    return cCoap.coapCall(address, verb="POST", payload=payload, loop=loop, context=context)

def musepa_observe(address, callback, loop=cCoap.global_loop, context=cCoap.global_context):
    """
    address: target musepa observation address
    callback: function to be used as callback
    
    loop: usually 
            asyncio.get_event_loop()
        My suggestion is to provide one manually -> see cCoap.py file
    context: usually is an 
            await Context.create_client_context()
        My suggestion is to provide one manually -> see cCoap.py file
    """
    return cCoap.coapObserve(address, callback=callback, loop=loop, context=context)

def musepa_unobserve(address, context, loop=cCoap.global_loop):
    """
    address: target musepa un-observation address
    
    loop: usually 
            asyncio.get_event_loop()
        My suggestion is to provide one manually -> see cCoap.py file
    context: usually is an 
            await Context.create_client_context()
        Compulsory manual here. Otherwise unsubscription will not be performed correctly
    """
    return cCoap.coapUnobserve(address, loop=loop, context=context)