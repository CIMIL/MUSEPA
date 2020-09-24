#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  prefix.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#  Jehad MELAD              <jehad.melad@etu.univ-st-etienne.fr>
#

import logging
import re

from os.path import isfile

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s   %(asctime)-15s %(filename)s[%(lineno)d] : %(message)s")

class Prefixes():
    """This class includes the utilities needed when the MUSEPA --prefixes option is called"""
    def __init__(self, path_to_file="", silent=False):
        self._prefix_dict = {}
        self._ttl = ""
        self._sparql = ""
        
        if path_to_file:
            if isfile(path_to_file):
                # The prefix file has to be given in ttl format
                prefix_regex = re.compile(r"@(?:prefix|PREFIX)[ \t]+(?P<tag>[a-zA-Z]*)[ \t]*:[ \t]*<(?P<namespace>.+)>[ \t]*\.")
                with open(path_to_file, "r") as prefix_file:
                    pfxs = prefix_file.readlines()
                    
                    self._ttl = "".join(pfxs)
                    
                    for item in pfxs:
                        group = prefix_regex.match(item)
                        if group is None:
                            logger.error("No match in {}".format(path_to_file))
                        else:
                            logger.debug("{}: {}".format(group["tag"], group["namespace"]))
                            self._prefix_dict[group["tag"]] = group["namespace"]
                            self._sparql += "PREFIX {}: <{}>\n".format(group["tag"], group["namespace"])
            else:
                raise ValueError("{} is not a file".format(path_to_file))
        elif not silent:
            logger.warning("No prefix file added")

    @property
    def sparql(self):
        return self._sparql

    @property
    def ttl(self):
        return self._ttl
    
    @property
    def dictionary(self):
        return self._prefix_dict

    def addPrefix(self, tag, namespace):
        if tag in self._prefix_dict:
            raise ValueError("Duplicate prefix request")
        else:
            self._prefix_dict[tag] = namespace
            self._sparql += "PREFIX {}: <{}> \n".format(group["tag"], group["namespace"])
            self._ttl += "@prefix {}: <{}> .\n".format(group["tag"], group["namespace"])

    def applyTo(self, content):
        """
        This function applies the prefixes to the 'content' variable. That is, if the content is 
        'http://francesco#test' and there is a prefix 'ns: <http://francesco#>', the returned value 
        will be 'ns:test'
        """
        n_content = content.decode()
        for prefix, value in self._prefix_dict.items():
            n_content = n_content.replace(value, prefix+':')
        return n_content.encode()