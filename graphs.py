#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#


import csv
import argparse
import asyncio

from os.path import exists
from cCoap import coapCall
from datetime import datetime
from time import sleep

from aiocoap import Context, Message, GET, POST, PUT, DELETE

context = None
loop = asyncio.get_event_loop()

MUSEPA_BASE_URL = "coap://193.49.165.70/{}"

# def create_files():
#     for i in range(0, 60, 10):
#         real_index = 1 if i == 0 else i
#         with open("./graph_tests/sparql_update_{}.ttl".format(real_index), "w") as file:
#             file.write("insert data {\n")
#             for n in range(1,real_index+1):
#                 file.write("ns:subject{} ns:predicate{} ns:object{} .\n".format(n, n, n))
#             file.write("}")


async def call(payload, address):
    global context
    request = Message(code=POST, payload=payload.encode(), uri=address)
    response = await context.request(request).response
    return response


async def ctx():
    global context
    context = await Context.create_client_context()


def execute_tests_update(endpoint):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    open_mode = "a" if exists("./graph_tests/update.csv") else "w"
    for address in [(MUSEPA_BASE_URL.format("sparql/update?format=ttl"), "./graph_tests/ttl_update_{}.ttl"), (MUSEPA_BASE_URL.format("sparql/update"), "./graph_tests/sparql_update_{}.sparql")]:
        for i in range(0, 60, 10):
            # deleting everything
            t = datetime.now()
            r = loop.run_until_complete(call("delete where {?a ?b ?c}", "coap://localhost/sparql/update"))
            delta = datetime.now() - t
            #print("Delete all time: {} ms".format(delta.total_seconds()*1000))
            
            real_index = max(1, i)
            with open(address[1].format(real_index), "r") as u_file:
                payload = u_file.read()

                t = datetime.now()
                r = loop.run_until_complete(call(payload, address[0]))
                delta = datetime.now() - t
                if "ttl" in address[0]: 
                    print("TTL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))
                else:
                    print("SPARQL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))

    # for i in range(0, 60, 10):
    #     coapCall(
    #             MUSEPA_BASE_URL.format("sparql/update"), verb="POST",
    #             payload="delete where {?a ?b ?c}")

    #     real_index = 1 if i == 0 else i
    #     with open("./graph_tests/ttl_update_{}.ttl".format(real_index), "r") as u_file:
    #         payload = u_file.read()

    #         update_address = MUSEPA_BASE_URL.format("sparql/update?format=ttl")
    #         t = datetime.now()
    #         r = loop.run_until_complete(call(payload, update_address))
    #         delta = datetime.now() - t
    #         print("TTL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))

        # with open("./graph_tests/update.csv", open_mode, newline='') as csvfile:
        #     graphwriter = csv.writer(csvfile)
        #     execute_tests(args.endpoint)


def main(args):
    u_results = execute_tests_update(args.endpoint)

    # q_results = query()

    # s_results = subscriptions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MUSEPA graph data builder")
    parser.add_argument(
        "--endpoint", metavar=("ENDPOINT_NAME"),
        default="blazegraph", choices=["blazegraph", "fuseki", "rdflib"],
        help="Choose the RDF endpoint to be used")
    args = parser.parse_args()
    main(args)
