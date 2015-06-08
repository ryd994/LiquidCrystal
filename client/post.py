import urllib3
import re
from copy import copy
from urllib.parse import urlsplit,urlunsplit
from datetime import datetime,timezone

from config import TIMEOUT,BLOCK_SIZE,API_SERVER,CACHE_SERVER


RETRIES         = 3
API_PROTOCOL    = 'http'
API_PATTERN     = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(7|39|71|103|135|167|215|247))|203\.104\.(105\.167|209\.(7|71|23|39|55)|248\.135)|222\.158\.206\.145)/kcsapi/.*'
CACHE_PATTERN   = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(7|39|71|103|135|167|215|247))|203\.104\.(105\.167|209\.(7|71|23|39|55)|248\.135)|222\.158\.206\.145)/kcs/.*'


HTTP_POOL = urllib3.PoolManager(num_pools=10,maxsize=10)

def connect(self):
    request_headers = copy(self.headers)          #shallow copy
    del(request_headers['Connection'])
    request_headers['Connection'] = 'keep-alive'

    
    if re.match(API_PATTERN, self.path):
        url = urlsplit(self.path)
        url = urlunsplit((API_PROTOCOL, API_SERVER,
                          '/{0:.3f}/{1}{2}'.format(datetime.now(timezone.utc).timestamp(), url[1], url[2]),
                          url[3], url[4]))
        request_headers.replace_header('Host',API_SERVER)
        
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = url,
            body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
            headers = dict(request_headers.items()),
            timeout = TIMEOUT,
            retries = RETRIES,
            release_conn    = True,
            preload_content = True,
            decode_content  = False,
            )
        response.headers.pop('Transfer-Encoding',None)
        response.headers['Content-Length'] = len(response.data)
        response.close()
    
    elif re.match(CACHE_PATTERN, self.path):
        url = urlsplit(self.path)
        url = urlunsplit((url[0], CACHE_SERVER, url[2], url[3], url[4]))
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = url,
            body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
            headers = dict(request_headers.items()),
            timeout = TIMEOUT,
            retries = RETRIES,
            release_conn    = True,
            preload_content = True,
            decode_content  = False,
            )
        
        response.headers.pop('Transfer-Encoding',None)
        response.headers['Content-Length'] = len(response.data)
        response.close()
    
    else:
        try:
            # set nonblocking mode for client connection will prevent httplib block for empty body
            # assuming this is a local server, so that local network is not the bottleneck
            request_timeout = self.connection.gettimeout()
            self.connection.setblocking(False)
            
            response = HTTP_POOL.urlopen (
                method  = self.command,
                url     = self.path,
                body    = self.rfile,
                headers = dict(request_headers.items()),
                timeout = TIMEOUT,
                retries = False,
                release_conn    = False,
                preload_content = False,
                decode_content  = False,
                )
        finally:
            # remember to reset timeout of client connection. refer to beginning of this try block
            self.connection.settimeout(request_timeout)
    
    response.headers['Connection'] = 'keep-alive'
    return response

def content(wfile, response):
    if response.closed:
        wfile.write(response.data)
    else:
        for chunk in response.stream(BLOCK_SIZE):
            try:
                if response.chunked:
                    wfile.write( ('%x\r\n'%len(chunk)).encode('iso-8859-1') + chunk + b'\r\n' )
                else:
                    wfile.write(chunk)
            except BrokenPipeError:
                response.close()
                break
        if response.chunked:
            wfile.write(b'0\r\n\r\n')
    return response.tell()