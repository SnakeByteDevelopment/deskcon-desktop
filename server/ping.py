#!/usr/bin/env python2

import sys
import socket
import argparse
import configmanager
from tls import TLSConnection, parser

def send_ping(ip, port):
    try:
        with TLSConnection(ip, port) as conn:
            conn.command('ping')
    except Exception as e:
        print(e)


def main(args=None):
    options = parser.parse_args(args)
    send_ping(options.ip, options.port)


if __name__ == '__main__':
    main()


