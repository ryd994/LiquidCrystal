import urllib3

from config import TIMEOUT

HTTP_POOL = urllib3.PoolManager(num_pools=10,maxsize=10)

def connect(self):
    request_headers = dict(self.headers.items())
    request_headers['Connection'] = 'keep-alive'
    
    try:
        # set nonblocking mode for client connection will prevent httplib block for empty body
        # assuming this is a local server, so that local network is not the bottleneck
        request_timeout = self.connection.gettimeout()
        self.connection.setblocking(False)
        
        response = HTTP_POOL.urlopen (
            method  = self.command,
            url     = self.path,
            body    = self.rfile,
            headers = request_headers,
            timeout = TIMEOUT,
            retries = False,
            release_conn = False,
            preload_content = False,
            decode_content  = False,
            )
    finally:
        # remember to reset timeout of client connection. refer to beginning of this try block
        self.connection.settimeout(request_timeout)
    return response

def content(wfile, response):
    if response.closed:
        wfile.write(response.data)
    else:
        for chunk in response.stream(8192):
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