import urllib3
import re
import os
import stat
import email.utils
from copy import copy
from urlparse import urlsplit,urlunsplit,parse_qs
from datetime import datetime
from time import time

import config


RETRIES         = 5
API_PROTOCOL    = 'http'
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
    
def is_api(path):
    API_PATTERN     = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(39|71|7|103|135|167|215|247))|203\.104\.(105\.167|209\.(71|23|39|55|102)|248\.135)|222\.158\.206\.145)/kcsapi/.*'
    if re.match(API_PATTERN, path):
        return True
    return False

def is_cache(path):
    CACHE_PATTERN   = '^http://(125\.6\.18(4\.(15|16)|7\.(205|229|253)|8\.25|9\.(39|71|7|103|135|167|215|247))|203\.104\.(105\.167|209\.(71|23|39|55|102)|248\.135)|222\.158\.206\.145)/kcs/.*'
    if re.match(CACHE_PATTERN, path):
        return True
    return False

def is_proxy(path):
    if re.match('^http://.*\.dmm.com/.*',path):
        return True
    if path.startswith(('http://203.104.209.7/kcscontents/','http://203.104.209.7/gadget/')):
        return True
    return False

def connect(self):
    request_headers = copy(self.headers)          #shallow copy
    del(request_headers['Connection'])
    request_headers['Connection'] = 'keep-alive'

    
    if is_api(self.path):
        url = urlsplit(self.path)
        url = urlunsplit((API_PROTOCOL, config.API_SERVER,'/'+url[1]+url[2], url[3], url[4]))
        request_headers['Host'] = config.API_SERVER
        request_headers['X-Crystal-Timestamp'] = '{0:.3f}'.format(time())

        
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = url,
            body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
            headers = dict(request_headers.items()),
            timeout = config.TIMEOUT,
            retries = RETRIES,
            release_conn    = True,
            preload_content = True,
            decode_content  = False,
            )
        response.headers.pop('Transfer-Encoding',None)
        response.headers['Content-Length'] = len(response.data)
        response.close()
    
    elif is_cache(self.path):
        url = urlsplit(self.path)
        query = {k.lower():v for k,v in parse_qs(url[3]).items()}
        
        cache_prefix = 'cache'
        cache_name = url[2].partition('.')     #cache_name[2] is extension
        hacked_path= cache_prefix + '/' + '.'.join((cache_name[0],'hack',cache_name[2]))
        
        if os.path.isfile(hacked_path): cache_path = hacked_path
        elif 'version' in query: cache_path = cache_prefix + '/' + '.'.join((cache_name[0],query['version'][0],cache_name[2]))
        else: cache_path = cache_prefix + '/' + '.'.join((cache_name[0],cache_name[2]))
        
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
            url = urlunsplit(('http', config.CACHE_SERVER, '/'+url[1]+url[2], url[3], url[4]))
            #request_headers['Host'] = config.CACHE_SERVER
            response = HTTP_POOL.urlopen (
                method  = self.command,
                url     = url,
                body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
                headers = dict(request_headers.items()),
                timeout = config.TIMEOUT,
                retries = RETRIES,
                release_conn    = True,
                preload_content = True,
                decode_content  = False,
                )
            try:
                os.makedirs(os.path.dirname(cache_path))
            except OSError:
                pass
            
            with open(cache_path,'wb') as cache_file:
                cache_file.write(response.data)
            
            mtime = response.headers.get('Last-Modified',None) or response.headers.get('Date',None)
            if mtime:
                mtime = email.utils.mktime_tz(email.utils.parsedate_tz(mtime))
                os.utime(cache_path,(time(),mtime))
            
            response.headers.pop('Transfer-Encoding',None)
            response.headers['Content-Length'] = len(response.data)
            response.close()    # close response so that content() can know data is preloaded

    elif is_proxy(self.path):
        url = urlsplit(self.path)
        url = urlunsplit(('http', 'super.crystalacg.com', url[2], url[3], url[4]))
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = url,
            body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
            headers = dict(request_headers.items()),
            timeout = config.TIMEOUT,
            retries = False,
            release_conn    = False,
            preload_content = False,
            decode_content  = False,
            )

    else:
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = self.path,
            body    = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None,
            headers = dict(request_headers.items()),
            timeout = config.TIMEOUT,
            retries = False,
            release_conn    = False,
            preload_content = False,
            decode_content  = False,
            )
    
    response.headers['Connection'] = 'close'
    return response

def content(wfile, response):
    if response.closed:
        wfile.write(response.data)
    else:
        for chunk in response.stream(config.BLOCK_SIZE):
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
    wfile.flush()
    return response.tell()