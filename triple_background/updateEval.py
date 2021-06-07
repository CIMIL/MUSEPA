#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  senza_nome.py
#  
#  Copyright 2021 Francesco Antoniazzi <francesco.antoniazzi1991@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import asyncio
import multiprocessing as multiproc
from time import sleep

import musepa_subscribe_observe
from types import SimpleNamespace
from aiocoap import Context, Message, POST, GET

async def update_call(address, payload, ttl=False):
    context = await Context.create_client_context()

    update_address = "coap://{}/sparql/update".format(address)
    if ttl:
        update_address += "?format=ttl"
        
    request = Message(code=POST, payload=payload.encode(), uri=update_address)
    response = await context.request(request).response
    return response

async def query_call(address, payload):
    context = await Context.create_client_context()

    query_address = "coap://{}/sparql/query".format(address)
    request = Message(code=GET, payload=payload.encode(), uri=query_address)
    response = await context.request(request).response
    return response

def main(args):
    FILEPATH = args[1]
    MUSEPA = args[2]
    SUBSCRIBERS = int(args[3])

    d = {"address": MUSEPA}

    
    multiproc.set_start_method('forkserver')
    all_processes = [multiproc.Process(target=musepa_subscribe_observe.main,  args=(SimpleNamespace(**d), f"select * where {{?a{s} ?b{s} ?c{s}}}")) for s in range(SUBSCRIBERS)]
    [p.start() for p in all_processes]

    sleep(1)

    with open(FILEPATH, "r") as triples:
        result = asyncio.get_event_loop().run_until_complete(update_call(MUSEPA, triples.read(), ttl=True))

    print(asyncio.get_event_loop().run_until_complete(query_call(MUSEPA, "select (count(*) as ?triples) where {?a ?b ?c}")).payload)
        
    [p.join() for p in all_processes]
    
    result = asyncio.get_event_loop().run_until_complete(update_call(MUSEPA, "delete where {?a ?b ?c}"))
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
