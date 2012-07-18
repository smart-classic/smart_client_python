import oauth2 as oauth
import httplib2
import urllib
import urlparse
import re
import os
import base64
import hmac
import hashlib
import json
from generate_api import SmartResponse, augment

import common.rdf_tools.rdf_ontology
import common.rdf_tools.util

KNOWN_SERVERS = {}

# Configuration file defining valid SMART API calls
CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'common', 'schema', 'smart.owl')

class SMARTClientError(Exception):
    pass

class SMARTClient(oauth.Client):
    """ Establishes OAuth communication with an SMART Container, and provides access to the API. """

    def __init__(self, api_base, consumer_params, resource_token=None, **state_vars):
        consumer = oauth.Consumer(consumer_params['consumer_key'], consumer_params['consumer_secret'])
        super(SMARTClient, self).__init__(consumer)

        if resource_token:
            self.update_token(resource_token)
                               
        self.api_base = api_base
        # Set extra state that was passed in (i.e. record_id, app_email, etc.)
        for var_name, value in state_vars.iteritems():
            setattr(self, var_name, value)
 
        if (not common.rdf_tools.rdf_ontology.parsed):
            f = open(CONFIG_FILE, 'r')
            self.__class__.ontology_file = f.read()
            f.close()
            common.rdf_tools.rdf_ontology.parse_ontology(SMARTClient.ontology_file)
            augment(self.__class__)

        if self.api_base not in KNOWN_SERVERS:
            resp, content = self.get('/manifest')
            assert resp.status == 200, "Failed to fetch container container manifest"
            KNOWN_SERVERS[self.api_base] = json.loads(content)

        self.container_manifest = KNOWN_SERVERS[self.api_base]

    def absolute_uri(self, uri):
        if uri[:4]=="http":
            return uri
        return self.api_base+uri

    def get(self, uri, body={}, headers={}, **uri_params):
        """ Make an OAuth-signed GET request to SMART Server. """

        # append the body data to the querystring
        if isinstance(body, dict):
            body = urllib.urlencode(body)
            uri = "%s?%s"%(uri, body) if body else uri

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
        resp, content = self.post(self.container_manifest['launch_urls']['request_token'], body=params)
        if resp['status'] != '200':
            raise SMARTClientError("%s response fetching request token: %s"%(resp['status'], content))
        req_token = dict(urlparse.parse_qsl(content))
        self.update_token(req_token)
        return req_token

    @property
    def auth_redirect_url(self):
        if not self.token:
            raise SMARTClientError("Client must have a token to get a redirect url")
        return self.container_manifest['launch_urls']['authorize_token'] + "?oauth_token="+self.token.key
        
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
                    raise KeyError("Expected argument %s"%arg_name)

            url = url.replace("{%s}"%param_name, v)
        return url

    def request(self, uri, uri_params, *args, **kwargs):
        uri = self._fill_url_template(uri, **uri_params)
        return super(SMARTClient, self).request(uri, *args, **kwargs)
