import json
import socket

from OpenSSL import SSL, crypto

import configmanager


def ignore_fail(callable):
    try:
        callable()
    except:
        pass


def verify_cb(conn, cert, errnum, depth, ok):
    # This obviously has to be updated
    #print "er"+str(errnum)
    #print "de"+str(depth)
    #print "ok "+str(ok)
    return ok


class TLSConnection(object):
    def __init__(self, host, port):
        port = int(port)
        self.ctx = ctx = SSL.Context(SSL.TLSv1_METHOD)
        # TLS1 and up
        ctx.set_options(SSL.OP_NO_SSLv2 | SSL.OP_NO_SSLv3)
        # Demand a certificate
        ctx.set_verify(SSL.VERIFY_PEER, verify_cb)
        ctx.use_privatekey_file(configmanager.privatekeypath)
        ctx.use_certificate_file(configmanager.certificatepath)
        ctx.load_verify_locations(configmanager.cafilepath)
        self.host, self.port = host, port

    def message(self, obj):
        message = json.dumps(obj)
        self.sslclientsocket.sendall(message)
        return self.sslclientsocket.recv(2)

    def command(self, type, data=None):
        uuid = configmanager.uuid
        hostname = socket.gethostname()

        jsonobj = {
            'uuid': uuid,
            'name': hostname,
            'type': type,
            'data': data,
        }
        self.message(jsonobj)

    def close(self):
        ignore_fail(self.sslclientsocket.close)
        ignore_fail(self.sslclientsocket.shutdown)

    def __enter__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sslclientsocket = SSL.Connection(self.ctx, sock)
        self.sslclientsocket.connect((self.host, self.port))
        return self

    def __exit__(self, type, ex, tb):
        self.close()
