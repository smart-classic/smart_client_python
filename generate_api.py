"""
Generate all API methods from SMART OWL ontology
"""

import os
import re
import json
import common
import common.rdf_tools.rdf_ontology as rdf_ontology

pFormat = "{.*?}"


class SmartResponse:
    def __init__(self, resp, body):
        self.response = resp
        self.body = body

        try:
            self.graph = common.rdf_tools.util.parse_rdf(body)
        except:
            self.graph = None
        try:
            self.json = json.loads(body)
        except:
            self.json = None


def params(call):
    return [x[1:-1] for x in re.findall(pFormat, str(call.path))]


def make_generic_call(call):
    def c(self, *args, **kwargs):
        url = str(call.path)
        f = getattr(self, str(call.http_method).lower())
        resp, body = f(url, *args, **kwargs)
        return SmartResponse(resp, body)
    return c


def augment(client_class):
    for c in rdf_ontology.api_calls:
        call = make_generic_call(c)
        setattr(client_class, c.client_method_name, call)
        call.__doc__ = """%s %s

%s

Returns RDF Graph containing:  %s
     """ % (c.http_method, c.path, c.description, c.target)
