import rdflib
from rdflib import Namespace, URIRef, Literal, BNode
from StringIO import StringIO as sIO


rdflib.plugin.register('sparql', rdflib.query.Processor,
                       'rdfextras.sparql.processor', 'Processor')

rdflib.plugin.register('sparql', rdflib.query.Result,
                       'rdfextras.sparql.query', 'SPARQLQueryResult')

rdf = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
rdfs = Namespace('http://www.w3.org/2000/01/rdf-schema#')
owl = Namespace('http://www.w3.org/2002/07/owl#')
sp = Namespace('http://smartplatforms.org/terms#')
spcode = Namespace('http://smartplatforms.org/terms/codes/')
api = Namespace('http://smartplatforms.org/terms/api#')
foaf = Namespace("http://xmlns.com/foaf/0.1/")
vcard = Namespace("http://www.w3.org/2006/vcard/ns#")
dcterms = Namespace('http://purl.org/dc/terms/')
xsd = Namespace('http://www.w3.org/2001/XMLSchema#')

NS = {"sp":sp, "rdf":rdf, "rdfs":rdfs, "owl":owl, "xsd":xsd , "api":api, "foaf": foaf, "v": vcard, "spcode": spcode, "dcterms":dcterms}

anyuri = URIRef(NS['xsd']['anyURI'])

# metaclass to allow class-based dictionary look-up
class LookupType(type):
    def __getitem__(self, key):
        return self.__getitem__(key)

def serialize_rdf(model):
    return model.serialize(format="pretty-xml")

def parse_rdf(string, model=None):
    if model == None:
        model = bound_graph() 
    try:
        model.default_context.parse(data=string)
    except:
        model.default_context.parse(data=string, format="n3")

    return model

def get_property(model, s, p, raw_statement=False):
    r = model.triples((s, p, None))
    if (raw_statement): return r

    r = list(r)
    assert len(r) <= 1, "Expect at most one %s on subject %s; got %s"%(p, s, len(r))    
    if len(r) == 0: return None

    return rdfO(r[0])

def get_property_list(model, s, p):
    r = model.triples((s, p, None))

    return [x[2] for x in r]

def remap_node(model, old_node, new_node=None):
    for s in list(model.triples((old_node, None, None))):
        model.remove(s)
        s = (new_node, s[1], s[2])
        model.add(s)

    for s in list(model.triples((None, None, old_node))):
        model.remove(s)
        s = (s[0], s[1], new_node)
        model.add(s)

    return


def bound_graph():
    g = rdflib.ConjunctiveGraph()
    for p,v in default_ns.iteritems():
        g.bind(p,v)
    return g

def rdfS(s):
    return s[0];
def rdfP(s):
    return s[1];
def rdfO(s):
    return s[2];

default_ns = {}
for k,v in NS.iteritems():
      default_ns[k] = v
