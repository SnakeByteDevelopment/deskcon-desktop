import socket

from OpenSSL import SSL, crypto

from . import configmanager
from server.models.sslMessage import SslMessage


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

    def message(self, message):
        self.send(message.dump_to_json())
        response_buffer = ""
        response_buffer += self.recv(2)
        while len(response_buffer) < 2:
            response_buffer += self.recv(1)
        return response_buffer

    def command(self, type, data=None):
        uuid = configmanager.uuid
        hostname = socket.gethostname()

        ssl_message = SslMessage(uuid, hostname, type, data)
        return self.message(ssl_message)

    def send(self, data):
        self.ssl_client_socket.sendall(data)

    def recv(self, nbytes):
        self.ssl_client_socket.recv(nbytes)

    def close(self):
        ignore_fail(self.ssl_client_socket.close)
        ignore_fail(self.ssl_client_socket.shutdown)

    def __enter__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ssl_client_socket = SSL.Connection(self.ctx, sock)
        self.ssl_client_socket.connect((self.host, self.port))
        return self

    def __exit__(self, type, ex, tb):
        self.close()
