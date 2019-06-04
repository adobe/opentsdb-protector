import json
import httplib
import gzip
import zlib
import logging
import traceback
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

from protector.proxy.http_request import HTTPRequest
from protector.query.query import OpenTSDBQuery, OpenTSDBResponse
import pprint


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

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_error(self, log_format, *args):

        # Suppress "Request timed out: timeout('timed out',)"
        # if isinstance(args[0], socket.timeout):
        #    return
        self.log_message(log_format, *args)

    def do_GET(self):

        self.headers['Host'] = self.backend_netloc
        self.filter_headers(self.headers)
        self._handle_request(self.scheme, self.backend_netloc, self.path, self.headers)

    def do_POST(self):

        length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(length)

        self.headers['Host'] = self.backend_netloc
        self.filter_headers(self.headers)

        # Only process query requests, everything else should pass through
        if self.path == "/api/query":

            self.tsdb_query = OpenTSDBQuery(post_data)

            # Check the payload against the Protector rule set
            result = self.protector.check(self.tsdb_query)
            if not result.is_ok():
                logging.warning("OpenTSDBQuery blocked: %s. Reason: %s", self.tsdb_query.get_id(), result.value)
                self.send_error(httplib.BAD_REQUEST, result.value)
                return

            
            post_data = self.tsdb_query.toJson()

            self.headers['Content-Length'] = str(len(post_data))

        self._handle_request(self.scheme, self.backend_netloc, self.path, self.headers, body=post_data, method="POST")

    def send_error(self, code, message=None):
        """
        Send and log plain text error reply.
        :param code:
        :param message:
        """
        message = message.strip()
        self.log_error("code %d, message: %s", code, message)
        self.send_response(code)
        #self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Type", "application/json")
        self.send_header('Connection', 'close')
        self.end_headers()
        if message:
            #self.wfile.write(message.encode())
            # Grafana style
            j = {'message': message, 'error': message}
            self.wfile.write(json.dumps(j))

    def _handle_request(self, scheme, netloc, path, headers, body=None, method="GET"):
        """
        Run the actual request
        """
        backend_url = "{}://{}{}".format(scheme, netloc, path)

        try:
            response = self.http_request.request(backend_url, method=method, body=body, headers=dict(headers))
            if response:
                self._return_response(response, method)
        except Exception as e:
            logging.error("{}".format(traceback.format_exc()))
            err = "Invalid response from backend: '{}' Server might be busy".format(e)
            logging.debug(err)
            self.send_error(httplib.SERVICE_UNAVAILABLE, err)

    def _process_response(self, payload, encoding):
        """
        :type payload: JSON
        :type encoding: Content Encoding
        """
        try:
            resp = OpenTSDBResponse(self.decode_content_body(payload, encoding))
            self.protector.save_stats(self.tsdb_query, resp)
        except Exception as e:
            err = "Skip: {}".format(e)
            logging.debug(err)

    def _process_bad_request(self, payload, encoding):
        """
        :type payload: JSON
        :type encoding: Content Encoding
        """
        # Re-package the error json for Grafana
        j = json.loads(self.decode_content_body(payload, encoding))
        err = j.get('error', None)
        b = {}

        if err:
            b = {'message': err.get('message', '?'), 'error': err.get('details', '?')}

        return self.encode_content_body(json.dumps(b), encoding)

    def _return_response(self, response, method):
        """
        :type response: HTTPResponse
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
                self._process_response(body, response.getheader('content-encoding'))
            if response.status == httplib.BAD_REQUEST:
                body = self._process_bad_request(body, response.getheader('content-encoding'))

        self.send_header('Content-Length', str(len(body)))
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
        if encoding == 'identity':
            return data
        if encoding in ('gzip', 'x-gzip'):
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                return f.read()
        if encoding == 'deflate':
            return zlib.decompress(data)

        raise Exception("Unknown Content-Encoding: %s" % encoding)
