#!/usr/bin/env python2

import sys
import socket
import argparse
from . import configmanager
from .tls import TLSConnection

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('ip', help='ip/hostname of the phone to ping')
parser.add_argument('port', type=int, help='port of the service (default 9096)')

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


