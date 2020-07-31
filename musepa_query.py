#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cCoap.py
#
#  Copyright 2020 Francesco Antoniazzi <francesco.antoniazzi@emse.fr>

import asyncio
import argparse

from aiocoap import Context, Message, GET


async def query_call(address, payload):
    context = await Context.create_client_context()

    query_address = "coap://{}/sparql/query".format(address)
    request = Message(code=GET, payload=payload.encode(), uri=query_address)
    response = await context.request(request).response
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tool to make queries to MUSEPA!")
    parser.add_argument("-a", "--address", required=True, help="Example: 127.0.0.1:5476 or 127.0.0.1 or 192.168.1.13...")
    parser.add_argument("-p", "--payload", required=True)
    args = parser.parse_args()

    result = asyncio.get_event_loop().run_until_complete(query_call(args.address, args.payload))

    print("Response code: %s\nServer answer : %s\nServer info : %r " % (result.code, result.payload.decode(), result.remote))
    