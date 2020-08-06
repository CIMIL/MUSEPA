#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#

import sys
import numpy as np
import asyncio
import csv

from datetime import datetime
from matplotlib import pyplot as plot
from aiocoap import Context, Message, POST, GET
from scipy import stats

NUMBER_OF_REPETITIONS = 20
QUERY = b'select * where {?a ?b ?c}'
ADDRESS = "coap://localhost/sparql/query"


async def ctx():
    global context
    context = await Context.create_client_context()


async def call(payload, address, verb=POST):
    global context
    request = Message(code=verb, payload=payload, uri=address)
    response = await context.request(request).response
    return response


def main(title):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    sparql_time_matrix = []
    sparql_time_matrix_no_extreme = []
    for repetition in range(NUMBER_OF_REPETITIONS):
        sparql_experiment = []
        for i in range(0, 60, 10):
            # deleting everything
            r = loop.run_until_complete(call(b"delete where {?a ?b ?c}", "coap://localhost/sparql/update"))

            real_index = max(1, i)
            with open("./graph_tests/sparql_update_{}.sparql".format(real_index), "r") as u_file:
                payload = u_file.read()
            r = loop.run_until_complete(call(payload.encode(), "coap://localhost/sparql/update"))

            t = datetime.now()
            r = loop.run_until_complete(call(QUERY, ADDRESS, verb=GET))
            delta = datetime.now() - t
            if repetition:
                sparql_experiment.append(delta.total_seconds()*1000)
                print("SPARQL {}: #execution time: {} ms ({})".format(real_index, delta.total_seconds()*1000, r.code))
        if repetition:
            sparql_time_matrix.append(sparql_experiment)
            c = sparql_experiment.copy()
            sparql_time_matrix_no_extreme.append(c)
    
    sparql_time_matrix = np.asarray(sparql_time_matrix)
    mean_result = np.mean(sparql_time_matrix, axis=0)
    median_result = np.median(sparql_time_matrix, axis=0)
    var_result = np.var(sparql_time_matrix, axis=0)
    std_result = np.std(sparql_time_matrix, axis=0)
    mad_result = stats.median_abs_deviation(sparql_time_matrix)
    print("Mean: {}\nMedian: {}\nVariance: {}\nStD: {}\nMAD: {}\n".format(mean_result,median_result,var_result,std_result,mad_result))

    sparql_time_matrix_no_extreme = np.asarray(sparql_time_matrix_no_extreme)
    _t = np.transpose(sparql_time_matrix_no_extreme)

    nmean_result = []
    nvar_result = []
    nstd_result = []
    nmad_result = []
    for i in range(6):
        row = _t[i,:]
        row = np.delete(row, row.argmin())
        row = np.delete(row, row.argmax())
        nmean_result.append(np.mean(row))
        nvar_result.append(np.var(row))
        nstd_result.append(np.std(row))
        nmad_result.append(stats.median_abs_deviation(row))
    print("nMean: {}\nnVariance: {}\nnStD: {}\nnMAD: {}\n".format(nmean_result,nvar_result,nstd_result,nmad_result))

    with open("query_table_{}.csv".format(title), "w") as tableresult:
        csv_writer = csv.writer(tableresult, delimiter=',')
        csv_writer.writerow(["Indicatore"] + [1, 10, 20, 30, 40, 50])
        csv_writer.writerow(["nMean"] + nmean_result)
        csv_writer.writerow(["nVariance"] + nvar_result)
        csv_writer.writerow(["nStd"] + nstd_result)
        csv_writer.writerow(["nMAD"] + nmad_result)
        csv_writer.writerow(["Mean"] + mean_result.tolist())
        csv_writer.writerow(["Median"] + median_result.tolist())
        csv_writer.writerow(["Variance"] + var_result.tolist())
        csv_writer.writerow(["Std"] + std_result.tolist())
        csv_writer.writerow(["MAD"] + mad_result.tolist())

    return nmean_result, nvar_result


if __name__ == "__main__":
    rdfLib_mean, rdfLib_var = main("RDFLib")
    
    input("Please start Blazegraph and insert a number: ")
    blazegraph_mean, blazegraph_var = main("Blazegraph")
    
    input("Please start Fuseki and insert a number: ")
    fuseki_mean, fuseki_var = main("Fuseki")

    x_axis = list(range(0, 60, 10))
    x_axis[0] = 1

    # The query that is tested is 'select * where {?a ?b ?c}'
    # so the number of bindings is 3 times the number of triples
    x_axis = 3*np.asarray(x_axis)

    width = 8
    fig, ax = plot.subplots()
    plot.bar(x_axis-width,   rdfLib_mean,     label="rdflib",     width=width-2)
    #plot.errorbar(x_axis-width, rdfLib_mean, yerr=rdfLib_var, fmt=".k")

    plot.bar(x_axis,             blazegraph_mean, label="blazegraph", width=width-2)
    #plot.errorbar(x_axis, blazegraph_mean, yerr=blazegraph_var, fmt=".k")

    plot.bar(x_axis+width,   fuseki_mean,     label="fuseki",     width=width-2)
    #plot.errorbar(x_axis+width, fuseki_mean, yerr=fuseki_var, fmt=".k")

    ax.set_title("Query time evaluation")
    ax.set_ylabel('Query time in ms')
    ax.set_xlabel('Number of bindings of the response')
    ax.set_xticks(x_axis)
    ax.legend()

    # for i, v in enumerate(rdflib):
    #     plt.text(_r[i]-w-100, v + 0.01, round(v))
    # for i, v in enumerate(blazegraph):
    #     plt.text(_r[i], v + 0.01, round(v))
    # for i, v in enumerate(fuseki):
    #     plt.text(_r[i]+w+100, v + 0.01, round(v))

    plot.show()

    sys.exit(0)
