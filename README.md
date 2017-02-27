DeskCon
-------
Version 0.4

integrates your Android Device in the Desktop. Receive Notifications, Files
and Commands from your mobile Device on your Desktop PC. The Data is send over a
secure TLS Connection. The Connection is encrypted and authenticated with
self-signed Certificates (RSA-2048 PK).

Warning: This Project is still in development (beta) and may contain some Bugs or
         Security Holes. If you find any, please report them ^^
         

Information:
------------
	- Project Website https://github.com/fbarriga/deskcon-desktop
	- Google Play Store https://play.google.com/store/apps/details?id=cl.felipebarriga.deskcon
         

Requirements (Desktop Server):
------------------------------
    - Python >= 2.7 < 3.x
    - pyopenssl
    - GTK3

Requirements (Unity Client):
------------------------------
    - Python >= 2.7 < 3.x
    - from pip:
        - dbus-python >= 1.2.4
        - pyOpenSSL >= 16.2.0
    - install binaries:
        - pygobject (GTK3) >= 3.22.0
        - AppIndicator3

Install:
--------
    - make sure Ports 8082 and 8083 tcp are open
    - start deskcon.sh in Root Folder of the Project
    - (optional) copy the Gnome Shell (>=3.8) Extension to ~/.local/share/gnome-shell/extensions
      and activate it 
    - (optional) start unity/deskcon-indicator.py for a Unity Indicator
    

Usage:
------
    - start the DeskCon Desktop Server
    - (optional) change config File in ~/.deskcon
    - To pair with a new Device, start setup_device.sh or use the Gnome Extension or Unity Indicator
    - start DeskCon App on your Android Device
    - select Network > Desktop Hosts
    - click the + Button and enter the IP of your Desktop PC
    - check whether the Fingerprints match


Todo:
-----
    - Translations
    - Mac/Windows support
    - Fingerprint validation via QR Code
    - Browser Extensions
    - Add option to automatically share clipboard
    - Pair client-server using resource discovery (broadcast would work fine)
    - Use external server to connect without local lan


Bugs:
-----
	- UI Design
