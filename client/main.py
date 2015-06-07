#!/usr/bin/python3

import socketserver
import http.server
import urllib3.exceptions

from config import PORT
import connect
import post

class LiquidHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def version_string(self):
        return 'LiquidCrystal/0.1'
    
    def do_CONNECT(self):
        socket_toremote = connect.connect(self.path)
        if socket_toremote:
            self.send_response_only(200)
            self.send_header('Proxy-agent',self.version_string())
            self.end_headers()
            
            byte_count = connect.content( self.connection, socket_toremote )
            
            self.log_request(200,byte_count)
        else:
            self.send_response(502)
            self.end_headers()
            
    def do_POST(self):
        try:
            response = post.connect(self)
        except (TimeoutError,urllib3.exceptions.TimeoutError):
            self.send_response(504)
            self.end_headers()
            self.close_connection = 1
        except (ConnectionError,urllib3.exceptions.HTTPError):
            self.send_response(502)
            self.end_headers()
            self.close_connection = 1
        if not response:
            self.send_response(502)
            self.end_headers()
            self.close_connection = 1
        
        self.send_response_only(response.status)
        for header in response.getheaders():
            if header.lower() != 'connection':
                self.send_header(header, response.getheader(header))
        self.send_header('Connection','keep-alive')
        self.end_headers()
        
        byte_count = post.content(self.wfile, response)
        self.log_request(response.status,byte_count)
        
    
    do_OPTIONS = do_GET = do_HEAD = do_DELETE = do_PUT = do_POST


if __name__ == "__main__":
    daemon = socketserver.ThreadingTCPServer(('127.0.0.1',8002),LiquidHandler)
    try:
        print('\nYour server is ready at :%s'%PORT)
        daemon.serve_forever()
    except KeyboardInterrupt:
        print('\nExiting...')
        daemon.shutdown()
        exit()