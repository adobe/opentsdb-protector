#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

from httplib import HTTPSConnection, HTTPConnection, IncompleteRead
import urlparse
import threading
import socket
import logging


class HTTPRequest(object):
    """
    A simple, thread-safe wrapper around HTTP(S)Connection
    """

    def __init__(self):
        self.tls = threading.local()
        self.tls.conns = {}

    def request(self, url, timeout, body=None, headers=None, max_retries=1, method="GET"):
        if headers is None:
            headers = dict()

        parsed = urlparse.urlsplit(url)
        origin = (parsed.scheme, parsed.netloc)

        uri = parsed.path
        if method == "GET":
            uri = parsed.path + "?" + parsed.query

        for i in range(max_retries):
            try:
                conn = self.create_conn(parsed, origin, timeout)
                conn.request(method, uri, body=body, headers=headers)
                return conn.getresponse()
            except socket.timeout, e:
                logging.warning("HTTPRequest socket timeout: %s", str(e))
                raise e
            except socket.error, e:
                logging.warning("HTTPRequest socket error: %s", str(e))
                raise e
            except IncompleteRead as e:
                return e.partial
            except Exception as e:
                if origin in self.tls.conns:
                    del self.tls.conns[origin]
                if (i + 1) >= max_retries:
                    raise e

    def create_conn(self, parsed, origin, timeout):
        if origin not in self.tls.conns:
            if parsed.scheme == 'https':
                self.tls.conns[origin] = HTTPSConnection(parsed.netloc, timeout=timeout)
            else:
                self.tls.conns[origin] = HTTPConnection(parsed.netloc, timeout=timeout)
        return self.tls.conns[origin]
