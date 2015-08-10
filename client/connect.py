import socket
from select import select

import config

def connect(remote_host, remote_port=None):
    socket_toremote = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    # TODO IPv6 support
    if not remote_port:
        try:
            remote_host,remote_port = remote_host.split(':',1)
            remote_port = int(remote_port)
        except ValueError:
            remote_port = 80
    if remote_host == 'www.dmm.com':
        remote_host = 'www.crystalacg.com'
    socket_toremote.connect((remote_host,remote_port))
    return socket_toremote

def content(socket_toclient,socket_toremote):
    socket_toclient.setblocking(False)
    socket_toremote.setblocking(False)
    rf = [socket_toclient,socket_toremote]
    byte_count = 0
    data = True
    dst = { socket_toremote: socket_toclient,
            socket_toclient: socket_toremote }
    while data:
        (rlst,_,errlst) = select(rf,[],rf,config.TIMEOUT)
        if errlst:
            break
        if rlst:
            for src in rlst:
                try:
                    data = src.recv(config.BLOCK_SIZE)
                    dst[src].setblocking(True)
                    dst[src].sendall(data)
                    dst[src].setblocking(False)
                except:
                    return byte_count
                byte_count += len(data)
    socket_toremote.close()
    socket_toclient.setblocking(True)
    return byte_count

