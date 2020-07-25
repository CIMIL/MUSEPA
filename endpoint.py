#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  endpoint.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#

import requests
import logging

from abc import ABC, abstractmethod
from rdflib import Graph

logger = logging.getLogger("endpoint")
logFormat = "%(levelname)s   %(asctime)-15s %(filename)s[%(lineno)d] : %(message)s"
logging.basicConfig(level=logging.INFO, format=logFormat)

AVAILABLE_ENDPOINTS = ["rdflib", "blazegraph", "fuseki"]


def get_endpoint(id, params=None):
    """Invokes the correct RDF store endpoint constructor.

    Parameters
    ----------
    id : str
        endpoint tag: must be one of the elements in AVAILABLE_ENDPOINTS
        variable

    params : depends on the endpoint, optional
        default to None, for 'blazegraph' is a string that contains its uri

    Raises
    ------
    ConnectionError
        if the endpoint is not reachable

    NotImplementedError
        if the 'id' is not contained in AVAILABLE_ENDPOINTS
    
    ValueError
        if params value is None when Fuseki is called

    Returns
    -------
    RDFEndpoint
        an RDFEndpoint instance
    """

    if id.lower() == "blazegraph":
        # raising exception if blazegraph is requested, but no running
        # instance is available
        blazegraph_ip = params if params else "http://localhost:9999/bigdata/sparql"
        if requests.get(blazegraph_ip).status_code != requests.codes.ok:
            logger.critical("Blazegraph is not reachable at {}".format(blazegraph_ip))
            raise ConnectionError("Blazegraph is not reachable at {}".format(blazegraph_ip))
        return Blazegraph(blazegraph_ip)
    elif id.lower() == "fuseki":
        if params is None:
            # params will contain something like http://localhost:3030/{dataset}
            logger.critical("For Fuseki endpoint, the endpoint parameter is compulsory")
            raise ValueError("For Fuseki endpoint, the endpoint parameter is compulsory")
        if requests.get(params).status_code != requests.codes.ok:
            logger.critical("Fuseki is not reachable at {}".format(params))
            raise ConnectionError("Fuseki is not reachable at {}".format(params))
        return Fuseki(params)
    elif id.lower() == "rdflib":
        return RDFLibEndpoint()
    else:
        error = "'{}' not found in the available RDF endpoints list".format(id)
        logger.error(error)
        raise NotImplementedError(error)


class RDFEndpoint(ABC):
    """
    Abstract class for endpoints.

    Methods
    -------
    query(sparql)
        Queries the RDF endpoint.

    update(content)
        Makes the update available in 'content' to the RDF endpoint.
    """
    @abstractmethod
    def query(self, sparql):
        """Queries the RDF endpoint.

        Parameters
        ----------
        sparql : str
            The SPARQL query to be done

        Returns
        -------
        tuple (str, requests.status_code)
            query output and, if applicable, the status code or a boolean to
            indicate success or failure
        """
        pass

    @abstractmethod
    def update(self, content):
        """Makes the update available in 'content' to the RDF endpoint.

        Parameters
        ----------
        content : str
            The update to be done: may be SPARQL Update, .ttl, .n3

        Returns
        -------
        tuple (response, requests.status_code)
            update output response, the status code or a boolean to indicate
            success or failure
        """
        pass


class Blazegraph(RDFEndpoint):
    def __init__(self, params):
        """
        Parameters
        ----------
        params : str
            if None, defines the standard uri for blazegraph 'http://localhost:9999/bigdata/sparql'
            else it contains the appropriate uri
        """
        self.endpoint_uri = params if params else "http://localhost:9999/bigdata/sparql"

    def query(self, sparql):
        logger.debug("Sparql query to blazegraph at {}".format(self.endpoint_uri))
        r = requests.get(
            self.endpoint_uri,
            headers={"Accept": "application/sparql-results+json"},
            params={"query": sparql})
        logger.info("Query request got status {}".format(r.status_code))
        return r.text.encode(), (r.status_code == requests.codes.ok)

    def update(self, content, format="sparql"):
        """Makes the update available in 'content' to the RDF endpoint.

        Parameters
        ----------
        content : str
            The update to be done

        format : str, optional
            defaults to 'sparql', this parameter tells the code how to
            interpret the content string

        Raises
        ------
        NotImplementedError
            if the format is not one of 'sparql', 'ttl', 'n3'

        Returns
        -------
        tuple (response, requests.status_code)
            update output response, the status code
        """
        # content may be sparql or .ttl or .n3
        l_format = format.lower()
        if l_format == "sparql":
            r = requests.post(self.endpoint_uri, params={"update": content})
        elif l_format == "ttl":
            r = requests.post(
                self.endpoint_uri,
                headers={"Content-Type": "application/x-turtle"},
                data=content)
        elif l_format == "n3":
            r = requests.post(
                self.endpoint_uri,
                headers={"Content-Type": "text/rdf+n3"}, data=content)
        else:
            error = "Format '{}' is unavailable".format(format)
            logger.error(error)
            raise NotImplementedError(error)
        logger.info("Update request got status {}".format(r.status_code))
        return r, (r.status_code == requests.codes.ok)


class Fuseki(RDFEndpoint):
    def __init__(self, params):
        """
        Parameters
        ----------
        params : defines the uri for fuseki 'http://localhost:3030/{dataset}'
            must not be None

        Raises
        ------
        ValueError
            if params is None
        """
        if params is None:
            raise ValueError("Fuseki initialization params must not be None")
        self.endpoint_uri = params

    def query(self, sparql):
        logger.debug("Sparql query to fuuseki at {}".format(self.endpoint_uri))
        r = requests.post(
            self.endpoint_uri + "/query",
            headers={"Content-Type": "application/sparql-query"},
            data=sparql)
        logger.info("Query request got status {}".format(r.status_code))
        return r.text.encode(), (r.status_code == requests.codes.ok)

    def update(self, content, format="sparql"):
        """Makes the update available in 'content' to the RDF endpoint.

        Parameters
        ----------
        content : str
            The update to be done

        format : str, optional
            defaults to 'sparql', this parameter tells the code how to
            interpret the content string

        Raises
        ------
        NotImplementedError
            if the format is not one of 'sparql', 'ttl', 'n3'

        Returns
        -------
        tuple (response, requests.status_code)
            update output response, the status code
        """
        # content may be sparql or .ttl or .n3
        l_format = format.lower()
        if l_format == "sparql":
            r = requests.post(
                self.endpoint_uri + "/update",
                headers={"Content-Type": "application/sparql-update"},
                data=content)
        elif l_format == "ttl" or l_format == "n3":
            r = requests.post(
                self.endpoint_uri + "/data",
                headers={"Content-Type": "text/n3; charset=utf-8"},
                data=content)
        else:
            error = "Format '{}' is unavailable".format(format)
            logger.error(error)
            raise NotImplementedError(error)
        logger.info("Update request got status {}".format(r.status_code))
        fail = True
        try:
            fail = r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(e)
        return r, (fail is None)


class RDFLibEndpoint(RDFEndpoint):
    def __init__(self, format="json"):
        """Parameters
        ----------
        format : str, optional
            Default to 'json', represents the serialize format of outputs
            See rdflib to know all available formats
        """
        self.graph = Graph()
        self._query_format = format

    @property
    def queryFormat(self):
        """Getter for the serialize format of outputs"""
        return self._query_format

    @queryFormat.setter
    def queryFormat(self, newformat):
        """Parameters
        ----------
        newformat : str
            new format for serialization of outputs.
        """
        self._query_format = newformat

    def query(self, sparql):
        query = None
        try:
            query = self.graph.query(sparql).serialize(format=self.queryFormat)
        except Exception as e:
            logging.error(e)
            return None, False
        return query, True

    def update(self, content, format="sparql"):
        try:
            if format == "sparql":
                update = self.graph.update(content)
            else:
                update = self.graph.parse(data=content, format=format)
        except Exception as e:
            logging.error(e)
            return None, False
        return update, True
