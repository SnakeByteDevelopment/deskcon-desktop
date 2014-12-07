#!/usr/bin/env python2

import sys
import socket
import argparse
import configmanager
from tls import TLSConnection

parser = argparse.ArgumentParser()
parser.add_argument('ip', help='ip/hostname of the phone to ping')
parser.add_argument('port', type=int, help='port of the service')

def send_ping(ip, port):
    uuid = configmanager.uuid
    hostname = socket.gethostname()

    jsonobj = {'uuid': uuid, 'name': hostname,
               'type': "ping", 'data': ""}

    try:
        with TLSConnection(ip, port) as conn:
            conn.message(jsonobj)
    except Exception as e:
        print(e)


def main(args=None):
    options = parser.parse_args(args)
    send_ping(options.ip, options.port)


if __name__ == '__main__':
    main()


