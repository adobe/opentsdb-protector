#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import gzip
import httplib
import json
import logging
import socket
import time
import zlib
# import traceback
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from protector.proxy.http_request import HTTPRequest
from protector.query.query import OpenTSDBQuery, OpenTSDBResponse


class ProxyRequestHandler(BaseHTTPRequestHandler):

    protector = None
    backend_address = None

    def __init__(self, *args, **kwargs):

        self.http_request = HTTPRequest()
        self.tsdb_query = None

        # Address to time series backend
        backend_host, backend_port = self.backend_address
        self.backend_netloc = "{}:{}".format(backend_host, backend_port)

        self.scheme = "http"
        self.path = None
        self.connection = None
        self.rfile = None
        self.wfile = None
        self.close_connection = 0
        #self.timeout = 12

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_error(self, log_format, *args):

        # Suppress "Request timed out: timeout('timed out',)"
        # if isinstance(args[0], socket.timeout):

        # logging.error("{}".format(traceback.format_exc()))
        # logging.error(pprint.pprint(args))

        self.log_message(log_format, *args)

    def log_message(self, format, *args):

        """Log an arbitrary message.

        This is used by all other logging functions.  Override
        it if you have specific logging wishes.

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client ip address and current date/time are prefixed to every
        message.

        """
        if not getattr(self, "headers", None):
            xff = self.headers.getheader('X-Forwarded-For', '-')
            xgo = self.headers.getheader('X-Grafana-Org-Id', '-')
            ua = self.headers.getheader('User-Agent', '-')

            logging.info("%s - - [%s] %s [X-Forwarded-For: %s, X-Grafana-Org-Id: %s, User-Agent: %s]" %
                         (self.client_address[0], self.log_date_time_string(), format % args, xff, xgo, ua))
        else:
            logging.info("%s - - [%s] %s" %
                         (self.client_address[0], self.log_date_time_string(), format % args))

    def do_GET(self):

        if self.path == "/metrics":
            data = generate_latest()

            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.headers['Host'] = self.backend_netloc
            self.filter_headers(self.headers)
            self._handle_request(self.scheme, self.backend_netloc, self.path, self.headers)

        self.finish()
        self.connection.close()

    def do_POST(self):

        length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(length)

        self.headers['Host'] = self.backend_netloc
        self.filter_headers(self.headers)

        # Only process query requests, everything else should pass through
        if self.path == "/api/query":

            self.tsdb_query = OpenTSDBQuery(post_data)
            self.headers['X-Protector'] = self.tsdb_query.get_id()

            # Check the payload against the Protector rule set
            result = self.protector.check(self.tsdb_query)
            if not result.is_ok():
                self.protector.REQUESTS_BLOCKED.labels(self.protector.safe_mode, result.value["rule"]).inc()

                if not self.protector.safe_mode:
                    logging.warning("OpenTSDBQuery blocked: %s. Reason: %s", self.tsdb_query.get_id(), result.value["msg"])
                    self.send_error(httplib.FORBIDDEN, result.value["msg"])
                    return

            post_data = self.tsdb_query.to_json()

            self.headers['Content-Length'] = str(len(post_data))

        status = self._handle_request(self.scheme, self.backend_netloc, self.path, self.headers, body=post_data, method="POST")

        #['method', 'path', 'return_code']
        self.protector.REQUESTS_COUNT.labels('POST', self.path, status).inc()

        self.finish()
        self.connection.close()

    def send_error(self, code, message=None):
        """
        Send and log plain text error reply.
        :param code:
        :param message:
        """
        message = message.strip()
        self.log_error("code %d, message: %s", code, message)
        self.send_response(code)

        self.send_header("Content-Type", "application/json")
        self.send_header('Connection', 'close')
        self.end_headers()
        if message:
            # Grafana style
            j = {'message': message, 'error': message}
            self.wfile.write(json.dumps(j))

    def _handle_request(self, scheme, netloc, path, headers, body=None, method="GET"):
        """
        Run the actual request
        """
        backend_url = "{}://{}{}".format(scheme, netloc, path)
        startTime = time.time()

        try:
            response = self.http_request.request(backend_url, method=method, body=body, headers=dict(headers))

            respTime = time.time()
            duration = respTime - startTime

            self.protector.TSDB_REQUEST_LATENCY.labels(response.status).observe(duration)
            self._return_response(response, method, duration)

            return response.status

        except socket.timeout, e:

            respTime = time.time()
            duration = respTime - startTime

            if method == "POST":
                self.protector.save_stats_timeout(self.tsdb_query, duration)

            self.protector.TSDB_REQUEST_LATENCY.labels(httplib.GATEWAY_TIMEOUT).observe(duration)
            self.send_error(httplib.GATEWAY_TIMEOUT, "Query timed out. Configured timeout: {}s".format(20))

            return httplib.GATEWAY_TIMEOUT

        except Exception as e:

            respTime = time.time()
            duration = respTime - startTime

            #logging.error("{}".format(traceback.format_exc()))
            err = "Invalid response from backend: '{}'".format(e)
            logging.debug(err)
            self.protector.TSDB_REQUEST_LATENCY.labels(httplib.BAD_GATEWAY).observe(duration)
            self.send_error(httplib.BAD_GATEWAY, err)

            return httplib.BAD_GATEWAY

    def _process_response(self, payload, encoding, duration):
        """
        :param payload: JSON
        :param encoding: Content Encoding
        """
        try:
            resp = OpenTSDBResponse(self.decode_content_body(payload, encoding))
            self.protector.save_stats(self.tsdb_query, resp, duration)
        except Exception as e:
            err = "Skip: {}".format(e)
            logging.debug(err)

    def _process_bad_request(self, payload, encoding):
        """
        :param payload: JSON
        :param encoding: Content Encoding
        """
        # Re-package the error json for Grafana
        j = json.loads(self.decode_content_body(payload, encoding))
        err = j.get('error', None)
        b = {}

        if err:
            b = {'message': err.get('message', '?'), 'error': err.get('details', '?')}

        return self.encode_content_body(json.dumps(b), encoding)

    def _return_response(self, response, method, duration):
        """
        :param response: HTTPResponse
        """
        self.filter_headers(response.msg)
        #cl = response.msg["content-length"]
        if "content-length" in response.msg:
            del response.msg["content-length"]

        self.send_response(response.status, response.reason)
        for header_key, header_value in response.msg.items():
            self.send_header(header_key, header_value)
        body = response.read()

        if method == "POST":
            if response.status == httplib.OK:
                # Process the payload
                self._process_response(body, response.getheader('content-encoding'), duration)
            if response.status == httplib.BAD_REQUEST:
                body = self._process_bad_request(body, response.getheader('content-encoding'))

        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)


    do_HEAD = do_GET
    do_OPTIONS = do_GET

    @staticmethod
    def filter_headers(headers):
        # http://tools.ietf.org/html/rfc2616#section-13.5.1
        hop_by_hop = (
            'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
            'transfer-encoding', 'upgrade'
        )
        for k in hop_by_hop:
            if k in headers:
                del headers[k]

    @staticmethod
    def encode_content_body(text, encoding):
        if not encoding:
            return text
        if encoding == 'identity':
            return text
        if encoding in ('gzip', 'x-gzip'):
            io = StringIO()
            with gzip.GzipFile(fileobj=io, mode='wb') as f:
                f.write(text)
            return io.getvalue()
        if encoding == 'deflate':
            return zlib.compress(text)
        raise Exception("Unknown Content-Encoding: %s" % encoding)

    @staticmethod
    def decode_content_body(data, encoding):
        if not encoding:
            return data
        if encoding == 'identity':
            return data
        if encoding in ('gzip', 'x-gzip'):
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                return f.read()
        if encoding == 'deflate':
            return zlib.decompress(data)

        raise Exception("Unknown Content-Encoding: %s" % encoding)
