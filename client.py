import oauth2 as oauth
import httplib2
import urllib
import urlparse
import re
import os
import os.path
import base64
import hmac
import hashlib
import json
from generate_api import SmartResponse, augment

import common.rdf_tools.rdf_ontology
import common.rdf_tools.util

KNOWN_SERVERS = {}

# Configuration file defining valid SMART API calls

class SMARTClientError(Exception):
    pass

class SMARTClient(oauth.Client):
    """ Establishes OAuth communication with an SMART Container, and provides access to the API. """

    def __init__(self, app_id, api_base, consumer_params, **state_vars):
        if consumer_params.get('consumer_key') is None \
            or consumer_params.get('consumer_secret') is None:
            raise SMARTClientError('We need both "consumer_key" and "consumer_secret" in the params dictionary, only got: %s' % consumer_params)

        consumer = oauth.Consumer(consumer_params['consumer_key'], consumer_params['consumer_secret'])
        super(SMARTClient, self).__init__(consumer)

        self.app_id = app_id
        self.api_base = api_base
        self._record_id = None

        # Set extra state that was passed in (i.e. record_id, app_email, etc.)
        for var_name, value in state_vars.iteritems():
            setattr(self, var_name, value)
 
        if self.api_base not in KNOWN_SERVERS:
            resp, content = self.get('manifest')
            assert resp.status == 200, "Failed to fetch container manifest"
            KNOWN_SERVERS[self.api_base] = json.loads(content)

        self.container_manifest = KNOWN_SERVERS[self.api_base]

    @property
    def record_id(self):
        return self._record_id
    
    @record_id.setter
    def record_id(self, new_record_id):
        if self._record_id != new_record_id:
            self._record_id = new_record_id
            self.token = None

    def loop_over_records(self):    
        """Iterator allowing background apps to loop through each patient
        record in the SMArt container, e.g. to perform reporting or analytics.
        For each patient record in the container, sets access tokens on the
        SmartClient object and yields the new record_id."""

        r = self.post("/apps/%s/tokens/records/first" % self.app_id)
        
        while r:
            status = r[0].get('status')
            if '200' != status:
                raise Exception('Did not get token: %s (%s)' % (r[1], status))
            
            p = {}
            for pair in r[1].split('&'):
                (k, v) = [urllib.unquote_plus(x) for x in pair.split('=')] 
                p[k]=v
            
            record_id = p['smart_record_id']
            self.record_id = record_id
            self.update_token(p)
            yield record_id
            
            self.record_id = None
            try:
                r = self.post("/apps/%s/tokens/records/%s/next" % (self.app_id, record_id))
            except:
                break


    def absolute_uri(self, uri):
        if uri[:4] == "http":
            return uri
        while '/' == uri[:1]:
            uri = uri[1:]
        return os.path.join(self.api_base, uri)

    def get(self, uri, body={}, headers={}, **uri_params):
        """ Make an OAuth-signed GET request to SMART Server. """

        # append the body data to the querystring
        if isinstance(body, dict) and len(body) > 0:
            body = urllib.urlencode(body)
            uri = "%s?%s" % (uri, body) if body else uri

        return self.request(self.absolute_uri(uri), uri_params, method="GET", body='', headers=headers)

    def put(self, uri, body='', headers={}, content_type=None, **uri_params):
        """ Make an OAuth-signed PUT request to SMART Server. """
        if content_type:
            headers['Content-Type'] = content_type
        if isinstance(body, dict):
            body = urllib.urlencode(body)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        return self.request(self.absolute_uri(uri), uri_params, method="PUT", body=body, headers=headers)

    def post(self, uri, body='', headers={}, content_type=None, **uri_params):
        """ Make an OAuth-signed POST request to SMART Server. """
        if content_type:
            headers['Content-Type'] = content_type
        if isinstance(body, dict):
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            body = urllib.urlencode(body)
        return self.request(self.absolute_uri(uri), uri_params, method="POST", body=body, headers=headers)

    def delete(self, uri, headers={}, **uri_params):
        """ Make an OAuth-signed DELETE request to SMART Server. """
        return self.request(self.absolute_uri(uri), uri_params, method="DELETE", headers=headers)


    def update_token(self, resource_token):
        """ Update the resource token used by the client to sign requests. """
        if isinstance(resource_token, oauth.Token):
            self.token = resource_token
        else:
            token = oauth.Token(resource_token['oauth_token'], resource_token['oauth_token_secret'])
            self.token = token

    def fetch_request_token(self, params={}):
        """ Get a request token from the server. """
        if self.token:
            raise SMARTClientError("Client already has a resource token.")

        # make sure we have the record id
        if params.get('smart_record_id') is None and self.record_id is not None:
            params['smart_record_id'] = self.record_id

        # "oauth_callback" can only be "oob" anyway, so just set it
        params['oauth_callback'] = 'oob'

        resp, content = self.post(self.container_manifest['launch_urls']['request_token'], body=params)
        if resp['status'] != '200':
            raise SMARTClientError("%s response fetching request token: %s" % (resp['status'], content))
        req_token = dict(urlparse.parse_qsl(content))
        self.update_token(req_token)
        return req_token

    @property
    def auth_redirect_url(self):
        if not self.token:
            raise SMARTClientError("Client must have a token to get a redirect url")
        return self.container_manifest['launch_urls']['authorize_token'] + "?oauth_token=" + self.token.key

    def exchange_token(self, verifier):
        """ Exchange the client's current token (should be a request token) for an access token. """
        if not self.token:
            raise SMARTClientError("Client must have a token to exchange.")
        
        self.token.set_verifier(verifier)
        resp, content = self.post(self.container_manifest['launch_urls']['exchange_token'])
        if resp['status'] != '200':
            raise SMARTClientError("%s response fetching access token: %s"%(resp['status'], content))
        access_token = dict(urlparse.parse_qsl(content))
        self.update_token(access_token)

        for var_name, value in access_token.iteritems():
            if not var_name.startswith("oauth_"):
                setattr(self, var_name, value)

        return access_token

    def get_surl_credentials(self):
        """ Produces a token and secret for signing URLs."""
        if not self.token:
            raise SMARTClientError("Client must have a token to generate SURL credentials.")
        secret = base64.b64encode(hmac.new(self.token.secret, "SURL-SECRET", hashlib.sha1).digest())
        return {'token': self.token.key, 'secret': secret}

    def _fill_url_template(self, url, **kwargs):
        for param_name in re.findall("{(.*?)}", str(url)):
            arg_name = param_name.lower()
            try:
                v = kwargs[arg_name]
            except KeyError as e:
                # Is it a direct attribute of the client? i.e. client.record_id
                try:
                    v = getattr(self, arg_name)
                except AttributeError:
                    raise KeyError("Expected argument %s" % arg_name)

            url = url.replace("{%s}"%param_name, v)
        return url

    def request(self, uri, uri_params, *args, **kwargs):
        uri = self._fill_url_template(uri, **uri_params)
        return super(SMARTClient, self).request(uri, *args, **kwargs)

if (not common.rdf_tools.rdf_ontology.parsed):
    assert False, "No ontology found"

augment(SMARTClient)
