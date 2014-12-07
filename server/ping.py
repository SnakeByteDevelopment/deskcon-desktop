#!/usr/bin/env python2

import os
import sys
import socket
import configmanager
import json
from tls import TLSConnection
from OpenSSL import SSL, crypto

def send_ping(ip, port):
    HOST, PORT = ip, int(port)
    uuid = configmanager.uuid
    hostname = socket.gethostname()

    jsonobj = {'uuid': uuid, 'name': hostname,
               'type': "ping", 'data': ""}

    try:
        with TLSConnection(ip, port) as conn:
            conn.message(jsonobj)
    except Exception as e:
        print(e)



def main(args):
    ip = args[1]
    port = args[2]
    send_ping(ip, port)


if __name__ == '__main__':
    if(len(sys.argv) < 3):
        print "not enough arguments given"
    else:
        main(sys.argv)


