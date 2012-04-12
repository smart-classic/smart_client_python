import re

class SMART_Querier(object):

    @classmethod
    def query(cls, 
              stype, 
              bindings = None,
              single_patient = False,
              extra_filters=""):

        ret = """
        BASE <http://smartplatforms.org/terms#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        CONSTRUCT { $construct_triples }
        """

        ret += """WHERE {
           graph ?root_subject  {
               $query_triples 
               $filter_clause
           }
        }
        """

        q = QueryBuilder(stype, "?root_subject")
        b = q.build()

        ret = ret.replace("$construct_triples", q.construct_triples())
        ret = ret.replace("$query_triples", b)        
        ret = ret.replace("$filter_clause", extra_filters)

        if bindings:
            ret += " BINDINGS ?root_subject {\n(" + ")\n(".join([
                        x.n3() for x in bindings
                   ]) +")}"

        return ret

class QueryBuilder(object):
    def __init__(self, root_type, root_name):
        self.root_type = root_type
        self.triples_created = []
        self.identifier_count = {}
        self.root_name = self.get_identifier(root_name)

    def construct_triples(self):
        return "\n ".join(self.triples_created)
        
    def get_identifier(self, id_base, role=""):
        if id_base.startswith("<") or id_base.startswith("_:"): return id_base
        
        start = id_base[0] == "?" and "?" or ""

        if "/" in id_base:
          id_base = id_base.rsplit("/", 1)[1]
        if "#" in id_base:
          id_base = id_base.rsplit("#", 1)[1]

        id_base = re.sub(r'\W+', '', id_base)
        id_base = start + id_base
        if role != "":
            id_base = id_base + "_" + role

        self.identifier_count.setdefault(id_base, 0)
        self.identifier_count[id_base] += 1
        ret = "%s"%id_base
        c = self.identifier_count[id_base]
        if c > 1:
            ret += "_%s"%c
        return ret

    def required_triple(self, root_name, pred, obj):
        self.triples_created.append("%s %s %s. " % (root_name, pred, obj))
        return " %s %s %s. \n" % (root_name, pred, obj)

    def optional_triple(self, root_name, pred, obj):
        self.triples_created.append("%s %s %s. " % (root_name, pred, obj))
        return " OPTIONAL { %s %s %s. } \n" % (root_name, pred, obj)
        
    def optional_linked_type(self, linked_type, root_name,  predicate, object, depth):
        self.triples_created.append("%s %s %s. " % (root_name, predicate, object))
        ret = " OPTIONAL { %s %s %s. $insertion } \n" % (root_name, predicate, object)
        repl = self.build(object, linked_type, depth)
        ret = ret.replace("$insertion", repl)
        return ret

    def build(self, root_name=None, root_type=None, depth=0):
        ret = ""

        # Recursion starting off:  set initial conditions (if any).
        if root_type == None:
            root_name = self.root_name
            root_type = self.root_type            
            ret = " ".join(self.triples_created)
            ret += self.required_triple(root_name, 
                             "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", 
                             root_type.uri.n3())
        else:
            ret += self.optional_triple(root_name, 
                             "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", 
                             self.get_identifier("?type", "object"))

        for prop in root_type.object_properties:
                oid = self.get_identifier("?"+prop.uri.n3(), "object")


                newdepth = depth
                if prop.to_class.is_statement :
                    newdepth += 1
   
                if ( (depth == 0 or not prop.to_class.is_statement)  and 
                      str(prop.to_class.uri) != "http://smartplatforms.org/terms#MedicalRecord"):

                    ret += self.optional_linked_type(linked_type=prop.to_class, 
                                             root_name=root_name,
                                             predicate=prop.uri.n3(),
                                             object=oid, 
                                             depth=newdepth)

                else: # if we're comming to another statement, bottom out the recursion
                    ret += self.optional_triple(root_name, prop.uri.n3(), oid)

        for prop in root_type.data_properties:
                oid = self.get_identifier("?"+prop.uri.n3(), "object")
                ret += self.optional_triple( root_name, prop.uri.n3(),oid)
        
        return ret
