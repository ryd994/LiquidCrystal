import socket
import select

from config import TIMEOUT,BLOCK_SIZE

def connect(remote_host, remote_port=None):
    socket_toremote = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    if not remote_port:
        try:
            remote_host,remote_port = remote_host.split(':',1)
            remote_port = int(remote_port)
        except ValueError:
            remote_port = 80
    try:
        socket_toremote.connect((remote_host,remote_port))
        socket_toremote.setblocking(False)
        return socket_toremote
    except socket.error:
        return None

def content(socket_toclient,socket_toremote):
    rf = [socket_toclient,socket_toremote]
    wf = []
    byte_count = 0
    data = True
    dst = { socket_toremote: socket_toclient,
            socket_toclient: socket_toremote }
    while data:
        (rlst,_,errlst) = select.select(rf,wf,rf,TIMEOUT)
        if errlst:
            break
        if rlst:
            for src in rlst:
                try:
                    data = src.recv(BLOCK_SIZE)
                    dst[src].sendall(data)
                except ConnectionResetError:
                    return byte_count
                byte_count += len(data)
    return byte_count

