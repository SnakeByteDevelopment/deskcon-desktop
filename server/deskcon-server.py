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
import notificationmanager
import filetransfer
import threading
import thread
import configmanager
import mediacontrol
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf
from OpenSSL import SSL
from OpenSSL.SSL import ZeroReturnError
from dbusservice import DbusThread
from base64 import b64decode

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
        self.mid_info = {'phones': [], 'settings': {}}
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
        jsondata = json.loads(data)
        uuid = jsondata['uuid']
        name = jsondata['devicename']
        msgtype = jsondata['type']
        message = jsondata['data']

        print "UUID", uuid
        print "NAME", name
        print "TYPE", msgtype
        print "MSG", message

        if uuid not in self.uuid_list:
            self.mid_info['phones'].append({
                'uuid': uuid, 'name': name,
                'battery': -1, 'volume': -1,
                'batterystate': False, 'missedsmscount': 0,
                'missedcallcount': 0, 'ip': address,
                'canmessage': False, 'controlport': 9096,
                'storage': -1, 'wifistrength': -1})

            apos = 0
            for x in range(0, len(self.mid_info['phones'])):
                if self.mid_info['phones'][x]['uuid'] == uuid:
                    apos = x

            self.uuid_list[uuid] = apos
            print "created "+uuid+" at pos "+str(apos)

        pos = self.uuid_list[uuid]
        phone = self.mid_info['phones'][pos]

        if (msgtype == "STATS"):
            newstats = json.loads(message)

            def maybe_transfer(key, new=None):
                if key in newstats:
                    if new is not None:
                        phone[new] = newstats[key]
                    else:
                        phone[key] = newstats[key]

            maybe_transfer('volume')
            maybe_transfer('controlport')
            maybe_transfer('battery')
            maybe_transfer('batterystate')
            maybe_transfer('missedmsgs', 'missedsmscount')
            maybe_transfer('missedcalls', 'missedcallcount')
            maybe_transfer('canmessage')
            maybe_transfer('storage')
            maybe_transfer('wifistrength')
            phone['ip'] = address

        elif (msgtype == "SMS"):
            smsobj = json.loads(message)
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
            if message == None or len(message) == 0:
                print "Error, empty text received on clipboard"
            else:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                clipboard.set_text(message.encode("utf-8"), -1)
                notificationmanager.buildTransientNotification("Clipboard", message)

        elif (msgtype == "MIS_CALL"):
            notificationmanager.buildNotification(
                name, "missed Call from " + message)

        elif (msgtype == "PING"):
            notificationmanager.buildTransientNotification(
                "Ping from " + name,
                "Name: " + name +
                "\nUUID: " + uuid +
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

    def compose_sms(self, number, ip, port):
        subprocess.Popen([PROGRAMDIR+"/sms.py", ip, port, number], stdin=subprocess.PIPE,
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
