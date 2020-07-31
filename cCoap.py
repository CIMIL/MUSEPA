#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cCoap.py
#
#  Copyright 2020 Francesco Antoniazzi <francesco.antoniazzi@emse.fr>
#
#  Makes coap calls, just to debug

import sys
import argparse
import asyncio
import logging

from aiocoap import Context, Message, GET, POST, PUT, DELETE

callback_count = 0

# this is necessary to deal with unobserve after ctrl-c
global_context = None
global_loop = None

# In general, when we call the functions in this script, the 
# output will be logged at info level.
result_printer = logging.info


def parse_verb(verb):
    if verb == "GET":
        return GET
    elif verb == "POST":
        return POST
    elif verb == "PUT":
        return PUT
    else:
        return DELETE


def default_observation_callback(response):
    # Default callback for subscription notification
    global callback_count
    print("/---------Start Callback #{}------------------------------------------\\".format(callback_count))
    print("Response: {}\nDecoded payload: {}".format(response, response.payload.decode()))
    print("/---------End Callback #{}------------------------------------------".format(callback_count))
    callback_count += 1


def coapCall(address, verb="GET", payload=b'', loop=None, context=None):
    """Makes a CoAP call.

    Parameters
    ----------
    address : str
        Something like coap://127.0.0.1/

    verb : str, optional
        default to GET, must be one of GET, POST, PUT, DELETE

    payload : byte[], optional
        default to b'', the payload of the CoAP call

    loop : asyncio.loop
        depends on your application, in general default is fine

    context : aiocoap.Context
        to be provided if you want to keep memory of the client identity
        i.e., to be able to unsubscribe

    Returns
    -------
    CoAP call Response
    """
    # This function is to be called by external scripts to perform a basic CoAP call.
    global global_context
    global global_loop

    # initializing application loop and context for programmatic calls of the script
    global_loop = asyncio.get_event_loop() if loop is None else loop
    if context:
        global_context = context
    return main(argparse.Namespace(
        address=address, verb=verb, payload=payload,
        observe=False, unobserve=False))


def coapObserve(address, payload=b'', callback=default_observation_callback,
                loop=None, context=None):
    """Makes a CoAP observe call.

    Parameters
    ----------
    address : str
        Something like coap://127.0.0.1/

    payload : byte[], optional
        default to b'', the payload of the CoAP call

    callback : function(param)
        the callback to be triggered in case of notification

    loop : asyncio.loop
        depends on your application, in general default is fine

    context : aiocoap.Context
        to be provided if you want to keep memory of the client identity
        i.e., to be able to unsubscribe

    Returns
    -------
    CoAP call Response
    """
    # This function is to be called by external scripts to perform a CoAP observe call.
    global global_context
    global global_loop

    # initializing application loop and context for programmatic calls of the script
    global_loop = asyncio.get_event_loop() if loop is None else loop
    if context:
        global_context = context
    return main(argparse.Namespace(
        address=address, payload=payload, observe=True, callback=callback))


def coapUnobserve(address, loop=None, context=None):
    """Makes a CoAP un-observe call.

    Parameters
    ----------
    address : str
        Something like coap://127.0.0.1/

    loop : asyncio.loop
        depends on your application, in general default is fine

    context : aiocoap.Context
        to be provided if you want to keep memory of the client identity
        i.e., to be able to unsubscribe

    Returns
    -------
    CoAP call Response
    """
    # This stops observing. Be careful that the context has to be the same as the one
    # of the observe call, otherwise the unobserve won't be successful.
    global global_context
    global global_loop

    # initializing application loop and context for programmatic calls of the script
    global_loop = asyncio.get_event_loop() if loop is None else loop
    if context:
        global_context = context
    return main(argparse.Namespace(
        address=address, verb=GET, payload=b'', observe=False, unobserve=True))


def main(args):
    global global_loop
    global global_context
    # notice that loop and context have already been initialized!
    logging.info(args)

    # transforming the payload coming from CLI or function call in byte array
    payload = args.payload if args.payload == b'' else args.payload.encode()

    if not args.observe:
        # CoAP resource regular method call (i.e. non observe request)
        verb = parse_verb(args.verb)

        async def call():
            global global_context
            if not global_context:
                # creates a context if none is given
                global_context = await Context.create_client_context()
            request = None
            if args.unobserve:
                # in particular, this is the case of a stop-observing request
                request = Message(code=GET, uri=args.address, observe=1)
            else:
                # all other cases: CoAP GET, POST, PUT... with or without payload
                request = Message(code=verb, payload=payload, uri=args.address)
            response = await global_context.request(request).response
            result_printer("Response code: %s\nServer answer : %s\nServer info : %r " % (response.code, response.payload.decode(), request.remote))
            return response
        return global_loop.run_until_complete(call())
    else:
        # Observation case
        logging.info("Resource observer...")

        # CoAP resource observer
        async def call():
            global global_context
            if not global_context:
                # creates a context if none is given
                global_context = await Context.create_client_context()
            # issuing the request
            request = Message(code=GET, payload=payload, uri=args.address, observe=0)
            obs_over = asyncio.Future()

            try:
                # If no callback function is provided, we use the default one
                cb = default_observation_callback if "callback" not in args else args.callback
                remote_request = global_context.request(request)
                remote_request.observation.register_callback(cb)
                response = await remote_request.response
                
                # the first response usually do not trigger the callback.
                # So we trigger it manually
                cb(response)
                
                exit_reason = await obs_over
                logging.warning(exit_reason)
            finally:
                if not remote_request.response.done():
                    remote_request.response.cancel()
                if not remote_request.observation.cancelled:
                    remote_request.observation.cancel()
        try:
            return global_loop.run_until_complete(call())
        except KeyboardInterrupt:
            # Once we stop the observation, we unobserve the resource
            # This is indeed a recursion call, since we already programmed
            # this case.
            coapUnobserve(args.address, loop=global_loop, context=global_context)
            logging.info("\nGot Ctrl-C: bye bye")
            return 1


if __name__ == '__main__':
    # CLI parameters, use -h or --help to get some friendly information
    parser = argparse.ArgumentParser(description="Tool to make coap calls!")
    parser.add_argument("-a", "--address", required=True)
    parser.add_argument(
        "--verb", default="GET", choices=["GET", "POST", "PUT", "DELETE"],
        help="Ignored when -o or --observe are used")
    parser.add_argument("-p", "--payload", default=b'')
    parser.add_argument(
        "-o", "--observe", action="store_true",
        help="Observes the given resource")
    parser.add_argument(
        "-u", "--unobserve", action="store_true",
        help="Stop observation of the resource")

    args = parser.parse_args()
    # initializing application loop for CLI calls of the script
    global_loop = asyncio.get_event_loop()

    # if we are here, then this is a CLI. So, the output should be
    # a standard output print.
    result_printer = print

    sys.exit(main(args))
