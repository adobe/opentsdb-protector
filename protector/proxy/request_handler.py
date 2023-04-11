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
import http.client
import json
import logging
import socket
import time
import zlib
import re
from http.server import BaseHTTPRequestHandler
from io import BytesIO
import traceback

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import datetime as dt

from protector.proxy.http_request import HTTPRequest
from protector.query.query import OpenTSDBQuery, OpenTSDBResponse


class ProxyRequestHandler(BaseHTTPRequestHandler):

    protector = None
    backend_address = None
    timeout = None
    
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

        try:
            BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        except ValueError:
            pass


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
        xff = '-'
        xgo = '-'
        ua = '-'
        headers = dict(self.headers)
        if 'X-Forwarded-For' in headers:
            xff = headers['X-Forwarded-For']
        if 'X-Grafana-Org-Id' in headers:
            xgo = headers['X-Grafana-Org-Id']
        if 'User-Agent' in headers:
            ua = headers['User-Agent']

        logging.info("%s - - [%s] %s [X-Forwarded-For: %s, X-Grafana-Org-Id: %s, User-Agent: %s]" %
                        (self.client_address[0], self.log_date_time_string(), format % args, xff, xgo, ua))

    def do_GET(self):

        top = re.match("^/top/(duration|dps)$", self.path)

        if self.path == "/metrics":

            data = generate_latest()

            self.send_response(http.client.OK)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)

        elif top:

            data = self.protector.get_top(top.group(1))

            self.send_response(http.client.OK)
            self.send_header("Content-Type", "application/json")
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

        # Deny put requests
        if self.path == "/api/put":
            logging.warning("OpenTSDBQuery blocked. Reason: %s", "/api/put not allowed")
            self.send_error(http.client.FORBIDDEN, "/api/put not allowed")
            return

        # Process query requests
        if self.path == "/api/query":

            self.tsdb_query = OpenTSDBQuery(post_data)
            self.headers['X-Protector'] = self.tsdb_query.get_id()

            # Increment metrics based on query start time
            start_time = dt.datetime.fromtimestamp(self.tsdb_query.get_start_timestamp())
            now_time = dt.datetime.fromtimestamp(int(round(time.time())))
            delta_time = now_time - start_time
            
            self.protector.TSDB_REQUEST_INTERVAL.labels("days").observe(int(delta_time.days))

            # Check the payload against the Protector rule set
            result = self.protector.check(self.tsdb_query)
            if not result.is_ok():
                self.protector.REQUESTS_BLOCKED.labels(self.protector.safe_mode, result.value["rule"]).inc()

                if not self.protector.safe_mode:
                    logging.warning("OpenTSDBQuery blocked: %s. Reason: %s", self.tsdb_query.get_id(), result.value["msg"])
                    self.send_error(http.client.FORBIDDEN, result.value["msg"])
                    return

            post_data = self.tsdb_query.to_json()

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
            self.wfile.write(json.dumps(j).encode())

    def _handle_request(self, scheme, netloc, path, headers, body=None, method="GET"):
        """
        Run the actual request
        """
        backend_url = "{}://{}{}".format(scheme, netloc, path)
        startTime = time.time()

        try:
            headers=dict(headers)
            if body is not None:
                headers['Content-Length'] = str(len(body))
            response = self.http_request.request(backend_url, self.timeout, method=method, body=body, headers=headers)

            respTime = time.time()
            duration = respTime - startTime

            self.protector.TSDB_REQUEST_LATENCY.labels(response.status, path, method).observe(duration)
            self._return_response(response, method, duration)

            return response.status

        except socket.timeout as e:

            respTime = time.time()
            duration = respTime - startTime

            if method == "POST":
                self.protector.save_stats(self.tsdb_query, None, duration, True)

            self.protector.TSDB_REQUEST_LATENCY.labels(http.client.GATEWAY_TIMEOUT, path, method).observe(duration)
            self.send_error(http.client.GATEWAY_TIMEOUT, "Query timed out. Configured timeout: {}s".format(self.timeout))

            return http.client.GATEWAY_TIMEOUT

        except Exception as e:

            respTime = time.time()
            duration = respTime - startTime

            err = "Invalid response from backend: '{}'".format(e)
            logging.debug(err)
            self.protector.TSDB_REQUEST_LATENCY.labels(http.client.BAD_GATEWAY, path, method).observe(duration)
            self.send_error(http.client.BAD_GATEWAY, err)

            return http.client.BAD_GATEWAY

    def _process_response(self, payload, encoding, duration):
        """
        :param payload: JSON
        :param encoding: Content Encoding
        """
        r = ""
        try:
            resp = OpenTSDBResponse(self.decode_content_body(payload, encoding))
            r = resp.to_json()
            self.protector.save_stats(self.tsdb_query, resp, duration)
        except Exception as e:
            err = "Skip: {}".format(e)
            logging.debug(err)
            logging.error("{}".format(traceback.format_exc()))

        return self.encode_content_body(r, encoding)

    def _process_bad_request(self, payload, encoding):
        """
        :param payload: JSON
        :param encoding: Content Encoding
        """
        # Re-package the error json for Grafana
        j = json.loads(self.decode_content_body(payload, encoding))
        err = j.get('error', None)
        msg = j.get('message', None)

        b = {}

        if err:
            b['error'] = err

        if msg:
            b['message'] = msg

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
            if response.status == http.client.OK:
                # Process the payload
                r = self._process_response(body, response.getheader('content-encoding'), duration)
                if r:
                    body = r
            if response.status == http.client.BAD_REQUEST:
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
            io = BytesIO()
            with gzip.GzipFile(fileobj=io, mode='wb') as f:
                f.write(text.encode('utf-8'))
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
            io = BytesIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                return f.read()
        if encoding == 'deflate':
            return zlib.decompress(data)

        raise Exception("Unknown Content-Encoding: %s" % encoding)
