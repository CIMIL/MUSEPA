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
from aiocoap import Context, Message, POST
from scipy import stats
from os import listdir

NUMBER_OF_REPETITIONS = 20
ADDRESS = "coap://localhost/sparql/update"
ADDRESS_FORMAT = "coap://localhost/sparql/update?format=ttl"


async def ctx():
    global context
    context = await Context.create_client_context()


async def call(payload, address):
    global context
    request = Message(code=POST, payload=payload, uri=address)
    response = await context.request(request).response
    return response


def test_exec(file_list, loop, ttl, endpoint):
    title = "TTL" if ttl else "SPARQL"
    address = ADDRESS_FORMAT if ttl else ADDRESS
    time_matrix = []
    for repetition in range(NUMBER_OF_REPETITIONS):
        experiment = []
        for _file in file_list:
            # deleting everything
            r = loop.run_until_complete(call(b"delete where {?a ?b ?c}", ADDRESS))

            with open("./graph_tests/{}".format(_file), "r") as u_file:
                payload = u_file.read().encode()

                t = datetime.now()
                r = loop.run_until_complete(call(payload, address))
                delta = datetime.now() - t
                if repetition:
                    experiment.append(delta.total_seconds()*1000)
                    print("{} {}: #execution time: {} ms ({})".format(
                        title,
                        _file,
                        delta.total_seconds()*1000,
                        r.code))
        if repetition:
            time_matrix.append(experiment)
    
    time_matrix_no_extreme = np.asarray(time_matrix.copy())
    time_matrix = np.asarray(time_matrix)

    mean_result = np.mean(time_matrix, axis=0)
    median_result = np.median(time_matrix, axis=0)
    var_result = np.var(time_matrix, axis=0)
    std_result = np.std(time_matrix, axis=0)
    mad_result = stats.median_abs_deviation(time_matrix)
    print("{}:\nMean: {}\nMedian: {}\nVariance: {}\nStD: {}\nMAD: {}\n".format(
        title,
        mean_result,
        median_result,
        var_result,
        std_result,
        mad_result))

    _t = np.transpose(time_matrix_no_extreme)

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
    print("{}:\nnMean: {}\nnVariance: {}\nnStD: {}\nnMAD: {}\n".format(
        title,
        nmean_result,
        nvar_result,
        nstd_result,
        nmad_result))

    with open("update_table_{}_{}.csv".format(title, endpoint), "w") as tableresult:
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

    return nmean_result

def main(endpoint):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ctx())

    updates_ttl = []
    updates_sparql = []
    for u_file in listdir("./graph_tests"):
        if "ttl_u" in u_file:
            updates_ttl.append(u_file)
        elif "sparql_u" in u_file:
            updates_sparql.append(u_file)
    
    updates_ttl.sort()
    updates_sparql.sort()

    s_mean = test_exec(updates_sparql, loop, False, endpoint)
    ttl_mean = test_exec(updates_ttl, loop, True, endpoint)

    return s_mean, ttl_mean


if __name__ == "__main__":
    rdfLib_mean_s, rdfLib_mean_t = main("RDFLib")
    
    input("Please start Blazegraph and insert a number: ")
    blazegraph_mean_s, blazegraph_mean_t = main("Blazegraph")
    
    input("Please start Fuseki and insert a number: ")
    fuseki_mean_s, fuseki_mean_t = main("Fuseki")

    x_axis = list(range(0, 60, 10))
    x_axis[0] = 1
    x_axis = np.asarray(x_axis)

    width = 2
    fig, (ax1, ax2) = plot.subplots(ncols=2)
    fig.add_subplot(111, frameon=False)
    plot.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)

    ax1.bar(x_axis-width-1,   rdfLib_mean_s,     label="RDFlib sparql",  width=width, color="blue")
    ax2.bar(x_axis-width-1,   rdfLib_mean_t,     label="RDFlib ttl",     width=width, color="red")
    #plot.errorbar(x_axis-width, rdfLib_mean, yerr=rdfLib_var, fmt=".k")

    ax1.bar(x_axis, blazegraph_mean_s, label="Blazegraph sparql", width=width, color="green")
    ax2.bar(x_axis, blazegraph_mean_t, label="Blazegraph ttl",    width=width, color="purple")
    # #plot.errorbar(x_axis, blazegraph_mean, yerr=blazegraph_var, fmt=".k")

    ax1.bar(x_axis+width+1,   fuseki_mean_s,     label="Fuseki sparql",  width=width, color="orange")
    ax2.bar(x_axis+width+1,   fuseki_mean_t,     label="Fuseki ttl",     width=width, color="cyan")
    # #plot.errorbar(x_axis+width, fuseki_mean, yerr=fuseki_var, fmt=".k")

    plot.title("Update time evaluation")
    plot.xlabel('Number of triples')
    ax1.set_ylabel('Update mean time in ms')
    ax1.set_xticks(x_axis)
    ax2.set_xticks(x_axis)
    ax1.legend()
    ax2.legend()

    # # for i, v in enumerate(rdflib):
    # #     plt.text(_r[i]-w-100, v + 0.01, round(v))
    # # for i, v in enumerate(blazegraph):
    # #     plt.text(_r[i], v + 0.01, round(v))
    # # for i, v in enumerate(fuseki):
    # #     plt.text(_r[i]+w+100, v + 0.01, round(v))

    plot.show()

    sys.exit(0)
