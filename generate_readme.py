import sys
tmp = sys.stdout
sys.stdout=sys.stderr
from smart import SmartClient

SMART_SERVER_OAUTH = {'consumer_key': 'developer-sandbox@apps.smartplatforms.org', 
                      'consumer_secret': 'smartapp-secret'}

SMART_SERVER_PARAMS = {'api_base' :          'http://sandbox-api.smartplatforms.org'}


"""An important static var"""
s = SmartClient(SMART_SERVER_OAUTH['consumer_key'], 
                       SMART_SERVER_PARAMS, 
                       SMART_SERVER_OAUTH)


import pydoc
t = pydoc.TextDoc()

# TextDoc default behavior wrecks havoc with markdown interpretation.
# So strip out the " |" line beginnings...
sys.stdout = tmp
d = t.docclass(SmartClient)
for l in d.split("\n"):
  try:
    if l[0:2] == " |":
      l = "  " + l[2:]
  except: pass
  print l
