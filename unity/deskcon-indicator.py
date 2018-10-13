#!/usr/bin/env python2

import json
import logging
import os
import signal

import dbus
import gi
from dbus import glib
from dbus.mainloop.glib import DBusGMainLoop
from gi.overrides import Gdk, Gtk, GObject
from gi.repository import AppIndicator3 as appindicator

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

glib.init_threads()

# FIXME: read config file
AUTO_STORE_CLIPBOARD = True

logging.basicConfig()
logger = logging.getLogger("deskcon-indicator")
logger.setLevel(logging.DEBUG)


class ClipboardListener:
    def __init__(self, on_change_cb):
        self.previous_text = None
        self.on_change_cb = on_change_cb
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self.clipboard_change)
        logger.debug("[ClipboardListener] ready")

    def clipboard_change(self, clipboard, ev):
        logger.debug("[ClipboardListener] clipboard_change")
        if not AUTO_STORE_CLIPBOARD:
            return

        text = self.clipboard.wait_for_text()
        if self.previous_text == text:
            logger.debug("[ClipboardListener] clipboard_change: didn't change")
        else:
            self.previous_text = text
            self.on_change_cb(text)


class ErrorDialog(Gtk.MessageDialog):
    def __init__(self, title, message):
        Gtk.MessageDialog.__init__(self, type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK)

        # FIXME: icon on message dialog isn't working
        #img = Gtk.Image.new_from_icon_name("dialog-question", Gtk.IconSize.DIALOG)
        #self.set_icon(img.get_pixbuf())
        self.set_title(title)
        self.set_markup(message)


class IndicatorDeskCon:
    def __init__(self):
        self.ind = appindicator.Indicator.new("indicator-deskcon",
                            "indicator-deskcon",
                            appindicator.IndicatorCategory.APPLICATION_STATUS)

        curr_dir = os.path.dirname(os.path.realpath(__file__))
        # first try to get the icon from the installed location, if it fails, try on current directory
        self.ind.set_icon(os.path.join(curr_dir, 'darkindicator-deskcon.svg'))

        self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.menu.show()
        self.ind.set_menu(self.menu)

        try:
            self.dbusclient = DbusClient(self)
        except dbus.exceptions.DBusException as ex:
            logger.fatal("[IndicatorDeskCon] DBus: Cannot connect to server. Check if the server is running.")
            self.showMessageDialog("DBus Error", "Cannot connect to server. Check if the server is running.", ex)
            self.handler_menu_exit()
            raise ex
        except Exception as ex:
            logger.fatal("[IndicatorDeskCon] DBus: Unknown error on dbus client.")
            self.showMessageDialog("DBus Error", "Unknown error on dbus client.", ex)
            self.handler_menu_exit()
            raise ex

        self.devicelist = {}

        #Settings Button
        self.settingsitem = Gtk.MenuItem("Settings")
        self.settingsitem.connect("activate", self.showsettings)
        self.settingsitem.show()
        self.menu.append(self.settingsitem)
        #Setup Button
        self.setupdeviceitem = Gtk.MenuItem("Setup Device")
        self.setupdeviceitem.connect("activate", self.setupdevice)
        self.setupdeviceitem.show()
        self.menu.append(self.setupdeviceitem)
        #Separator
        separator = Gtk.SeparatorMenuItem()
        separator.show()
        self.menu.append(separator)
        #Quit Button
        self.quititem = Gtk.MenuItem("Quit")
        self.quititem.connect("activate", self.handler_menu_exit)
        self.quititem.show()
        self.menu.append(self.quititem)

    def showMessageDialog(self, title, message, ex):
        pango_message = '<span size="large">' + message + '\n\nException:\n\n</span>' \
                        + '<span font_family="monospace">' + ex.message + '</span>'
        dialog = ErrorDialog(title, pango_message)
        dialog.run()
        dialog.destroy()
        self.handler_menu_exit()

    def update(self):
        try:
            jsonstr = self.dbusclient.getStats()
        except Exception:
            jsonstr = "{}"
        data = json.loads(jsonstr)

        if ('phones' not in data):
            return
        devices = data['phones']

        for device in devices:
            uuid = device['uuid']
            if (uuid in self.devicelist):
                self.devicelist[uuid].update(device)
            else:
                newdevice = DeviceMenuBundle(self, device)
                self.devicelist[uuid] = newdevice

    def notificationhandler(self):
        notification = self.dbusclient.getNotifications().split('::')
        uuid = notification[0]
        text = notification[1]

        if (uuid in self.devicelist):
            self.devicelist[uuid].addnotification(text)
        else:
            self.update()
            self.devicelist[uuid].addnotification(text)      

    
    def handler_menu_exit(self, evt=None):
        Gtk.main_quit()

    def compose(self, evt, ip, port):
        self.dbusclient.compose(ip, port)

    def ping(self, evt, ip, port):
        self.dbusclient.ping(ip, port)

    def sendfile(self, evt, ip, port):
        self.dbusclient.send_file(ip, port)

    def setclipboard(self, evt, ip, port):
        self.dbusclient.set_clipboard(ip, port)

    def showsettings(self, evt):
        self.dbusclient.show_settings()

    def setupdevice(self, evt):
        self.dbusclient.setup_device()

    def main(self):
        self.dbusclient.run()
        self.update()
        Gtk.main()

class DeviceMenuBundle():
    def __init__(self, indicator, data):
        self.device = data
        self.indicator = indicator 
        self.clipboard_listener = ClipboardListener(self.onClipboardUpdate)
        self.statsitem = Gtk.MenuItem("")
        self.statsitem.show()
        self.actionmenu = Gtk.Menu()
        self.statsitem.set_submenu(self.actionmenu)
        self.indicator.menu.insert(self.statsitem, 0)  
        self.composeitem = None

        #Actions
        if (data['canmessage']):
            self.composeitem = Gtk.MenuItem("Compose Message ...")
            self.composeitem.connect("activate", self.indicator.compose, 
                            data['ip'], data['controlport'])
            self.composeitem.show()
            self.actionmenu.append(self.composeitem)

        self.pingitem = Gtk.MenuItem("Ping")
        self.pingitem.connect("activate", self.indicator.ping, 
                        data['ip'], data['controlport'])
        self.pingitem.show()
        self.actionmenu.append(self.pingitem)

        self.setclipboarditem = Gtk.MenuItem("Set Clipboard")
        self.setclipboarditem.connect("activate", self.indicator.setclipboard,
                        data['ip'], data['controlport'])
        self.setclipboarditem.show()
        self.actionmenu.append(self.setclipboarditem)

        self.sendfileitem = Gtk.MenuItem("Send File(s)")
        self.sendfileitem.connect("activate", self.indicator.sendfile, 
                        data['ip'], data['controlport'])
        self.sendfileitem.show()
        self.actionmenu.append(self.sendfileitem)
        
        #Notifications
        self.notificationlist = []
        self.notificationitem = Gtk.MenuItem("Notifications")
        self.notificationsmenu = Gtk.Menu()
        self.notificationitem.set_submenu(self.notificationsmenu)
        self.notclearitem = Gtk.MenuItem("clear")
        self.notclearitem.connect("activate", self.clearnotifications)
        self.notclearitem.show()
        separator = Gtk.SeparatorMenuItem()
        separator.show()
        self.notificationsmenu.append(separator)
        self.notificationsmenu.append(self.notclearitem)

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        self.indicator.menu.insert(self.notificationitem, 1)
        #Sep
        self.indicator.menu.insert(separator, 2)

        self.update(data)

    def onClipboardUpdate(self, text):
        self.indicator.setclipboard(None, self.device['ip'], self.device['controlport'])

    def update(self, data):
        name = data['name']
        volume = str(data['volume'])
        battery = str(data['battery'])
        storage = str(data['storage'])
        wifistrength = str(data['wifistrength'])

        missedsmstxt = ""
        missedcalltxt = ""
        if (data['missedsmscount'] > 0): 
            missedsmstxt = "\nunread Messages "+ str(data['missedsmscount'])     
        if (data['missedcallcount'] > 0): 
            missedcalltxt = "\nmissed Calls "+ str(data['missedcallcount'])
        missedtxt = missedsmstxt+missedcalltxt
        
        text = (name + "\nBat: " + battery + "%"
                + " / Vol: " + volume + "%\n"
                + "Used Space: " + storage + "%"
                + " / WiFi: " + wifistrength + "%"
                + missedtxt)

        self.statsitem.set_label(text)
        if (data['canmessage'] and self.composeitem == None):
            self.composeitem = Gtk.MenuItem("Compose Message ...")
            self.composeitem.connect("activate", self.indicator.compose, 
                            data['ip'], data['controlport'])
            self.composeitem.show()
            self.actionmenu.append(self.composeitem)

    def addnotification(self, text):
        notificationitem = Gtk.MenuItem(text)
        notificationitem.show()
        self.notificationlist.append(notificationitem)
        self.notificationsmenu.insert(notificationitem, 0)
        self.notificationitem.show()

    def clearnotifications(self, widget):
        for item in self.notificationlist:
            self.notificationlist.remove(item)
            item.destroy()
        self.notificationitem.hide()

    # get pos child poc in menu
    def getmenuposition(self):
        pos = 0
        for child in self.indicator.menu.get_children():
            if (child == self.statsitem):
                return pos
            pos = pos + 1


class DbusClient():
    def __init__(self, indicator):
        self.indicator = indicator
        bus = dbus.SessionBus()
        proxy = bus.get_object("net.screenfreeze.desktopconnector",
                               "/net/screenfreeze/desktopconnector",
                               True, True)
        self.iface = dbus.Interface(proxy, 'net.screenfreeze.desktopconnector')

        # check if the dbus connection is working
        proxy.Introspect(dbus_interface="org.freedesktop.DBus.Introspectable")

        bus.add_signal_receiver(self.indicator.update,
                        dbus_interface="net.screenfreeze.desktopconnector",
                        signal_name="changed")
        bus.add_signal_receiver(self.indicator.notificationhandler,
                        dbus_interface="net.screenfreeze.desktopconnector",
                        signal_name="new_notification")

    def run(self):
        DBusGMainLoop(set_as_default=True)        
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()

    def getStats(self):
        return self.iface.stats()

    def getNotifications(self):
        return self.iface.notification()

    def compose(self, ip, port):
        host = ip + ":" + str(port)
        self.iface.compose_sms(host)

    def ping(self, ip, port):
        host = ip + ":" + str(port)
        self.iface.ping_device(host)

    def set_clipboard(self, ip, port):
        host = ip + ":" + str(port)
        self.iface.set_clipboard(host)

    def send_file(self, ip, port):
        host = ip + ":" + str(port)
        self.iface.send_file(host)

    def show_settings(self):
        self.iface.show_settings()

    def setup_device(self):
        self.iface.setup_device()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    ind = IndicatorDeskCon()
    ind.main()
