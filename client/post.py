import urllib3
import re
import os
import stat
import email.utils
from copy import copy
from urllib.parse import urlsplit,urlunsplit,parse_qs
from datetime import datetime,timezone
from time import time


from config import TIMEOUT,BLOCK_SIZE,API_SERVER,CACHE_SERVER


RETRIES         = 3
API_PROTOCOL    = 'http'
API_PATTERN     = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(7|39|71|103|135|167|215|247))|203\.104\.(105\.167|209\.(7|71|23|39|55)|248\.135)|222\.158\.206\.145)/kcsapi/.*'
CACHE_PATTERN   = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(7|39|71|103|135|167|215|247))|203\.104\.(105\.167|209\.(7|71|23|39|55)|248\.135)|222\.158\.206\.145)/kcs/.*'
MIME_DICT       = {
    'jpg':'image/jpeg',
    'mp3':'audio/mpeg',
    'png':'image/png',
    'swf':'application/x-shockwave-flash',
    }

HTTP_POOL = urllib3.PoolManager(num_pools=10,maxsize=10)

class DummyResponse:
    closed = True
    def __init__(self):
        self.data = b''
        self.status = 200
        self.headers = {}
    
    def tell(self):
        return len(self.data)
    

def connect(self):
    request_headers = copy(self.headers)          #shallow copy
    del(request_headers['Connection'])
    request_headers['Connection'] = 'keep-alive'

    
    if re.match(API_PATTERN, self.path):
        url = urlsplit(self.path)
        url = urlunsplit((API_PROTOCOL, API_SERVER,
                          '/{0:.3f}/{1}{2}'.format(time(), url[1], url[2]),
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
        query = parse_qs(url[3])
        
        cache_name = url[2].rpartition('.')     #cache_name[2] is extension
        hacked_path= '.'.join(('',cache_name[0],'hack',cache_name[2]))
        
        if os.path.isfile(hacked_path): cache_path = hacked_path
        elif 'version' in query: cache_path = '.'.join(('',cache_name[0],query['version'][0],cache_name[2]))
        else: cache_path = '.'.join(('',cache_name[0],cache_name[2]))
        
        if os.path.isfile(cache_path):
            with open(cache_path,'rb') as cache_file:
                fileinfo = os.fstat(cache_file.fileno())
                response = DummyResponse()
                response.headers['Content-Length'] = str(fileinfo.st_size)
                response.headers['Content-Type'] = MIME_DICT.get(cache_name[2],'application/octet-stream')
                response.headers['Date'] = email.utils.formatdate()
                response.headers['Last-Modified'] = email.utils.formatdate(fileinfo.st_mtime)
                response.data = cache_file.read()
        else:
            url = urlunsplit(('http', CACHE_SERVER, url[2], url[3], url[4]))
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
            
            os.makedirs(os.path.dirname(cache_path),exist_ok=True)
            
            with open(cache_path,'wb') as cache_file:
                cache_file.write(response.data)
            
            mtime = response.headers.get('Last-Modified',None) or response.headers.get('Date',None)
            if mtime:
                mtime = email.utils.mktime_tz(email.utils.parsedate_tz(mtime))
                os.utime(cache_path,(time(),mtime))
            
            response.headers.pop('Transfer-Encoding',None)
            response.headers['Content-Length'] = len(response.data)
            response.close()    # close response so that content() can know data is preloaded
    
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