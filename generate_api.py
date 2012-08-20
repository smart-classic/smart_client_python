"""
Generate all API methods from SMArt OWL ontology
"""

import os, re, json
import common.rdf_tools.rdf_ontology as rdf_ontology

pFormat = "{.*?}"

class SmartResponse:
    def __init__ (self, body, contentType = "text/plain", graph = None, json = None):
        self.body = body
        self.contentType = contentType
        self.graph = graph
        self.json = json

def fill_url_template(call, *args, **kwargs):
    url =  str(call.path)

    # Look for each param in kwargs.  
    for p in params(call):
        try:  
            v = kwargs[p]
            url = url.replace("{%s}"%p, v)
        except KeyError as e:
            # If not found, try to find it as a direct attribute of the SmartClient
            try: v = getattr(kwargs['_client'], p)
            except: 
                raise e
        url = url.replace("{%s}"%p, v)
    return url

def params(call):
    return [x[1:-1] for x in re.findall(pFormat, str(call.path))]
    
def get_query_params(call, *args, **kwargs):
    queryParams = {}

    if call.cardinality == "multiple":
        queryParams['limit'] = kwargs.get('limit', None)
        queryParams['offset'] = kwargs.get('offset', None)
        
    for p in call.parameters + call.filters:
        param_name = str(p.client_parameter_name)
        queryParams[param_name] = kwargs.get(param_name, None)
        
    return {k:queryParams[k] for k in queryParams if queryParams[k]}

def make_generic_call(call):
    def c(self, *args, **kwargs):
        kwargs['_client'] = self
        url = fill_url_template(call, **kwargs)
        data = kwargs.get('data', None)
        query_params = get_query_params (call, **kwargs)
        content_type = kwargs.get('content_type', None)
        f = getattr(self, str(call.http_method).lower())          
        res =  f(url=url, query_params=query_params, data=data, content_type=content_type)
        ct = res.contentType
        
        try:
            return SmartResponse (res.body, ct, self.data_mapper(res.body), None)
        except:
            pass
            
        try:
            return SmartResponse (res.body, ct, None, json.loads(res.body))
        except:
            pass
            
        return SmartResponse (res.body, ct)
                
    return c

def augment(client_class):
    for c in rdf_ontology.api_calls:
        call = make_generic_call(c)
        call.__doc__ = """%s %s

%s

Returns RDF Graph containing:  %s
     """%(c.http_method, c.path, c.description, c.target)
        setattr(client_class, c.client_method_name, call)
