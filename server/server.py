import struct
import bson
import pymongo
from datetime import datetime,utcfromtimestamp,utcnow
from time import time
from urllib3.poolmanager import PoolManager

HTTPPool = PoolManager( num_pools=30, maxsize=20,timeout=5, retries=False, )
Collection = pymongo.MongoClient('mongodb:///var/run/mongodb/mongodb-27017.sock',
                                 tz_aware=True).kancache.kancache

def application(environ, start_response):
    client_ip = struct.unpack('i',environ['BINARY_REMOTE_ADDR'])[0] # unpacked as signed_int32,
                                                                    # so that we can save space in mongo
    _,client_time,host,path = environ['REQUEST_URI'].split('/',3)
    client_time = float(client_time)
    
    cache = Collection.find_one(
        {
            'url'       :'/'.join((host,path)),
            'client_ip' :client_ip,
            'client_time':client_time,
        },
        {
            '_id'       :False,
            'response'  :True,
        },
    )
    if cache is None:
        request_headers = { k[5:].replace('_','-'): v 
                            for k,v in environ.items() 
                            if k.startswith('HTTP_') }
        
        request_headers['HOST'] = host
        request_headers['CONNECTION'] = 'keep-alive'
        request_headers['ACCEPT-ENCODING'] = 'deflate, gzip'
        request_headers['X-FORWARDED-FOR'] = environ['REMOTE_ADDR']
        
        request_body = environ['wsgi.input'].read()
        
        server_result = HTTPPool.urlopen(
            method  = environ['REQUEST_METHOD'],
            url     = '/'.join( ('http:/',host,path) ),
            body    = request_body,
            headers = request_headers,
            retries = False, 
            preload_content =True,
            decode_content  =True, 
            )
        response_header = { k: v
                            for k,v in server_result.getheaders().items()
                            if k.upper() not in ('TRANSFER-ENCODING','CONTENT-ENCODING','CONTENT-LENGTH') }
        response_header['Content-Length'] = len(server_result.data)
        Collection.insert( {
            'url'       :'/'.join( (host,path) ),
            'client_ip' :client_ip,
            'client_time':client_time,
            'time'      :utcnow()
            'request'   :{
                'header'    :request_headers,
                'content'   :bson.binary.Binary(request_body),
                },
            'response'  :{
                'status'    :server_result.status,
                'header'    :response_header,
                'content'   :bson.binary.Binary(server_result.data),
                },
            } )
        response_header['X-CrystalACG-Cache'] = 'MISS'
        start_response( str(server_result.status), response_header.items() )
        return [ server_result.data ]
    else:
        response_header = [ (k.encode('iso-8859-1'),v.encode('iso-8859-1')) for k,v in cache['response']['header'].items() ]
        response_header.append( ('X-CrystalACG-Cache','HIT') )
        start_response( str(cache['response']['status']), response_header )
        return [ cache['response']['content'] ]

