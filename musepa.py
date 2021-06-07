#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#

import sys
import logging
import argparse
import asyncio
import json
import time
import csv

from aiocoap import resource as coap
from aiocoap import Context, Message, NOT_FOUND, DELETED, BAD_REQUEST
from aiocoap import BAD_OPTION, CHANGED, CREATED, FORBIDDEN
from aiocoap.optiontypes import StringOption
from os.path import exists, dirname
from ipaddress import ip_address, IPv4Address
from endpoint import get_endpoint
from hashlib import md5
from prefix import Prefixes


SPARQL = "sparql"
CLIENTS = "clients"
RESOURCE = "resource"
DEFAULT = "default"

logger = logging.getLogger(__name__)
START_TIME = time.time()

rdf_endpoint = None
prefix_container = Prefixes(silent=True)

# This global variable will act as storage of information about the
# currently running subscriptions. The dictionary here will be formatted as
# "subscription_alias": {
#       "sparql": "SPARQL_QUERY_SUBSCRIPTION",
#       "clients": [informations],
#       "resource": SubscriptionResource instance
# }
subscription_store = {}


class musepaInfo(coap.Resource):
    """Global info resource about MUSEPA"""
    # This is the coap resource that will provide informations about
    # MUSEPA to the clients making GET request
    async def render_get(self, request):
        logger.info("Information request from {}".format(request.remote.hostinfo))
        with open("./README.md", "r") as readMe:
            info = readMe.read().encode()
        return Message(payload=info)


class SparqlQuery(coap.Resource):
    """Resource that can be contacted to query the contents of the RDF store"""
    # This is the coap resource that deals with queries.
    # To make a query here you setup a CoAP GET request with
    # sparql SELECT as payload.
    async def render_get(self, request):
        global rdf_endpoint
        logger.debug(f"Request from {request.remote.hostinfo}\nRequest payload: {request.payload}")
        if request.payload == b'':
            return Message(code=BAD_OPTION)
        else:
            prefixed_query = prefix_container.sparql + request.payload.decode()
            res, code = rdf_endpoint.query(prefixed_query)
            if code:
                return Message(payload=prefix_container.applyTo(res))
            else:
                return Message(code=BAD_REQUEST)


class SparqlUpdate(coap.Resource):
    """Resource that can be contacted to update the contents of the RDF store"""
    # https://stackoverflow.com/questions/107390/whats-the-difference-between-a-post-and-a-put-http-request
    # TODO render_delete to include possibility of deleting from
    # ttl or n3 format
    async def render_post(self, request):
        global rdf_endpoint
        global START_TIME
        global TNUM
        logger.debug(f"Request from {request.remote.hostinfo}\nRequest payload: {request.payload}")

        START_TIME = time.time()
        if request.payload == b'':
            return Message(code=BAD_OPTION)
        else:
            # Here the update logic, e.g., query rdflib or query fuseki or
            # Blazegraph. For return codes, have a look to
            # https://tools.ietf.org/html/rfc7252#section-5.9
            coap_request_options = list(request.opt.option_list())
            code = True

            # Here we need to check if there are more than one StringOption
            # among the coap_request_options (i.e.: the format parameter)
            stringOptionLen = sum(isinstance(i, StringOption) for i in coap_request_options)
            if stringOptionLen > 1:
                logger.warning("stringOptionLen > 1")
                # dealing with file upload, like .ttl
                # e.g. POST coap://HERE_THE_URI/sparql/update?format=ttl
                for option in coap_request_options:
                    parse_option = str(option).split("=")
                    if len(parse_option) > 1 and "format" == parse_option[0]:
                        logger.info(f"Requested option {parse_option[1]} file")
                        if hasattr(prefix_container, parse_option[1]):
                            prefixed_update = getattr(prefix_container, parse_option[1]) + request.payload.decode()
                        else:
                            logger.warning(f"Unable to find {parse_option[1]} format...")
                            prefixed_update = request.payload.decode()
                        res, code = rdf_endpoint.update(prefixed_update, format=parse_option[1])
                        logger.debug(f"Result: {res}; code: {code}")
                        break
            else:
                prefixed_update = prefix_container.sparql + request.payload.decode()
                res, code = rdf_endpoint.update(prefixed_update)
                logger.debug(f"Result: {res}; code: {code}")
            update_time = time.time() - START_TIME
            res, code = rdf_endpoint.query("select (count(*) as ?triples) where {?a ?b ?c}")
            TNUM = int(json.loads(res.decode())["results"]["bindings"][0]["triples"]["value"])
            print(TNUM)
            if ((TNUM>0) and (request.payload.decode() != "delete where {?a ?b ?c}")):
                UPDATEWRITER.writerow([len(subscription_store.keys()), TNUM, update_time])
            if code:
                START_TIME = time.time()
                for k in subscription_store.keys():
                    subscription_store[k][RESOURCE].rescheduleNow()    
                return Message(code=CHANGED)
            else:
                return Message(code=BAD_REQUEST)


class SparqlSubscription(coap.Resource):
    """Resource that should be contacted to
    - request new subscriptions
    - get some informations about running subscriptions
    - delete a subscription
    """
    async def render_post(self, request):
        global root
        global subscription_store
        logger.debug(f"Request from {request.remote.hostinfo}\nRequest payload: {request.payload}")
        if request.payload == b'':
            return Message(code=BAD_OPTION)
        else:
            hash_alias = md5(request.payload).hexdigest()
            if hash_alias not in subscription_store.keys():
                # Only if the subscription does not exist we create a new resource
                decoded_payload = request.payload.decode()
                new_res = SubscriptionResource(hash_alias, decoded_payload)
                subscription_store[hash_alias] = {
                    SPARQL: decoded_payload,
                    RESOURCE: new_res,
                    CLIENTS: []}
                root.add_resource((hash_alias,), new_res)
                logging.warning(root.get_resources_as_linkheader())
            return Message(payload=hash_alias.encode(), code=CREATED)

    async def render_get(self, request):
        """This method returns information about existing subscriptions.
        In case of empty payload it will return a NOT_FOUND
        In case of wrong payload it will return a BAD_REQUEST
        Otherwise, it sends a view of global dictionary subscription_store
        """
        global subscription_store
        logger.debug(f"Request from {request.remote.hostinfo}\nRequest payload: {request.payload}")
        decoded_payload = request.payload.decode()       

        if decoded_payload == '':
            return Message(code=NOT_FOUND)
        elif decoded_payload in subscription_store.keys():
            informations = {
                SPARQL: subscription_store[decoded_payload][SPARQL],
                CLIENTS: len(subscription_store[decoded_payload][CLIENTS])}
            logger.debug(f"Subscription {decoded_payload} information: {informations}")
            return Message(payload=json.dumps(informations).encode())
        else:
            return Message(code=BAD_REQUEST)

    async def render_delete(self, request):
        logger.warning("Deprecated DELETE subscription to /sparql/subscription")
        return Message(code=BAD_REQUEST, payload=b'Use GET request to subscription resource with observe flag =1')


class SubscriptionResource(coap.ObservableResource):
    """ObservableResource class that deals with notifications to subscribers"""
    def __init__(self, alias, content):
        super().__init__()
        self.alias = alias
        self.content = prefix_container.sparql + content
        self.lastRes, _ = rdf_endpoint.query(content)
        self.notify()

    def notify(self):
        global subscription_store
        global START_TIME
        new, code = rdf_endpoint.query(self.content)
        logger.info("{} notify method called!".format(self.alias))
        if new != self.lastRes:
            # only if old results differs from the new ones
            self.lastRes = new
            self.updated_state()
        full_notification_time = time.time() - START_TIME
        if len(json.loads(new.decode())["results"]["bindings"])>0:
            NOTIFWRITER.writerow([TNUM, len(subscription_store.keys()), full_notification_time])

    def rescheduleNow(self):
        # TODO verify if this method is necessary, or if we can directly call self.notify instead
        self.handle = asyncio.get_event_loop().call_soon_threadsafe(self.notify)

    async def render_get(self, request):
        global root
        client = request.remote.hostinfo
        logger.info("observing client: {}".format(client))
        if request.opt.observe == 1:
            if client in subscription_store[self.alias][CLIENTS]:
                # if the requesting client is observing this resource
                subscription_store[self.alias][CLIENTS].remove(client)
                logger.warning(f"{client} stopped observing {self.alias} resource")
                if len(subscription_store[self.alias][CLIENTS]) == 0:
                    # if it's the only client observing
                    root.remove_resource((self.alias,))
                    del subscription_store[self.alias]
                    return Message(code=DELETED)
                    #return Message(code=DELETED, payload=b'Resource deleted')
                else:
                    # if other clients are still observing
                    return Message(code=CHANGED)
                    #return Message(code=CHANGED, payload=b'Observation stopped')
            else:
                # if the client is not observing, then he cannot delete!
                return Message(code=FORBIDDEN)
        else:
            if client not in subscription_store[self.alias][CLIENTS]:
                subscription_store[self.alias][CLIENTS].append(client)
            logger.debug(subscription_store)
            return Message(payload=prefix_container.applyTo(self.lastRes))


def musepa(a4=DEFAULT, a6=DEFAULT, port=5683,  # custom ip:port address for musepa
           endpoint="blazegraph",  # endpoint type: choose between rdflib and Blazegraph
           event_loop=asyncio.new_event_loop(),  # event loop: only if you know what you are doing
           params=None):  # additional params to be used to parametrize the endpoint
    """Invokes musepa in a programmatic way (no CLI)

    Parameters
    ----------
    a4 : str, optional
        defaults to 'default' (i.e. 127.0.0.1), should be the ipv4 ip address
        where musepa is listening.

    a6 : str, optional
        defaults to 'default' (i.e. ::ffff:127.0.0.1), should be the ipv6 ip
        address where musepa is listening.

    port : int, optional
        default to CoAP default port 5683, it's the port on which musepa is
        listening

    endpoint = endpoint.RDFEndpoint, optional
        defaults to blazegraph instance, should be populated by the returned
        value of endpoint.get_endpoint function

    event_loop = asyncio.Loop, optional
        defaults to asyncio.new_event_loop()

    params = str, optional
        defaults to None, it is useful to give programmatically params to the
        endpoint instance that should be created
    """
    global subscription_store
    global prefix_container
    subscription_store = {}
    prefix_container = Prefixes()
    logFormat = "%(levelname)s   %(asctime)-15s %(filename)s[%(lineno)d] : %(message)s"
    logging.basicConfig(level=logging.INFO, format=logFormat, filename="./musepa_log.log")
    logging.warning(subscription_store)
    asyncio.set_event_loop(event_loop)
    main(a4, a6, port, endpoint=get_endpoint(endpoint, params), loop=event_loop)


def main(addressV4, addressV6, port, endpoint, loop=asyncio.get_event_loop()):
    # setup endpoint
    global rdf_endpoint
    rdf_endpoint = endpoint

    global root
    root = coap.Site()
    root.add_resource((".well-known", "core"), coap.WKCResource(root.get_resources_as_linkheader))
    root.add_resource(('info',), musepaInfo())
    root.add_resource((SPARQL, 'query',), SparqlQuery()) 
    root.add_resource((SPARQL, 'update',), SparqlUpdate())
    root.add_resource((SPARQL,'subscription',),SparqlSubscription())
    # TODO accept ttl file to make delete
    # print(root.get_resources_as_linkheader())

    musepaAddress = ""
    if addressV4 == DEFAULT:
        asyncio.Task(Context.create_server_context(root))
        print("This CoAP server is running on default params")
        musepaAddress = "coap://localhost"
    else:
        asyncio.Task(Context.create_server_context(root, bind=(addressV6, port)))
        print(f"This CoAP server is running on {addressV4}:{port}")
        musepaAddress = f"coap://{addressV4}:{port}"
    print(f"""\n/-------------------------------------------------------\\
| Information: \t{musepaAddress}/info
| Query: \t{musepaAddress}/sparql/query
| Update: \t{musepaAddress}/sparql/update
| Subscribe: \t{musepaAddress}/sparql/subscription
\\-------------------------------------------------------/""")

    logger.info("waiting for client action...")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt: shutting down!")
    logger.info("MUSEPA was stopped")


if __name__ == '__main__':
    # command line parsing
    parser = argparse.ArgumentParser(description="MUSEPA server")
    parser.add_argument(
        "--address", metavar=("MUSEPA_ADDRESS"), 
        default=DEFAULT, type=str, help="MUSEPA server ip address")
    parser.add_argument(
        "--port", metavar=("MUSEPA_PORT"), 
        default=5683, type=int, help="MUSEPA server port")
    parser.add_argument(
        "--endpoint", metavar=("ENDPOINT_NAME"),
        default="rdflib", choices=["blazegraph", "fuseki", "rdflib"],
        help="Choose the RDF endpoint to be used")
    parser.add_argument(
        "--endpoint_param", metavar=("ENDPOINT_PARAMETER"),
        default=None, help="Add here a parameter for the endpoint. In case of Fuseki, for instance, provide here the uri like http://127.0.0.1:3030/_dataset_")
    parser.add_argument(
        "--prefixes", metavar=("PATH_TO_PREFIX_FILE"),
        default=None, help="If needed, add here the path to a file containing prefixes in a ttl format")
    parser.add_argument(
        "-l", "--logLevel", metavar=("LOGGER_LEVEL"), 
        default=10, type=int,
        help="Logger level setup: 10 (info), 20, 30, ... 50 (critical)")
    parser.add_argument(
        "-d", "--logDestination", metavar=("LOGGER_DESTINATION"), 
        default=None, type=str,
        help="Destination of the logging messages (default is 'stdout')")
    parser.add_argument("-v", "--verbose", action="store_true", help="Include imported logs")
    args = parser.parse_args()
    logging.debug(args)

    print("""Welcome to

 __  __ _   _ ____  _____ ____   _    
|  \/  | | | / ___|| ____|  _ \ / \   
| |\/| | | | \___ \|  _| | |_) / _ \  
| |  | | |_| |___) | |___|  __/ ___ \ 
|_|  |_|\___/|____/|_____|_| /_/   \_\\
                                      

(former cMinor v2)      
""")

    # setup of logging
    logFormat = "%(levelname)s   %(asctime)-15s %(filename)s[%(lineno)d] : %(message)s"
    if args.logDestination and exists(dirname(args.logDestination)):
        logging.basicConfig(level=args.logLevel, format=logFormat, filename=args.logDestination)
    else:
        logging.basicConfig(level=args.logLevel, format=logFormat)

    if not args.verbose:
        asyncioLogger = logging.getLogger("asyncio").setLevel(logging.WARNING)
        coapLogger = logging.getLogger("coap-server").setLevel(logging.WARNING)
        coapLogger = logging.getLogger("coap-server.responder").setLevel(logging.WARNING)

    # checks for non-default ip and port
    addressV4 = DEFAULT
    addressV6 = DEFAULT
    if args.address != DEFAULT:
        try:
            address = ip_address(args.address)
        except ValueError:
            logger.error("Invalid ip address {}".format(args.address))
            sys.exit(1)

        if type(address) is IPv4Address:
            addressV4 = args.address
            addressV6 = "::ffff:{}".format(args.address)
        else:
            addressV4 = str(address.sixtofour)
            addressV6 = args.address

    if args.prefixes:
        prefix_container = Prefixes(args.prefixes)
    logger.info("MUSEPA configuration complete!")

    UPDATETIMEFILE = open("./test/update_times.csv", "a")
    NOTIFTIMEFILE = open("./test/notif_times.csv", "a")
    UPDATEWRITER = csv.writer(UPDATETIMEFILE)
    NOTIFWRITER = csv.writer(NOTIFTIMEFILE)
    NOTIFWRITER.writerow(["triples", "subscriptions", "time"])

    main(addressV4, addressV6, args.port,
         get_endpoint(args.endpoint, params=args.endpoint_param))

    UPDATETIMEFILE.close()
    NOTIFTIMEFILE.close()

    sys.exit(0)
