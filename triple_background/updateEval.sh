#! /bin/bash


rm *.ttl
for i in {1..5000..1000}
do
   curl "https://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query=select+*+where+%7B%3Fa+%3Fb+%3Fc%7D+LIMIT+$i&format=text%2Fturtle&timeout=30000&signal_void=on&signal_unconnected=on" -o ./triples$i.ttl
   python updateEval.py ./triples$i.ttl localhost 40
done