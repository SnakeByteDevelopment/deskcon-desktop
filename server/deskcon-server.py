#!/usr/bin/env python2
# DesCon Desktop Server
# Version 0.2

import socket
import webbrowser
import signal
import subprocess
import platform
import json
import os
import logging
import notificationmanager
import filetransfer
import threading
import thread
import configmanager
import mediacontrol
import gi
from OpenSSL import SSL
from OpenSSL.SSL import ZeroReturnError
from dbusservice import DbusThread
from base64 import b64decode

from server.models.dataObject import DataObject
from server.models.phone import Phone
from server.models.sessionInfo import SessionInfo

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf

logging.basicConfig()
logger = logging.getLogger("deskcon-server")
logger.setLevel(logging.DEBUG)

Gdk.threads_init()
GObject.threads_init()

configmanager.write_pidfile(str(os.getpid()))
abspath = os.path.abspath(__file__)

HOST = configmanager.get_bindip()
SECUREPORT = int(configmanager.secure_port)
PROGRAMDIR = os.path.dirname(abspath)
BUFFERSIZE = 4096

AUTO_ACCEPT_FILES = configmanager.auto_accept_files
AUTO_OPEN_URLS = configmanager.auto_open_urls
AUTO_STORE_CLIPBOARD = configmanager.auto_store_clipboard

def reload_config():
    global HOST, SECUREPORT, AUTO_STORE_CLIPBOARD, AUTO_ACCEPT_FILES, AUTO_OPEN_URLS
    configmanager.load()
    HOST = configmanager.get_bindip()
    SECUREPORT = int(configmanager.secure_port)
    AUTO_ACCEPT_FILES = configmanager.auto_accept_files
    AUTO_OPEN_URLS = configmanager.auto_open_urls
    AUTO_STORE_CLIPBOARD = configmanager.auto_store_clipboard


class Connector():
    def __init__(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGUSR1, self.signal_handler)
        self.uuid_list = {}
        self.mid_info = SessionInfo()
        # self.mid_info = {'phones': [], 'settings': {}}
        self.last_notification = ""

        self.dbus_service_thread = DbusThread(self)
        self.dbus_service_thread.daemon = True

        self.sslserver = sslserver(self)
        self.sslserver.daemon = True

    def run(self):
        GObject.threads_init()
        self.dbus_service_thread.start()
        self.sslserver.start()
        print "Server started"
        signal.pause()

    def signal_handler(self, signum, frame):
        if (signum == 10):
            print "restart Server"
            self.sslserver.stop()
            self.sslserver.join()
            # reload settings
            reload_config()
            # create new Thread
            self.sslserver = sslserver(self)
            self.sslserver.daemon = True
            self.sslserver.start()
            print "Server started"
            signal.pause()
        else:
            print "shuting down Server"
            self.sslserver.stop()
            self.sslserver.join()

    def get_mid_info(self):
        return json.dumps(self.mid_info)

    def get_last_notification(self):
        return self.last_notification

    def parseData(self, data, address, csocket):
        data_object = DataObject(**json.loads(data))
        print data_object.to_nice_string()

        phone = \
            Phone(data_object.uuid, data_object.device_name, None, None, False, 0, 0, address, False, 9096, None, None)

        if [phone.uuid for phone in self.mid_info.phones if phone.uuid == data_object.uuid]:
            self.mid_info.phones.append(phone)
            print "created "+data_object.uuid

        if data_object.data_type == "STATS":
            phone.state = data_object.data

        elif (data_object.data_type == "SMS"):
            smsobj = json.loads(data_object.data)
            name = smsobj['name']
            number = smsobj['number']
            smsmess = smsobj['message']
            notificationmanager.buildSMSReceivedNotification(
                name, number, smsmess, address,
                phone['controlport'], self.compose_sms)

        elif (msgtype == "CALL"):
            notificationmanager.buildTransientNotification(
                name, "incoming Call from " + message)

        elif (msgtype == "URL"):
            if (AUTO_OPEN_URLS):
                webbrowser.open(message, 0, True)
            else:
                notificationmanager.buildNotification("URL", "Link: "+message)

        elif (msgtype == "CLPBRD"):
            logger.debug("[Connector] CLPBRD received")
            if message == None or len(message) == 0:
                logger.debug("[Connector] CLPBRD received empty text, ignoring it")
                return

            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            current_clipboard = clipboard.wait_for_text()
            logger.debug("[Connector] Current clipboard readed")
            if current_clipboard == message:
                logger.info("[Connector] Not updating clipboard, no changes")
                return

            if AUTO_STORE_CLIPBOARD:
                logger.debug("[Connector] updating clipboard")
                clipboard.set_text(message.encode("utf-8"), -1)
                logger.debug("[Connector] clipboard updated")
                notificationmanager.buildTransientNotification("Clipboard", message)
            else:
                # FIXME: no timeout / able to select text
                notificationmanager.buildNotification("Clipboard", message)

        elif (msgtype == "MIS_CALL"):
            notificationmanager.buildNotification(
                name, "missed Call from " + message)

        elif (data_object.data_type == "PING"):
            notificationmanager.buildTransientNotification(
                "Ping from " + data_object.device_name,
                #"Name: " + name +
                #"\nUUID: " + uuid +
                "\nIP: " + address)

        elif (msgtype == "OTH_NOT"):
            msginfo = message.split(': ', 1)
            new_notification = uuid+"::"+message
            if (self.last_notification != new_notification):
                self.last_notification = new_notification
                self.dbus_service_thread.emit_new_notification_signal()
                if (len(msginfo) > 1):
                    sender = msginfo[0]
                    notification = msginfo[1]
                    notificationmanager.buildTransientNotification(
                        sender, notification)
                else:
                    notificationmanager.buildTransientNotification(
                        name, message)

        elif (msgtype == "FILE_UP"):
            filenames = json.loads(message)
            if (AUTO_ACCEPT_FILES):
                print "accepted"
                filePaths = filetransfer.write_files(filenames, csocket)
                notificationmanager.buildFileReceivedNotification(
                    filePaths, self.open_file)
            else:
                accepted = notificationmanager.buildIncomingFileNotification(
                    filenames, name)
                print "wait for ui"
                if (accepted):
                    print "accepted"
                    fpaths = filetransfer.write_files(filenames, csocket)
                    notificationmanager.buildFileReceivedNotification(
                        fpaths, self.open_file)
                else:
                    print "not accepted"

        elif (msgtype == "MEDIACTRL"):
            thread.start_new_thread(mediacontrol.control, (message,))

        elif (msgtype == "NOT_BIG"):
            obj = json.loads(message)            
            app = obj['appName']
            title = obj['title']
            text = obj['text']
            new_notification = uuid+"::"+title+" - "+text
            if (self.last_notification != new_notification):
                self.last_notification = new_notification
                self.dbus_service_thread.emit_new_notification_signal()
                if "icon" in obj:
                    icon = b64decode(obj['icon'])
                    loader = GdkPixbuf.PixbufLoader.new_with_type('png')
                    loader.write(icon)
                    pixbuf = loader.get_pixbuf()
                    loader.close()
                else:
                    pixbuf = None
                            
                notificationmanager.buildBigNotification(title, text, pixbuf)
                print "NOT_BIG captured"

        else:
            print "ERROR: Non parsable Data received"

        #print json.dumps(self.mid_info)

    def compose_sms(self, number, ip, port, msg):
        subprocess.Popen([PROGRAMDIR+"/sms.py", ip, port, number, msg], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def ping_device(self, ip, port):
        subprocess.Popen([PROGRAMDIR+"/ping.py", ip, port], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send_file(self, ip, port):
        subprocess.Popen([PROGRAMDIR+"/filechooser.py", ip, port], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def set_clipboard(self, ip, port):
        print "setting clipboard"
        subprocess.Popen([PROGRAMDIR+"/setClipboard.py", ip, port], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def open_file(self, path):
        if (path == ""):
            path = configmanager.downloaddir
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.Popen(["xdg-open", path], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def show_settings(self):
        subprocess.Popen([PROGRAMDIR+"/settingswindow.py"], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def setup_device(self):
        subprocess.Popen([PROGRAMDIR+"/setupdevice.py"], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)



class sslserver(threading.Thread):

    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.running = True
        self.conn = conn

    def run(self):
        GObject.threads_init()
        # Initialize context
        try:
            ctx = SSL.Context(SSL.SSLv23_METHOD)
            ctx.set_options(SSL.OP_NO_SSLv2|SSL.OP_NO_SSLv3) #TLS1 and up
            ctx.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb) #Demand a certificate
            ctx.set_cipher_list('HIGH:!SSLv2:!aNULL:!eNULL:!3DES:@STRENGTH')
            ctx.use_privatekey_file(configmanager.privatekeypath)
            ctx.use_certificate_file(configmanager.certificatepath)
            ctx.load_verify_locations(configmanager.cafilepath)
        except Exception as e:
            error = e[0]
            if len(error)>0:  # ignore empty cafile error
                print error
        self.sslserversocket = SSL.Connection(ctx, socket.socket(socket.AF_INET,
                             socket.SOCK_STREAM))

        self.sslserversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sslserversocket.bind(('', SECUREPORT))
        self.sslserversocket.listen(5)
        while self.running:
            sslcsocket = None
            try:
                sslcsocket, ssladdress = self.sslserversocket.accept()
                address = format(ssladdress[0])
                print "SSL connected"
                # receive data
                data = sslcsocket.recv(4096)
                try:
                    # maybe this is already parseble. then don't wait as the client may wait for us then
                    self.conn.parseData(data, address, sslcsocket)
                except:
                    try:
                        while True:
                            more = sslcsocket.recv(4096)
                            data += more
                    except ZeroReturnError as e:
                        # this is no real error. Only no data avail.
                        pass

                    self.conn.parseData(data, address, sslcsocket)
                # emit new data dbus Signal
                self.conn.dbus_service_thread.emit_changed_signal()
            except Exception as e:
                errnum = e[0]
                if (errnum != 22):
                    print "Error " + str(e[0])
            finally:
                # close connection
                if sslcsocket:
                    sslcsocket.shutdown()
                    sslcsocket.close()

        print "Server stopped"

    def stop(self):
        self.running = False
        self.sslserversocket.sock_shutdown(0)
        self.sslserversocket.close()


def verify_cb(conn, cert, errnum, depth, ok):
    # This obviously has to be updated
    #print "er"+str(errnum)
    #print "de"+str(depth)
    #print "ok "+str(ok)
    return ok


def main():
    os.chdir(PROGRAMDIR)
    app = Connector()
    app.run()

if __name__ == '__main__':
   try:
      main()
   except KeyboardInterrupt:
      print "\nServer stopped"
      pass
