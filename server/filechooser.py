#!/usr/bin/env python2
import os
import sys
import threading
import json
import tls
from gi.repository import Gtk, GObject

sent_size = 0
total_size = 0


class FileChooserWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)
        self.dialog = Gtk.FileChooserDialog(
            "Please choose a file", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        homefolder = os.path.expanduser("~")
        self.dialog.set_select_multiple(True)
        self.dialog.set_current_folder(homefolder)

    def run(self, ip, port):
        response = self.dialog.run()
        if response == Gtk.ResponseType.OK:
            files = self.dialog.get_filenames()
            pd = ProgressbarDialog(self.dialog)
            t = threading.Thread(target=pd.run, args=())
            t.daemon = True
            t.start()

            send_data(self.dialog, files, ip, port, pd)
        elif response == Gtk.ResponseType.CANCEL:
            self.dialog.destroy()


class ProgressbarDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Filetransfer", parent, 0)

        self.set_default_size(150, 50)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_transient_for(parent)

        label = Gtk.Label("Transfering Files ...")
        self.progressbar = Gtk.ProgressBar()

        box = self.get_content_area()
        box.add(label)
        box.add(self.progressbar)
        self.show_all()


def send_data(dialog, files, ip, port, pd):
    HOST, PORT = ip, int(port)

    filenames = []
    for filepath in files:
        head, name = os.path.split(filepath)
        filenames.append(name)

    data = json.dumps(filenames)

    try:
        with tls.TLSConnection(HOST, PORT) as conn:
            response = conn.command('fileup', data)
            print response
            if (response == "O"):
                # Get total transfer size
                global total_size
                for filepath in files:
                    total_size = total_size + os.path.getsize(filepath)

                print "send files"
                for filepath in files:
                    send_file(filepath, conn, pd)
                print "succesfully send Files"
    except Exception as e:
        print "Error " + str(e)
    finally:
        dialog.destroy()


def send_file(filepath, socket, pd):
    filesize = os.path.getsize(filepath)

    socket.send(str(filesize)+"\n")
    #wait for ready
    socket.recv(1)

    ofile = open(filepath, 'rb')
    fbuffer = ofile.read(4096)
    sent_size = 0
    while (fbuffer):
        socket.send(fbuffer)
        fbuffer = ofile.read(4096)
        update_progress(pd)

    ofile.close()


def update_progress(pd):
    global sent_size
    sent_size = sent_size+4096
    perc = (sent_size/float(total_size))
    pd.progressbar.set_fraction(perc)


def main(args):
    GObject.threads_init()
    ip = args[1]
    port = args[2]
    win = FileChooserWindow()
    win.run(ip, port)

if __name__ == '__main__':
    if(len(sys.argv) < 3):
        print "not enough arguments given"
    else:
        main(sys.argv)







