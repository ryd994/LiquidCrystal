#!/usr/bin/python3

import SocketServer
import BaseHTTPServer
import urllib3.exceptions

from config import PORT
import connect
import post
import socket
import sys

class LiquidHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def version_string(self):
        return 'LiquidCrystal/0.1'
    
    def send_response_only(self, code, message=None):
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''
        if self.request_version != 'HTTP/0.9':
            self.wfile.write("%s %d %s\r\n" %
                            (self.protocol_version, code, message))
    
    def do_CONNECT(self):
        try:
            socket_toremote = connect.connect(self.path)
        except socket.error:
            self.send_response(502)
            self.end_headers()
            self.close_connection = 1
            return
        
        self.send_response_only(200)
        self.send_header('Proxy-Agent',self.version_string())
        self.end_headers()
        
        byte_count = connect.content( self.connection, socket_toremote )
        
        self.log_request(200,byte_count)
           
            
    def do_POST(self):
        try:
            response = post.connect(self)
        except (urllib3.exceptions.TimeoutError):
            self.send_response(504)
            self.end_headers()
            self.close_connection = 1
            return
        except (urllib3.exceptions.HTTPError):
            self.send_response(502)
            self.end_headers()
            self.close_connection = 1
            raise
        
        self.send_response_only(response.status)
        for k,v in response.headers.items():
            self.send_header(k, v)
        self.end_headers()
        
        byte_count = post.content(self.wfile, response)
        
        self.log_request(response.status, byte_count)
    
    
    do_OPTIONS = do_GET = do_HEAD = do_DELETE = do_PUT = do_POST


if __name__ == "__main__":
    daemon = SocketServer.ThreadingTCPServer(('127.0.0.1',PORT),LiquidHandler,bind_and_activate=False)
    daemon.allow_reuse_address = True
    try:
        daemon.server_bind()
    except socket.error:
        print('Can not bind to specified port')
        sys.exit(0)
    daemon.server_activate()
    
    try:
        print('Your server is ready at :%s'%PORT)
        sys.stdout.flush()
        daemon.serve_forever()
    except KeyboardInterrupt:
        print('Exiting...')
        daemon.shutdown()
        sys.exit(0)