#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import unittest
import json
from mock import MagicMock, patch
from result import Ok
import time
import threading
import urllib.request, urllib.error, urllib.parse

from protector.proxy import request_handler
from protector.proxy import server


class MockHTTPResponse(object):
    HTTP_10 = 10
    HTTP_11 = 11

    def __init__(self, status, reason, msg=None, body="", version=HTTP_11, delay=0):
        if msg is None:
            msg = {}
        self.status = status
        self.reason = reason
        self.msg = msg
        self.body = body
        self.version = version
        self.delay = delay

    def read(self):
        if self.delay:
            time.sleep(self.delay)
        return self.body

    def getheader(self, header):
        return 'identity'


class TestRequests(unittest.TestCase):
    def setUp(self):
        self.host = "127.0.0.1"
        self.port = 8888
        self.backend_host = "127.0.0.1"
        self.backend_port = 4242

    def start_server(self):
        request_handler.ProxyRequestHandler.protocol_version = "HTTP/1.1"
        request_handler.ProxyRequestHandler.protector = self.create_protector()
        request_handler.ProxyRequestHandler.backend_address = (self.backend_host, self.backend_port)

        self.test_server = server.ThreadingHTTPServer(
            (self.host, self.port), request_handler.ProxyRequestHandler
        )
        self.server_thread = threading.Thread(target=self.test_server.serve_forever)
        self.server_thread.start()
        time.sleep(0.25)

    def tearDown(self):
        self.test_server.shutdown()
        self.test_server.server_close()

    def create_protector(self, return_value=Ok(True)):
        protector = MagicMock()
        protector.check.return_value = return_value
        return protector

    @patch('protector.proxy.request_handler.HTTPRequest')
    def test_proxy_redirect(self, mock_http_request):
        mock_http_request_class = mock_http_request.return_value
        mock_http_request_class.request.return_value = MockHTTPResponse(200, "OK", {}, "{}")

        self.start_server()

        url_string = "http://{}:{}/?q=list%20series%20%2Ffoo%5C.bar%5C.baz%2F"
        frontend_url = url_string.format(self.host, self.port)
        backend_url = url_string.format(self.backend_host, self.backend_port)

        # Do proxy request
        response = urllib.request.urlopen(frontend_url)

        # Check if we did a single request to the backend
        self.assertTrue(mock_http_request_class.request.called)
        self.assertEqual(mock_http_request_class.request.call_count, 1)

        # Check that we called the backend host
        parameters, _ = mock_http_request_class.request.call_args_list[0]
        self.assertEqual(parameters[0], backend_url)

        # Check valid response code
        self.assertEqual(response.code, 200)
        self.assertEqual(response.msg, "OK")
        self.assertEqual(response.read().decode(), "{}")

    @patch('protector.proxy.request_handler.HTTPRequest')
    def test_proxy_error_response(self, mock_http_request):
        mock_http_request_class = mock_http_request.return_value
        mock_http_request_class.request.return_value = MockHTTPResponse(500, "Internal Server Error")

        self.start_server()

        url_string = "http://{}:{}/?q=list%20series%20%2Ffoo%5C.bar%5C.baz%2F"
        frontend_url = url_string.format(self.host, self.port)
        backend_url = url_string.format(self.backend_host, self.backend_port)

        # An internal server error will raise an exception
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(frontend_url)

        # Check if we did a single request to the backend
        self.assertTrue(mock_http_request_class.request.called)
        self.assertEqual(mock_http_request_class.request.call_count, 1)
        parameters, _ = mock_http_request_class.request.call_args_list[0]
        self.assertEqual(parameters[0], backend_url)

    @patch('protector.proxy.request_handler.HTTPRequest')
    def test_proxy_invalid_query(self, mock_http_request):
        mock_http_request_class = mock_http_request.return_value
        mock_http_request_class.request.return_value = MockHTTPResponse(400, "Bad request")

        self.start_server()

        url_string = "http://{}:{}/?q=list%20series%20%2Ffoo%5C.bar%5C.baz%2F"
        frontend_url = url_string.format(self.host, self.port)
        backend_url = url_string.format(self.backend_host, self.backend_port)

        # An internal server error will raise an exception
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(frontend_url)

        # Check if we did a single request to the backend
        self.assertTrue(mock_http_request_class.request.called)
        self.assertEqual(mock_http_request_class.request.call_count, 1)
        parameters, _ = mock_http_request_class.request.call_args_list[0]
        self.assertEqual(parameters[0], backend_url)

    @patch('protector.proxy.request_handler.HTTPRequest')
    def test_invalid_response(self, mock_http_request):
        mock_http_request_class = mock_http_request.return_value
        mock_http_request_class.request.return_value = "Invalid response"

        self.start_server()

        url_string = "http://{}:{}/?q=list%20series%20%2Ffoo%5C.bar%5C.baz%2F"
        frontend_url = url_string.format(self.host, self.port)
        backend_url = url_string.format(self.backend_host, self.backend_port)

        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(frontend_url)

        # Check if we did a single request to the backend
        self.assertTrue(mock_http_request_class.request.called)
        self.assertEqual(mock_http_request_class.request.call_count, 1)

        parameters, _ = mock_http_request_class.request.call_args_list[0]
        self.assertEqual(parameters[0], backend_url)

    @patch('protector.proxy.request_handler.HTTPRequest')
    def test_post(self, mock_http_request):
        mock_http_request_class = mock_http_request.return_value
        mock_http_request_class.request.return_value = MockHTTPResponse(200, "OK", {}, "{}")

        self.start_server()

        url_string = "http://{}:{}/api/query"

        q = {
                "start": "3m-ago",
                "queries": [
                    {
                        "metric": "mymetric",
                        "aggregator": "max",
                        "downsample": "20s-max",
                        "filters": []
                    }
                ]
            }

        rq = q.copy()
        rq["showSummary"] = True
        rq["showQuery"] = True

        data = json.dumps(q).encode()
        dataq = json.dumps(rq).encode()

        frontend_url = url_string.format(self.host, self.port)
        backend_url = url_string.format(self.backend_host, self.backend_port)

        # Do proxy request
        req = urllib.request.Request(frontend_url, data, {'Content-Type': 'application/json'})
        response = urllib.request.urlopen(req)

        # Check if we did a single request to the backend
        self.assertTrue(mock_http_request_class.request.called)
        self.assertEqual(mock_http_request_class.request.call_count, 1)

        # Check that we called the backend host
        parameters, _ = mock_http_request_class.request.call_args_list[0]
        self.assertEqual(parameters[0], backend_url)

        args, kwargs = mock_http_request_class.request.call_args
        self.assertEqual("POST", kwargs.get('method'))

        self.assertEqual(dataq.decode(), kwargs.get('body'))

        # Check valid response code
        self.assertEqual(response.code, 200)
        self.assertEqual(response.msg, "OK")
        self.assertEqual(response.read().decode(), "[]")
