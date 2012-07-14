"""
Generate all API methods from SMArt OWL ontology
"""

import os, re, json
import common
import common.rdf_tools.rdf_ontology as rdf_ontology

pFormat = "{.*?}"

class SmartResponse:
    def __init__ (self, resp, body):
        self.response = resp
        self.body = body

        try:
            self.graph =  common.rdf_tools.util.parse_rdf(body)
        except:
            self.graph = None
        try:
            self.json = json.loads(body)
        except:
            self.json = None

def call_name(call):
    ret = str(call.path)
    ret = ret.split("?")[0]
    ret = ret.replace("/", "_")
    ret = re.sub(pFormat, "_X", ret)
    ret = ret + "_" + str(call.method)
    ret = re.sub("_+", "_", ret)
    ret = re.sub("^_", "", ret)
    return ret

def params(call):
    return [x[1:-1] for x in re.findall(pFormat, str(call.path))]

def make_generic_call(call):
    def c(self, *args, **kwargs):
        url =  str(call.path)
        f = getattr(self, str(call.method).lower())          
        resp, body =  f(url, *args, **kwargs)
        return SmartResponse(resp, body)
    return c

def augment(client_class):
    for c in rdf_ontology.api_calls:
        call = make_generic_call(c)
        setattr(client_class, call_name(c), call)
        call.__doc__ = """%s %s

%s

Returns RDF Graph containing:  %s
     """%(c.method, c.path, c.description, c.target)
