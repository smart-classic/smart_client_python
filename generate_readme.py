import sys
import pydoc
import re

from client import SMARTClient

tmp = sys.stdout
sys.stdout = sys.stderr

# instantiate TextDoc
t = pydoc.TextDoc()

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
