import sys
import pydoc
import re

from client import SMARTClient

CONSUMER_TOKENS = {
	'consumer_key': 'my-app@apps.smartplatforms.org',
	'consumer_secret': 'smartapp-secret'
}

api_base = 'http://localhost:7000'

tmp = sys.stdout
sys.stdout = sys.stderr

# instantiate our client and TextDoc 
s = SMARTClient(api_base, CONSUMER_TOKENS)
t = pydoc.TextDoc()
#t = pydoc.HTMLDoc()

sys.stdout = tmp
d = t.docclass(SMARTClient)
d = pydoc.plain(d)
# TextDoc default behavior wrecks havoc with markdown interpretation.
# So strip out the " |" line beginnings...
d = re.sub(r"\n\s*\|", "\n", d)

print """SMART Python Client Library
===========================

To generate this README:

    $ python generate_readme.py > README

---

"""

print d
