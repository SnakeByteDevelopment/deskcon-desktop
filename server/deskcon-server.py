#!/usr/bin/env python2
# DesCon Desktop Server
# Version 0.2

import gi
import json
import logging
import os
import platform
import signal
import socket
import subprocess
import _thread
import threading
import webbrowser
from base64 import b64decode

from OpenSSL import SSL
from OpenSSL.SSL import ZeroReturnError

from . import configmanager
from . import filetransfer
from . import mediacontrol
from . import notificationmanager
from .dbusservice import DbusThread
from server.models.dataObject import DataObject
from server.models.phone import Phone, PhoneState
from server.models.sessionInfo import SessionInfo
from server.models.sms import Sms

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


class Connector:
    def __init__(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGUSR1, self.signal_handler)
        self.uuid_list = {}
        self.mid_info = SessionInfo()
        # self.mid_info = {'phones': [], 'settings': {}}
        self.last_notification = ""

        self.dbus_service_thread = DbusThread(self)
        self.dbus_service_thread.daemon = True

        self.sslserver = SslServer(self)
        self.sslserver.daemon = True

    def run(self):
        GObject.threads_init()
        self.dbus_service_thread.start()
        self.sslserver.start()
        print("Server started")
        signal.pause()

    def signal_handler(self, signum, frame):
        if (signum == 10):
            print("restart Server")
            self.sslserver.stop()
            self.sslserver.join()
            # reload settings
            reload_config()
            # create new Thread
            self.sslserver = SslServer(self)
            self.sslserver.daemon = True
            self.sslserver.start()
            print("Server started")
            signal.pause()
        else:
            print("shuting down Server")
            self.sslserver.stop()
            self.sslserver.join()

    def get_mid_info(self):
        return json.dumps(self.mid_info)

    def get_last_notification(self):
        return self.last_notification

    def parseData(self, data, address, csocket):
        data_object = DataObject(**json.loads(data))
        print(data_object.to_nice_string())

        for phone in self.mid_info.phones:
            if phone.uuid == data_object.uuid:
                data_object.phone = phone
                break
        else:
            data_object.phone = Phone(data_object.uuid, data_object.device_name, None, None, False, 0, 0,
                                      address, False, 9096, None, None)
            self.mid_info.phones.append(data_object.phone)
            print("created " + data_object.uuid)

        if data_object.data_type == "STATS":
            data_object.phone.state = PhoneState(**data_object.data)

        elif data_object.data_type == "SMS":
            sms = Sms(**data_object.data)
            notificationmanager.buildSMSReceivedNotification(
                sms.name, sms.number, sms.message, address,
                data_object.phone.state.control_port, self.compose_sms)

        elif data_object.data_type == "CALL":
            notificationmanager.buildTransientNotification(
                data_object.phone.device_name, "incoming Call from " + str(data_object.data))

        elif data_object.data_type == "URL":
            if (AUTO_OPEN_URLS):
                webbrowser.open(data_object.data, 0, True)
            else:
                notificationmanager.buildNotification("URL", "Link: " + data_object.data)

        elif data_object.data_type == "CLPBRD":
            logger.debug("[Connector] CLPBRD received")
            if data_object.data == None or len(data_object.data) == 0:
                logger.debug("[Connector] CLPBRD received empty text, ignoring it")
                return

            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            current_clipboard = clipboard.wait_for_text()
            logger.debug("[Connector] Current clipboard readed")
            if current_clipboard == data_object.data:
                logger.info("[Connector] Not updating clipboard, no changes")
                return

            if AUTO_STORE_CLIPBOARD:
                logger.debug("[Connector] updating clipboard")
                clipboard.set_text(data_object.data.encode("utf-8"), -1)
                logger.debug("[Connector] clipboard updated")
                notificationmanager.buildTransientNotification("Clipboard", data_object.data)
            else:
                # FIXME: no timeout / able to select text
                notificationmanager.buildNotification("Clipboard", data_object.data)

        elif data_object.data_type == "MIS_CALL":
            notificationmanager.buildNotification(
                data_object.phone.device_name, "missed Call from " + str(data_object.data))

        elif data_object.data_type == "PING":
            notificationmanager.buildTransientNotification(
                "Ping from " + data_object.phone.device_name,
                "\nIP: " + data_object.phone.state.ip)

        elif data_object.data_type == "OTH_NOT":
            msginfo = data_object.data.split(': ', 1)
            new_notification = data_object.phone.uuid + "::" + data_object.data
            if self.last_notification != new_notification:
                self.last_notification = new_notification
                self.dbus_service_thread.emit_new_notification_signal()
                if len(msginfo) > 1:
                    sender = msginfo[0]
                    notification = msginfo[1]
                    notificationmanager.buildTransientNotification(
                        sender, notification)
                else:
                    notificationmanager.buildTransientNotification(
                        data_object.phone.device_name, data_object.data)

        elif data_object.data_type == "FILE_UP":
            filenames = data_object.data
            if AUTO_ACCEPT_FILES:
                print("accepted")
                filePaths = filetransfer.write_files(filenames, csocket)
                notificationmanager.buildFileReceivedNotification(
                    filePaths, self.open_file)
            else:
                accepted = notificationmanager.buildIncomingFileNotification(
                    filenames, data_object.phone.device_name)
                print("wait for ui")
                if (accepted):
                    print("accepted")
                    fpaths = filetransfer.write_files(filenames, csocket)
                    notificationmanager.buildFileReceivedNotification(
                        fpaths, self.open_file)
                else:
                    print("not accepted")

        elif data_object.data_type == "MEDIACTRL":
            _thread.start_new_thread(mediacontrol.control, (data_object.data,))

        elif data_object.data == "NOT_BIG":
            obj = json.loads(data_object.data)
            app = obj['appName']
            title = obj['title']
            text = obj['text']
            new_notification = data_object.phone.uuid + "::" + title + " - " + text
            if self.last_notification != new_notification:
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
                print("NOT_BIG captured")

        else:
            print("ERROR: Non parsable Data received")

    def compose_sms(self, number, ip, port, msg):
        subprocess.Popen([PROGRAMDIR + "/sms.py", ip, port, number, msg], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def ping_device(self, ip, port):
        subprocess.Popen([PROGRAMDIR + "/ping.py", ip, port], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send_file(self, ip, port):
        subprocess.Popen([PROGRAMDIR + "/filechooser.py", ip, port], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def set_clipboard(self, ip, port):
        print("setting clipboard")
        subprocess.Popen([PROGRAMDIR + "/setClipboard.py", ip, port], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def open_file(self, path):
        if path == "":
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
        subprocess.Popen([PROGRAMDIR + "/settingswindow.py"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def setup_device(self):
        subprocess.Popen([PROGRAMDIR + "/setupdevice.py"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class SslServer(threading.Thread):
    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.running = True
        self.conn = conn

    def run(self):
        GObject.threads_init()
        # Initialize context
        try:
            ctx = SSL.Context(SSL.SSLv23_METHOD)
            ctx.set_options(SSL.OP_NO_SSLv2 | SSL.OP_NO_SSLv3)  # TLS1 and up
            ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_cb)  # Demand a certificate
            ctx.set_cipher_list('HIGH:!SSLv2:!aNULL:!eNULL:!3DES:@STRENGTH')
            ctx.use_privatekey_file(configmanager.privatekeypath)
            ctx.use_certificate_file(configmanager.certificatepath)
            ctx.load_verify_locations(configmanager.cafilepath)
        except Exception as e:
            error = e[0]
            if len(error) > 0:  # ignore empty cafile error
                print(error)
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
                print("SSL connected")
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
                if errnum != 22:
                    print("Error " + str(e[0]))
            finally:
                # close connection
                if sslcsocket:
                    sslcsocket.shutdown()
                    sslcsocket.close()

        print("Server stopped")

    def stop(self):
        self.running = False
        self.sslserversocket.sock_shutdown(0)
        self.sslserversocket.close()


def verify_cb(conn, cert, errnum, depth, ok):
    # This obviously has to be updated
    # print "er"+str(errnum)
    # print "de"+str(depth)
    # print "ok "+str(ok)
    return ok


def main():
    os.chdir(PROGRAMDIR)
    app = Connector()
    app.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped")
        pass
