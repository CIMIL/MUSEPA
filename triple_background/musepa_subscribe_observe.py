#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cCoap.py
#
#  Copyright 2020 Francesco Antoniazzi <francesco.antoniazzi@emse.fr>

import asyncio
import argparse

from aiocoap import Context, Message, GET, POST
from os.path import isfile

global_context = None
global_loop = asyncio.get_event_loop()
TOGGLE_NOTIF = False


def notification_callback(result):
    print("This is a notification!\n")


async def subscription_call(address, payload):
    global global_context
    global_context = await Context.create_client_context()

    subscription_address = "coap://{}/sparql/subscription".format(address)
    request = Message(code=POST, payload=payload.encode(), uri=subscription_address)
    response = await global_context.request(request).response
    return response


async def observation_call(address):
    global global_context
    global TOGGLE_NOTIF

    request = Message(code=GET, payload=b'', uri=address, observe=0)
    obs_over = asyncio.Future()

    try:
        remote_request = global_context.request(request)
        remote_request.observation.register_callback(notification_callback)
        response = await remote_request.response
        
        # the first response usually do not trigger the callback.
        # So we trigger it manually
        #notification_callback(response)
        
        #exit_reason = await obs_over
    finally:
        if not remote_request.response.done():
            remote_request.response.cancel()
        if not remote_request.observation.cancelled:
            remote_request.observation.cancel()
    
    if TOGGLE_NOTIF:
        raise KeyboardInterrupt
    else:
        TOGGLE_NOTIF = True


async def unsubscription_call(address):
    global global_context
    request = Message(code=GET, uri=address, observe=1)
    response = await global_context.request(request).response
    return response


def main(args, query):
    # first of all we subscribe
    result = global_loop.run_until_complete(subscription_call(args.address, query))
    subscription_resource_hash = result.payload.decode()

    observe_address = "coap://{}/{}".format(args.address, subscription_resource_hash)

    # then we observe
    try:
        global_loop.run_until_complete(observation_call(observe_address))
    except KeyboardInterrupt:
        # Once we stop the observation, we unobserve the resource
        # This is indeed a recursion call, since we already programmed
        # this case.
        result = global_loop.run_until_complete(unsubscription_call(observe_address))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tool to make queries to MUSEPA!")
    parser.add_argument("-a", "--address", required=True, help="Example: 127.0.0.1:5476 or 127.0.0.1 or 192.168.1.13...")
    parser.add_argument("-p", "--payload", required=True, help="""This parameter can be either a SPARQL query, 
either a path to a file (containing a SPARQL query)""")
    args = parser.parse_args()

    query = args.payload
    if isfile(args.payload):
        print("Detected file address...")
        with open(args.payload, "r") as payload_file:
            query = payload_file.read()
    else:
        print("Detected string payload (or non existing file)...")

    main(None, args, query)

    
