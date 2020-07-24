#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#

import pytest
import logging
import json
import asyncio

from aiocoap import CONTENT, CHANGED, CREATED, POST, DELETED
from aiocoap import BAD_OPTION, BAD_REQUEST, Context, Message, GET
from threading import Thread
from musepa import musepa
from cCoap import coapCall, coapUnobserve
from endpoint import AVAILABLE_ENDPOINTS
from time import sleep

MUSEPA_BASE_URL = "coap://127.0.0.1/{}"

logFormat = "%(levelname)s   %(asctime)-15s %(filename)s[%(lineno)d] : %(message)s"
logging.basicConfig(level=logging.INFO, format=logFormat)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True, params=AVAILABLE_ENDPOINTS)
def musepa_fixture(request):
    logger.info("Starting MUSEPA...")
    loop = asyncio.new_event_loop()
    thread = Thread(
        target=musepa, kwargs={"endpoint": request.param, "event_loop": loop})
    thread.daemon = True
    thread.start()

    sleep(1)
    yield thread
    logger.info("Teardown MUSEPA")
    loop.stop()
    sleep(1)


class Test4musepa:
    def test_info(self):
        logger.info("Test info request...")
        assert coapCall(MUSEPA_BASE_URL.format("info")).code == CONTENT

# -------------------  Test Query  --------------------------------------#
#
    def test_query_no_payload(self):
        assert coapCall(MUSEPA_BASE_URL.format("sparql/query")).code == BAD_OPTION

    def test_query_sparql(self):
        logger.info("Test good sparql request")
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/query"),
            payload="SELECT * WHERE {?a ?b ?c}").code == CONTENT
        logger.info("Test bad sparql request")
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/query"),
            payload="SELECT * WHERE ?a ?b ?c").code == BAD_REQUEST

# -------------------  Test Update  --------------------------------------#
#
    def test_update_no_payload(self):
        assert coapCall(MUSEPA_BASE_URL.format("sparql/update"), verb="POST").code == BAD_OPTION

    def test_update_sparql(self):
        # clearing the RDF store, and adding a triple
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/update"), verb="POST",
            payload="prefix : <http://test.org/> DELETE {?a ?b ?c} INSERT {:s :p :o} WHERE { OPTIONAL{?a ?b ?c} }").code == CHANGED

        logger.info("Checking if triples successfully added...")
        check = coapCall(
            MUSEPA_BASE_URL.format("sparql/query"),
            payload="SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }")
        assert int(json.loads(check.payload.decode())["results"]["bindings"][0]["triples"]["value"]) == 1

        # whenever sparql is wrong...
        logger.info("test bad sparql update...")
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/update"), verb="POST",
            payload="DELETE ?a ?b ?c WHERE ?a ?b ?c").code == BAD_REQUEST

    def test_update_file(self):
        # clearing the RDF store, and adding a triple
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/update"), verb="POST",
            payload="DELETE {?a ?b ?c} WHERE {?a ?b ?c}").code == CHANGED

        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/update?format=ttl"), 
            verb="POST",
            payload="@prefix : <http://test.org/>. :a :b :c.").code == CHANGED

        logger.info("Checking if triples successfully added...")
        check = coapCall(
            MUSEPA_BASE_URL.format("sparql/query"),
            payload="SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }")
        assert int(json.loads(check.payload.decode())["results"]["bindings"][0]["triples"]["value"]) == 1

# -------------------  Subscription  POST & Observe  -------------------------#
#
    def test_subscribe(self):
        # Here we clear the RDF store for this test
        assert coapCall(
            MUSEPA_BASE_URL.format("sparql/update"),
            verb="POST",
            payload="DELETE WHERE {?a ?b ?c}", loop=asyncio.get_event_loop()).code == CHANGED

        # Here we create the subscription
        logger.info("Test good POST sparql Subscription")
        response = coapCall(
            MUSEPA_BASE_URL.format("sparql/subscription"), verb="POST",
            payload="SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        logger.warning(response.payload.decode())
        assert response.code == CREATED

        async def observation():
            # This is the observation task, that contains...
            coap_context = None

            end_of_test = asyncio.Event()
            end_of_observation_setup = asyncio.Event()

            def callback(result):
                # ... The observation callback...
                nonlocal end_of_test
                logging.warning("Callback called! {}".format(result))
                end_of_test.set()

            async def call(address):
                # ... The actual observe call...
                nonlocal coap_context
                nonlocal end_of_observation_setup
                logger.debug("Address {}".format(address))
                coap_context = await Context.create_client_context()
                request = Message(code=GET,
                                  payload=b'', uri=address, observe=0)
                obs_over = asyncio.Future()

                try:
                    remote_request = coap_context.request(request)
                    remote_request.observation.register_callback(callback)
                    resp = await remote_request.response
                    logging.warning("Observe response: {}\nObserve code: {}".format(resp.payload.decode(), resp.code))
                    assert resp.code == CONTENT
                    # We don't trigger the first notification in this test
                    # we just check that something arrived. Once it is the case
                    # we can proceed in triggering the test update to see if
                    # the callback is working.
                    end_of_observation_setup.set()

                    exit_reason = await obs_over
                    logging.debug(exit_reason)
                finally:
                    if not remote_request.response.done():
                        remote_request.response.cancel()
                    if not remote_request.observation.cancelled:
                        remote_request.observation.cancel()

            # The observation instanciates the call...
            observation_task = asyncio.create_task(call(MUSEPA_BASE_URL.format(response.payload.decode())))
            # ... waits for the call to finish
            logger.info("Waiting for end_of_observation_setup")
            await end_of_observation_setup.wait()

            # ...Tests the callback after an update
            update = Message(
                code=POST,
                payload="INSERT DATA {<http://a> <http://b> <http://c>}".encode(),
                uri=MUSEPA_BASE_URL.format("sparql/update"))
            ctx = await Context.create_client_context()
            update_response = await ctx.request(update).response
            logging.debug(update_response)
            assert update_response.code == CHANGED

            # ...Waits the callback after the update
            await end_of_test.wait()
            observation_task.cancel()
            # ...Returns the context, since the unsubscription must come from
            # the same context
            return coap_context

        # Here we run the observation job
        ctx = asyncio.get_event_loop().run_until_complete(observation())

        # Check unsubscription as well once the job is finished
        assert coapUnobserve(MUSEPA_BASE_URL.format(response.payload.decode()),
                             context=ctx).code == DELETED

    def test_Subscription_no_payload(self):
        logger.info("Test sparql POST Subscription No payload")
        assert coapCall(MUSEPA_BASE_URL.format("sparql/subscription"), verb="POST").code == BAD_OPTION