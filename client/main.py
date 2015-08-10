#!/usr/bin/python3

import socket
import SocketServer
import BaseHTTPServer
import urllib3.exceptions

import config
import connect
import post


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
    
    '''
    do_*() is called when request mathod matches
    
    To simplify main.py, actual implement is done in (method).py . For short, main.py 
    controls response code, headers and logging, while (method).py prepares response and
    sends content.
    
    All operation performed before any data sent to client is handled by (method).connect() .
    Exceptions are allowed in (method).connect(), they will be converted to appropriate 
    HTTP status code and response. If no error occured, (method).connect() shoudl return 
    a (response) to be passed to (method).content()
    
    All operation after status code and headers sent are handled by (method).content() .
    (method).content() should not throw exceptions, any exception will abort processing 
    immediately and connection will be closed. (method).content() should return byte count
    and/or other info for logging.
    
    '''
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
            return
        
        self.send_response_only(response.status)
        for k,v in response.headers.items():
            self.send_header(k, v)
        self.end_headers()
        
        byte_count = post.content(self.wfile, response)
        
        self.log_request(response.status, byte_count)
        
    do_OPTIONS = do_GET = do_HEAD = do_DELETE = do_PUT = do_POST


if __name__ == "__main__":
    import sys
    from os.path import splitext,basename
    import os
    import signal
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--port','-p',type=int,dest='PORT',help='listening port number')
    parser.add_argument('--timeout','-t',type=int,dest='TIMEOUT',help='timout for connecting')
    parser.add_argument('--api-server','-as',dest='API_SERVER',help='server for game api operations')
    parser.add_argument('--cache-server','-cs',dest='CACHE_SERVER',help='server for game resources')

    parser.parse_args(namespace=config)
    
    daemon = SocketServer.ThreadingTCPServer(('127.0.0.1',config.PORT),LiquidHandler,bind_and_activate=False)
    daemon.daemon_threads = True

    # OS-specific settings
    if os.name == 'posix':
        # TIME_WAIT bind fail workaround in linux
        daemon.allow_reuse_address = True
    elif os.name == 'nt':
        # Windows has different behavior on SO_REUSEADDR, don't use this options on Windows
        daemon.allow_reuse_address = False
    # Not sure with other OS, open a ticket if you can provide assistance
    
    try:
        daemon.server_bind()
        daemon.server_activate()    
    except socket.error:
        print('Cannot bind to specified port')
        exit(65)
    
    print('Your server is ready at :%s'%config.PORT)
    sys.stdout.flush()
    
    try:
        daemon.serve_forever()
    except KeyboardInterrupt:
        print('Exiting...')
        exit(0)