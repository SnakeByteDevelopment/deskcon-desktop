#!/usr/bin/env python2

import os
import sys
import tls
import argparse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('EDataServer', '1.2')
gi.require_version('EBook', '1.2')
from gi.repository import Gtk, GObject
from gi.repository import EDataServer, EBook, EBookContacts

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('ip', help='ip/hostname of the phone to ping')
parser.add_argument('port', type=int, help='port of the service (default 9096)')
parser.add_argument(
    'number', nargs='?',
    help='optional phone number',
    default='')
parser.add_argument(
    'msg', nargs='?',
    help='optional message',
    default='')


class EntryWindow(object):
    PHONE_PROPS = (
        'primary-phone',
        'mobile-phone',
        'business-phone',
        'home-phone',
        'business-phone-2',
        'home-phone-2',
        'company-phone',
        'other-phone',
        'assistant-phone',
        'callback-phone',
        'car-phone',
        'pager'
    )

    def __init__(self, ip, port, number):

        builder = Gtk.Builder()
        builder.add_from_file(os.path.dirname(os.path.realpath(__file__)) + "/share/ui/sms.glade")
        builder.connect_signals(self)
        self.window = builder.get_object("smswindow")
        self.numberentry = builder.get_object("numberentry")
        self.messagetextview = builder.get_object("messagetextview")
        self.charlabel = builder.get_object("charcountlabel")
        self.errordialog = builder.get_object("errordialog")

        self.window.set_wmclass("DeskCon", "Compose")

        self.ip = ip
        self.port = port

        # # get address book from eds
        # eds_registry = EDataServer.SourceRegistry.new_sync(None)
        # address_book_source = EDataServer.SourceRegistry.ref_default_address_book(eds_registry)
        # self.address_book_client = EBook.BookClient.new(address_book_source)
        #
        # # init list store
        # self.liststore = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        #
        # # register completion for numberentry
        # completion = Gtk.EntryCompletion()
        # self.numberentry.set_completion(completion)
        # completion.set_model(self.eds_search("")) # get all data
        # completion.set_text_column(0)
        #
        # completion.connect("match-selected", self.on_completion_select_number)
        # completion.set_match_func(self.fuzzy_match, None)

        self.numberentry.set_text(number)

        self.textbuffer = self.messagetextview.get_buffer()
        self.window.show_all()

    # search eds given a string
    def eds_search(self, search_string):
        q = EBookContacts.BookQuery.any_field_contains(search_string)
        status, contacts = self.address_book_client.get_contacts_sync(q.to_string())
        self.liststore.clear()
        for contact in contacts:
            full_name = contact.get_property('full_name')
            for phone_type in self.PHONE_PROPS:
                value = contact.get_property(phone_type)
                if value:
                    phone_number = contact.get_property(phone_type)
                    self.liststore.append([full_name + ': ' + phone_number, phone_number])
        sorted_list = Gtk.TreeModelSort(self.liststore)
        sorted_list.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        return sorted_list

    # match all words from for completion
    def fuzzy_match(self, completion, key_string, iter, data):
        row_string = completion.get_model().get_value(iter, 0)

        words = key_string.split()
        word_count_matches = 0
        for word in words:
            if word in row_string.lower() != -1:
                word_count_matches = word_count_matches + 1

        return word_count_matches >= len(words)

    def on_completion_select_number(self, entry_completion, model, iter):
        entry_completion.get_entry().set_text(model.get_value(iter, 1))
        return True

    def on_sendbutton_clicked(self, widget):
        siter = self.textbuffer.get_start_iter()
        eiter = self.textbuffer.get_end_iter()
        txt = self.textbuffer.get_text(siter, eiter, False).strip()
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
            errordialog.format_secondary_text("Errornumber " + str(errnum))
        errordialog.run()
        errordialog.hide()

    finally:
        Gtk.main_quit()


def main(options):
    GObject.threads_init()
    if options.msg != "":
        send_sms(options.number, options.msg, options.ip, options.port, None)
    win = EntryWindow(options.ip, options.port)
    win.run()


if __name__ == '__main__':
    options = parser.parse_args()
    main(options)
