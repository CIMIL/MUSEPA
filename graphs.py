#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#


import argparse
import asyncio

from os.path import exists
from datetime import datetime

from aiocoap import Context, Message, POST, GET

from matplotlib import pyplot as plt
from numpy import arange, array, mean, append, empty, asarray, var

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


async def call(payload, address, verb=POST):
    global context
    request = Message(code=verb, payload=payload.encode(), uri=address)
    response = await context.request(request).response
    return response


async def ctx():
    global context
    context = await Context.create_client_context()


def execute_tests_update(endpoint, title):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    ttl_time_matrix = []
    sparql_time_matrix = []
    for repetition in range(0,20):
        #open_mode = "a" if exists("./graph_tests/update.csv") else "w"
        ttl_experiment = []
        sparql_experiment = []
        for address in [(MUSEPA_BASE_URL.format("sparql/update?format=ttl"), "./graph_tests/ttl_update_{}.ttl"),
                        (MUSEPA_BASE_URL.format("sparql/update"), "./graph_tests/sparql_update_{}.sparql")]:

            for i in range(0, 60, 10):
                # deleting everything
                t = datetime.now()
                r = loop.run_until_complete(call("delete where {?a ?b ?c}", "coap://193.49.165.70/sparql/update"))
                delta = datetime.now() - t

                real_index = max(1, i)
                with open(address[1].format(real_index), "r") as u_file:
                    payload = u_file.read()

                    t = datetime.now()
                    r = loop.run_until_complete(call(payload, address[0]))
                    delta = datetime.now() - t
                    if repetition:
                        if "ttl" in address[0]: 
                            ttl_experiment.append(delta.total_seconds()*1000)
                            print("TTL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))
                        else:
                            sparql_experiment.append(delta.total_seconds()*1000)
                            print("SPARQL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))
        if repetition:
            ttl_time_matrix.append(ttl_experiment)
            sparql_time_matrix.append(sparql_experiment)

    ttl_time_matrix = mean(asarray(ttl_time_matrix), axis=0)
    sparql_time_matrix = mean(asarray(sparql_time_matrix), axis=0)

    fig, ax = plt.subplots()
    width = 2
    _range = arange(0,60,10)
    _range[0] = 1
    sparql_bar = ax.bar(_range-width/2-0.1, sparql_time_matrix, width=width, label="sparql")
    ttl_bar = ax.bar(_range+width/2+0.1, ttl_time_matrix, width=width, label="ttl")
    
    ax.set_title("{} endpoint update time evaluation".format(args.title))
    ax.set_ylabel('Update time in ms')
    ax.set_xlabel('Number of triples in the update')
    ax.set_xticks(_range)
    ax.legend()

    for i, v in enumerate(ttl_time_matrix):
        plt.text(_range[i]+width/2+0.1, v + 0.01, round(v))
    for i, v in enumerate(sparql_time_matrix):
        plt.text(_range[i]-width/2-0.1, v + 0.01, round(v))

    plt.show()


def execute_tests_query(endpoint, title):
    #loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    ttl_time_matrix = []
    sparql_time_matrix = []
    _range = [0 for i in range(0,60,10)]
    for repetition in range(0,20):
        #open_mode = "a" if exists("./graph_tests/update.csv") else "w"
        ttl_experiment = []
        sparql_experiment = []

        for i in range(0, 60, 10):
            # deleting everything
            r = loop.run_until_complete(call("delete where {?a ?b ?c}", "coap://193.49.165.70/sparql/update"))
            real_index = max(1, i)
            with open("./graph_tests/sparql_update_{}.sparql".format(real_index), "r") as u_file:
                payload = u_file.read()
            r = loop.run_until_complete(call(payload, "coap://193.49.165.70/sparql/update"))

            t = datetime.now()
            r = loop.run_until_complete(call("select * where {?a ?b ?c}", "coap://193.49.165.70/sparql/query", verb=GET))
            delta = datetime.now() - t
            if repetition:
                _range[int(i/10)] = len(r.payload)
                sparql_experiment.append(delta.total_seconds()*1000)
                print("SPARQL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))
        if repetition:
            sparql_time_matrix.append(sparql_experiment)

    sparql_time_matrix = mean(asarray(sparql_time_matrix), axis=0)
    _range = asarray(_range)
    return _range, sparql_time_matrix


class Subscriber(Thread):
    def __init__(self, payload):
        super().__init__()
        self.daemon = True
        self.address = "coap://193.49.165.70/"+payload.decode()
        self.start_time = None
        self.delta = None
        self.start()
        self.event = Event()

    def getDelta(self):
        return self.delta

    def update(self):
        loop.run_until_complete(call("insert where {?a ?b ?c}", "coap://193.49.165.70/sparql/update"))
        

    def run(self):
        loop = asyncio.new_event_loop()
        async def call():
            context = await Context.create_client_context()
            request = Message(code=GET, payload=b'select * where {?a ?b ?c}', uri=self.address, observe=0)
            obs_over = asyncio.Future()
            remote_request = None
            
            def callback(data):
                print("Callback!")
            
            try:
                remote_request = context.request(request)
                remote_request.observation.register_callback(callback)
                response = await remote_request.response

                callback(response)
                
                exit_reason = await obs_over
                logging.warning(exit_reason)
            finally:
                if not remote_request.response.done():
                    remote_request.response.cancel()
                if not remote_request.observation.cancelled:
                    remote_request.observation.cancel()
            self.event.wait()
            return
        return loop.run_until_complete(call())

    def stop(self):
        self.event.set()



def execute_tests_subscription():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    r = loop.run_until_complete(call("delete where {?a ?b ?c}", "coap://193.49.165.70/sparql/update"))
    r = loop.run_until_complete(call("select * where {?a ?b ?c}", "coap://193.49.165.70/sparql/subscription"))
    print(r.payload)
    for n_subscribers in range(1,101):
        tasks = [Subscriber(r.payload) for i in range(n_subscribers)]
        sleep(2)
        tasks[0].update()
        sleep(2)
        for i in tasks:
            i.stop()


def main(args):
    #u_results = execute_tests_update(args.endpoint, args.title)

    # _r, rdflib = execute_tests_query("rdflib", "RDFlib")
    # input("insert a number to proceed")
    # _, blazegraph = execute_tests_query("blazegraph", "Blazegraph")
    # input("insert a number to proceed")
    # _, fuseki = execute_tests_query("fuseki", "Fuseki")
    
    # w = 300
    # fig, ax = plt.subplots()
    # plt.bar(_r-w-100, rdflib, label="rdflib", width=w)
    # plt.bar(_r, blazegraph, label="blazegraph", width=w)
    # plt.bar(_r+w+100, fuseki, label="fuseki", width=w)

    # ax.set_title("Query time evaluation")
    # ax.set_ylabel('Query time in ms')
    # ax.set_xlabel('Length of "SELECT * WHERE {?a ?b ?c}" query response in bytes')
    # ax.set_xticks(_r)
    # ax.legend()

    # for i, v in enumerate(rdflib):
    #     plt.text(_r[i]-w-100, v + 0.01, round(v))
    # for i, v in enumerate(blazegraph):
    #     plt.text(_r[i], v + 0.01, round(v))
    # for i, v in enumerate(fuseki):
    #     plt.text(_r[i]+w+100, v + 0.01, round(v))

    # plt.show()

    execute_tests_subscription()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MUSEPA graph data builder")
    parser.add_argument(
        "--endpoint", metavar=("ENDPOINT_NAME"),
        default="blazegraph", choices=["blazegraph", "fuseki", "rdflib"],
        help="Choose the RDF endpoint to be used")
    parser.add_argument(
        "--title", metavar=("GRAPH_TITLE"),
        required=True, help="Choose the RDF endpoint to be used")
    args = parser.parse_args()
    main(args)
