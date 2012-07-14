import sys
tmp = sys.stdout
sys.stdout=sys.stderr
from client import SMARTClient

CONSUMER_TOKENS = {'consumer_key': 'my-app@apps.smartplatforms.org', 
                      'consumer_secret': 'smartapp-secret'}

api_base = 'http://localhost:7000'


"""An important static var"""
s = SMARTClient(api_base, CONSUMER_TOKENS)

import pydoc
t = pydoc.TextDoc()

# TextDoc default behavior wrecks havoc with markdown interpretation.
# So strip out the " |" line beginnings...
sys.stdout = tmp
d = t.docclass(SMARTClient)
d = pydoc.plain(d)
print """SMART Python Client Library

To generate this README:

  $ python generate_readme.py > README

---

"""
print d
