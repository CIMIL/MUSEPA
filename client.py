#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cminor_client.py
#  
#  Copyright (c) 2020 
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.


import logging
import asyncio
import argparse
import json

from aiocoap import *

from cCoap import coapCall
CMINOR_BASE_URL = "coap://127.0.0.1/{}"

def update(args):
    logging.info("Update process...")
    coapCall(CMINOR_BASE_URL.format("sparql/update"),verb="POST", payload=args.payload)

def query(args):    
    logging.info("Query process...")
    coapCall(CMINOR_BASE_URL.format("sparql/query"),verb="GET", payload=args.payload)

def info():    
    logging.info("Query process...")
    coapCall(CMINOR_BASE_URL.format("sparql/subscription"),verb="GET", payload="8d1c4")

class Subs_Obs():
    '''
    The subscribe will happen and right after it will launch the observation, 
    which will observe all the changes happen in this specific subsribe.
    '''
    def subscribe(self, args):
        logging.info("Subscribe process...")
        hashed = coapCall(CMINOR_BASE_URL.format("sparql/subscription"),verb="POST", payload=args.payload).payload.decode()
 
        
        self.observal(hashed)

    def observal(self, new):
        self.new = new

        def observation_cb(response):
            print(response.payload)

        async def obs():
                context = await Context.create_client_context()
                request = Message(code=GET, uri='coap://127.0.0.1/{}'.format(self.new), observe=0)  
                obs_over = asyncio.Future()

                try:
                    requester = context.request(request)
                    requester.observation.register_callback(observation_cb)
                    response = await requester.response

                    exit_reason = await obs_over
                    print(exit_reason)
                finally:
                    if not requester.response.done():
                        requester.response.cancel()
                    if not requester.observation.cancelled:
                        requester.observation.cancel()
        return asyncio.get_event_loop().run_until_complete(obs())

if __name__ == "__main__":
    import sys
    subscriber = Subs_Obs()
    
    parser = argparse.ArgumentParser(description="Tool to make coap calls!")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', "--update", help="To submit an update", action='store_true')
    group.add_argument('-q', "--query", help="To submit an query", action='store_true')
    group.add_argument('-s', "--subscribe", help="To submit an subscribe", action='store_true')
    group.add_argument('-o', "--observe", help="To submit an subscribe", action='store_true')
    group.add_argument('-i', "--info", help="To get information about an subscribe", action='store_true')



    parser.add_argument("-p", "--payload", default=b'')
    parser.add_argument("-l", "--log",      metavar=("LOG DESTINATION"), default=argparse.SUPPRESS, help="Add this parameter to redirect logging to a file")

    args = parser.parse_args()

    FORMAT = "%(asctime)-15s %(filename)s[%(funcName)s] %(levelname)s:%(message)s"
    if "log" in args:
        logging.basicConfig(filename=args["log"], format=FORMAT, level=logging.INFO)

    else:
        logging.basicConfig(format=FORMAT, level=logging.INFO)

    if  args.update:
        sys.exit(update(args))
    elif args.query:
        sys.exit(query(args))
    elif args.info:
        info()
    elif args.subscribe:
        subscriber.subscribe(args)
        subscriber.observal()
