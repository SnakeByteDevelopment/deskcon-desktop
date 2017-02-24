#!/usr/bin/env python2
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gdk

import notificationmanager
import tls
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('ip', help='ip/hostname of the phone to set the Clipboard')
parser.add_argument('port', type=int, help='port of the service (default 9096)')


def set_clipboard( host, port):

    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    text = clipboard.wait_for_text()

    data = {'text': text}

    try:
        with tls.TLSConnection(host, port) as conn:
            conn.command('clpbrd', data)
    except Exception as e:
        errnum = e[0]
        print "Error " + str(e[0])
        if (errnum == -5):
            notificationmanager.buildTransientNotification("Error setting clipboard!",
                "The Device is not reachable. "
                "Maybe it's not on your Network")
        else:
            notificationmanager.buildTransientNotification("Error setting clipboard!",
                "Errornumber "+str(errnum))


def main(args=None):
    options = parser.parse_args(args)
    set_clipboard(options.ip, options.port)


if __name__ == '__main__':
    main()

