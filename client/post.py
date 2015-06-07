import urllib3

from config import TIMEOUT

HTTP_POOL = urllib3.PoolManager(num_pools=10,maxsize=10)

def connect(self):
    request_headers = dict(self.headers.items())
    request_headers['Connection'] = 'keep-alive'
    request_body = self.rfile.read( int(request_headers.get('Content-Length',0)) ) or None
    
    response = HTTP_POOL.urlopen (
        method  = self.command,
        url     = self.path,
        body    = request_body,
        headers = request_headers,
        timeout = TIMEOUT,
        retries = False,
        release_conn = False,
        preload_content = False,
        decode_content  = False,
        )
    return response

def content(wfile, response):
    if response.closed:
        wfile.write(response.data)
    else:
        for chunk in response.stream(2**20):
            if response.chunked:
                wfile.write( ('%x\r\n'%len(chunk)).encode('iso-8859-1') + chunk + b'\r\n' )
            else:
                wfile.write(chunk)
    return response.tell()
    
    
    
