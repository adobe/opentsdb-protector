#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import sys
import ssl
import socket
from socketserver import ThreadingMixIn
from http.server import HTTPServer


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Server that handles requests in multiple threads
    """
    daemon_threads = True

    def server_bind(self):
        HTTPServer.server_bind(self)

    def handle_error(self, request, client_address):
        """
        Overwrite error handling to suppress socket/ssl related errors
        :param client_address: Address of client
        :param request: Request causing an error
        """
        cls, e = sys.exc_info()[:2]
        if cls is socket.error or cls is ssl.SSLError:
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)
    