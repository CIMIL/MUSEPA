# How to use MUSEPA

Hello! If you are reading this, it's very likely that you want to use MUSEPA (formerly, cMinor v2).

The software has been slightly modified since the previous version that was described in [this](https://ieeexplore.ieee.org/abstract/document/8588087) paper:

Viola, F., Turchet, L., Antoniazzi,
F., & Fazekas, G. (2018, November). C minor: a semantic publish/subscribe broker for the internet of musical things. In *2018 23rd Conference of Open Innovations Association (FRUCT)* (pp. 405-415). IEEE.

So, let's start here to use **MUSEPA**.

## 1. First things to do

The most stable version of MUSEPA will be stored in [this](https://github.com/fr4ncidir/MUSEPA.git) repository, at _master_ branch.
So, the first thing to do is

```
$ git clone https://github.com/fr4ncidir/MUSEPA.git
```

The second thing that would be wise to do is to create a Python3 virtual environment. This is not compulsory, but yet highly recommended. This is usually done this way

```
$ cd 'your_folder'
$ virtualenv -p python3 ./venv
$ source ./venv/bin/activate
```

At this point, your Python3 virtual environment is activated, and we can proceed with MUSEPA.

## 2. Installing requirements

There should be a `requirements.txt` file in the repository. So, to install every required library, you should type

```
$ pip3 install -r requirements.txt
```

We are now ready to run MUSEPA.

## 3. Running MUSEPA

First of all, since MUSEPA works with an RDF store, you have to decide if to run Fuseki, or Blazegraph, or to use rdflib to store your triples. If you want to use Blazegraph, go to section 3.1; otherwise, section 3.2 for rdflib and section 3.3 for Fuseki.

Consider that Blazegraph is available, but tests show that it is not the most performant RDF endpoint;

#### 3.1 MUSEPA over a Blazegraph endpoint

Of course, you must run a Blazegraph instance. Please refer to [Blazegraph website](https://blazegraph.com/) to know how to do this.

Once this is done, the first thing to try is:

```
$ python3 musepa.py --endpoint blazegraph --help
```

Have also a look to 3.3, for the usage of the `--endpoint-param` option.

#### 3.2 MUSEPA on a rdflib endpoint

There is nothing to install in this case. The drawback of using rdflib is that MUSEPA doesn't provide a way to store permanently triples when we use rdflib. This means that if you close MUSEPA, you lose your knowledge base.

```
$ python musepa.py --endpoint rdflib
```

This is equivalent to the following call, that is meant to be _the standard way to call MUSEPA_ (i.e., with an RDFlib endpoint running, and listening on localhost.

```
$ python3 musepa.py 
```

#### 3.3 MUSEPA on a Fuseki endpoint

As we did for Blazegraph, a running Fuseki instance is needed in this case. Refer to [this](https://jena.apache.org/download/index.cgi) website.

For the Fuseki case, it is necessary to introduce a new command line parameter, `--endpoint-param`. This parameter will be used to define the actual location of fuseki, included the dataset of interest in our application. Let's imagine that the dataset is called `musepa_dataset` and that Fuseki is running on `http://localhost:3030`: in this case, you'll run MUSEPA as the following:

```
$ python musepa.py --endpoint fuseki --endpoint-param http://localhost:3030/musepa
```

## 4. Using MUSEPA

The interaction with MUSEPA can be of 3 different types:

- Query
- Update
- Subscribe

#### 4.1 Query

As it is done with any SPARQL RDF endpoint, e.g. Blazegraph, you can use the SPARQL language to issue a query to MUSEPA. Since MUSEPA can be contacted through CoAP protocol, you need to build a CoAP request like the following, depending of course on your host setup.

```
COAP GET
Host: coap://localhost/sparql/query

Payload:
SELECT * WHERE {
    ?a ?b ?c
}
```

The response payload will contain the bindings of the result, or an error code.

#### 4.2 Update

You can use the SPARQL language to issue an update to MUSEPA. Since MUSEPA can be contacted through CoAP protocol, you need to build a CoAP request like the following, depending of course on your host setup.

```
COAP POST
Host: coap://localhost/sparql/update

Payload:
PREFIX : <http://musepa/Example#>
INSERT DATA {
   :subject :predicate :object.
}
```

The response payload may contain some result. However, it always contains a success (or error) code.

Notice that it is also possible to make an update like the following:

```
COAP POST
Host: coap://localhost/sparql/update?format=ttl

Payload:
@prefix : <http://musepa/Example#>.
:subject :predicate :object.
```

Issuing in this way a request on a turtle (or n3, or rdf/xml) file, instead that with SPARQL.

#### 4.3 Subscribe

The subscription creation is a two step procedure: (i) creation of the subscription resource; (ii) observation of the resource.

##### _4.3.1 Creation of the resource_

To create a subscription in MUSEPA, you have to issue a request like the following:

```
COAP POST
Host: coap://localhost/sparql/subscription

Payload:
SELECT * WHERE {
   ?a ?b ?c
}
```

Once this request is received, MUSEPA creates a new subscription resource that is reachable at `coap://localhost/{payload_hash}`. Such hash will be returned back to the client within the payload. So, if the payload is `SELECT * WHERE {?a ?b ?c}`, the created resource will be located at `coap://localhost/11354c8e688bcd6f6da34c6293be8cac`. In this way, if two clients issue an identical subscription, they just end up in being addressed to observe the same resource.

##### _4.3.1 Observe the resource_

Once you are ready, you can observe the resource `coap://localhost/11354c8e688bcd6f6da34c6293be8cac` with your coap APIs and be notified about events.

What are these events? Let's identify some examples.

1. Let's imagine that the RDF store is empty at the beginning. We (CLIENT1) request a subscription like the one in 4.3.1 `SELECT * WHERE {?a ?b ?c}`. We then start the observation.

Another client (CLIENT2) now makes an update like the following:

```
COAP POST
Host: coap://localhost/sparql/update

Payload:
PREFIX : <http://musepa/Example#>
INSERT DATA {
   :subject :predicate :object.
}
```

CLIENT1 will now be notified that something happened. In particular, the subscription query `SELECT * WHERE {?a ?b ?c}` is made by MUSEPA _before_ and _after_ the update. Since the two results are different, (before=`empty`, after=`{a=:subject, b=:predicate, c=:object}`, the contents of _after_ is sent as a notification to the client.

This means that if nothing changes, no notification is issued.

2. If CLIENT2 makes another update:

```
COAP POST
Host: coap://localhost/sparql/update

Payload:
PREFIX : <http://musepa/Example#>
INSERT DATA {
   :sub :pred :obj.
}
```

Since the two results are different, (before=`{a=:subject, b=:predicate, c=:object}`, after=`{[a=:subject, b=:predicate, c=:object], [a=:sub, b=:pred, c=:obj]}`, the contents of _after_ is sent as a notification to the client.

Notice that there is here the great difference with SEPA implementations: we don't retransmit added/removed bindings: we just retransmit the whole query result.

## 5. The cCoap tool

cCoap is a script that easily makes CoAP calls for MUSEPA. So, if you want to make a query:

```
$ python3 cCoap.py -a coap://localhost/sparql/query -p "SELECT * WHERE {?a ?b ?c}"
```

If you want to make an update:

```
$ python3 cCoap.py -a coap://localhost/sparql/update -p "PREFIX : <http://musepa/Example#> INSERT DATA {:sub :pred :obj}" --verb POST
```


If you want to make an update with a turtle file:

```
$ python3 cCoap.py -a coap://localhost/sparql/update?format=ttl -p "@prefix : <http://musepa/Example#>. :subject :predicate :object." --verb POST
```

If you want to make a subscription request:

```
$ python3 cCoap.py -a coap://localhost/sparql/subscription -p "SELECT * WHERE {?a ?b ?c}" --verb POST
```

If you want to observe the subscription resource:

```
$ python3 cCoap.py -a coap://localhost/11354c8e688bcd6f6da34c6293be8cac -o
```

If you need to create your own MUSEPA client, you will probably start by having a look to the cCoap.py source code.

## The `--prefixes` option
By reading this file, you probably noticed that each time we had to send a request to MUSEPA, it was necessary to send all the needed prefixes.
MUSEPA allows to avoid this by calling the `--prefixes` option.

First of all, you have to create a file. Let's consider that the file is `{path}\my_prefix_file`.
_It must be filled as if it was a .ttl file_, and the 'unnamed prefix' is not allowed (i.e., the prefix that is just ':'). Here's an example:
```
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
```
You can then call MUSEPA like this:
```
$ python musepa.py --prefixes {path}\my_prefix_file
```

And from now on, there will be no need to transmit at each interaction these prefixes.

## Examples

See the client_examples folder for some easy-to-copy examples, to learn how to code your clients.

You can do updates:
```
$ cd ./client_examples
$ python musepa_update.py -a 127.0.0.1 -p "insert data {<http://a> <http://b> <http://c>}"
$ python musepa_update.py -a 127.0.0.1 -p "<http://a> <http://b> <http://c>." --ttl
$ python musepa_update.py -a 127.0.0.1 -p ./update_file_sparql_content.sparql
$ python musepa_update.py -a 127.0.0.1 -p ./update_file_ttl_content.ttl --ttl
```

You can do queries:
```
$ python musepa_query.py -a 127.0.0.1 -p "select ?b ?c where {?a ?b ?c}"
$ python musepa_query.py -a 127.0.0.1 -p ./query_file_sparql_content.sparql
```

You can do subscriptions:
```
$ python musepa_subscribe_observe.py -a 127.0.0.1 -p "select ?b ?c where {?a ?b ?c}"
$ python musepa_subscribe_observe.py -a 127.0.0.1 -p ./query_file_sparql_content.sparql
```

##### Authors:

[Francesco Antoniazzi](mailto:francesco.antoniazzi@emse.fr)

[Jehad Melad](jehad.melad@emse.fr)
