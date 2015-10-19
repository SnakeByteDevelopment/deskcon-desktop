#!/usr/bin/env python2

import os
import sys
import tls
import argparse
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('ip', help='ip/hostname of the phone to ping')
parser.add_argument('port', type=int, help='port of the service')
parser.add_argument(
    'number', nargs='?',
    help='optional phone number',
    default='')

class EntryWindow(object):

    def __init__(self, ip, port, number):

        builder = Gtk.Builder()
        builder.add_from_file(os.getcwd()+"/share/ui/sms.glade")
        builder.connect_signals(self)
        self.window = builder.get_object("smswindow")
        self.numberentry = builder.get_object("numberentry")
        self.messagetextview = builder.get_object("messagetextview")
        self.charlabel = builder.get_object("charcountlabel")
        self.errordialog = builder.get_object("errordialog")

        self.window.set_wmclass ("DeskCon", "Compose")

        self.ip = ip
        self.port = port

        self.numberentry.set_text(number)
        self.textbuffer = self.messagetextview.get_buffer()
        self.window.show_all()

    def on_sendbutton_clicked(self, widget):
        siter = self.textbuffer.get_start_iter()
        eiter = self.textbuffer.get_end_iter()
        txt = self.textbuffer.get_text(siter, eiter,  False).strip()
        number = self.numberentry.get_text().strip()

        if (number == ""):
            self.errordialog.format_secondary_text("No Number.")
            self.errordialog.run()
            self.errordialog.hide()
        elif (txt == ""):
            self.errordialog.format_secondary_text("Text is empty.")
            self.errordialog.run()
            self.errordialog.hide()
        else:
            send_sms(number, txt, self.ip, self.port, self.errordialog)

    def on_cancelbutton_clicked(self, widget):
        Gtk.main_quit()

    def on_smswindow_destroy(self, *args):
        Gtk.main_quit(*args)

    def on_errordialog_close(self, widget):
        Gtk.main_quit()

    def run(self):
        GObject.threads_init()
        Gtk.main()


def send_sms(recver, msg, host, port, errordialog):

    data = {'number': recver, 'message': msg}

    try:
        with tls.TLSConnection(host, port) as conn:
            conn.command('sms', data)
    except Exception as e:
        errnum = e[0]
        print "Error " + str(e[0])
        if (errnum == -5):
            errordialog.format_secondary_text(
                "The Device is not reachable. "
                "Maybe it's not on your Network")
        else:
            errordialog.format_secondary_text("Errornumber "+str(errnum))
        errordialog.run()
        errordialog.hide()

    finally:
        Gtk.main_quit()


def main(options):
    GObject.threads_init()
    win = EntryWindow(options.ip, options.port, options.number)
    win.run()


if __name__ == '__main__':
    options = parser.parse_args()
    main(options)


