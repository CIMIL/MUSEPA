#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musAPI.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#

import musAPI

# IMPORTANT WARNING
# These APIs are an extremely simplified version of what can be done only by
# observing the 'client_examples' folder. From here, you may encounter problems if
# you want to perform very complex interactions, because here some inner mechanisms
# of asyncio and aiocoap are hidden to the user.
# If you foresee the need to achieve complex multithreaded environment or complex
# behaviors for your code, please consider starting a client from scratch examining
# the code provided in the example clients. 
# It will also be ways more performant than using these wrapper of APIs.



def my_personal_callback(content):
    print("The callback has been called with content {}".format(content))
    print("Callback payload {}".format(content.payload))


if __name__ == "__main__":

    # in some cases it may be useful to pass a context to these functions: i.e.,
    # 
    # context = await Context.create_client_context()
    # 
    # from the asyncio and aiocoap libraries.

    result = musAPI.musepa_update("coap://localhost/sparql/update",
                                  "insert data {<http://ciao> <http://sono> <http://francesco>}")
    print("Update result: {}".format(result))
    print("Update result payload: {}".format(result.payload))
    print("Update result status code: {}".format(result.code))

    result = musAPI.musepa_query("coap://localhost/sparql/query",
                                 "select * where {?a ?b ?c}")
    print("\nQuery result: {}".format(result))
    print("Query result payload: {}".format(result.payload))
    print("Query result status code: {}".format(result.code))

    result = musAPI.musepa_subscribe("coap://localhost/sparql/subscription",
                                     "select * where {?a ?b ?c}")
    print("\nSubscription result: {}".format(result))
    print("Subscription result payload: {}".format(result.payload))
    print("Subscription result status code: {}".format(result.code))

    result = musAPI.musepa_observe("coap://localhost/{}".format(result.payload.decode()),
                          my_personal_callback)

    # HERE IT BLOCKS UNTIL THE END OF OBSERVATION that is a ctrl-c
    # and then unsubscribes automatically
    # It is not possible to change this behaviour with these APIs, since
    # there could be plenty of exit-methods that the user could be
    # interested in. So, if it's not the behaviour that you want, please
    # dive into cCoap.py and client_examples folders.a

    print("\nStopped observation!")