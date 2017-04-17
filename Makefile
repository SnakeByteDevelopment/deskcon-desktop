DEST_DIR=/opt/desk-con/
SOURCE_DIR=$(shell pwd)
HOME_DIR=$(HOME)
GNOME_EXTENSION_DIR=$(HOME_DIR)/.local/share/gnome-shell/extensions

.PHONY: all server gnome-shell unity

help:
	@echo "DeskCon" makefile
	@echo
	@echo Options available:
	@echo  "  % make help "
	@echo  "         display this help"
	@echo
	@echo  "  % make server		"
	@echo	 "        Installes DeskCon Server to /opt/desk-con/"
	@echo  "        Creates Symlink to /usr/bin/deskcon-server"
	@echo
	@echo  "  % make gnome-shell"
	@echo  "        Enables GNOME Extension"
	@echo
	@echo  "  % make unity"
	@echo  "        Enables Unity Extension"
	@echo
	@echo  "  % make remove"
	@echo  "        Removes The DeskCon Server"
	@echo
	@echo "The author does not take any responsibility"
	@echo "for the bad use/misuse of this Makefile."
	@echo

server:
	@./runasroot.sh
	test ! -d $(DEST_DIR) && mkdir -p $(DEST_DIR)
	test -d $(DEST_DIR) && cp -r $(SOURCE_DIR)/server $(DEST_DIR)
	cp $(SOURCE_DIR)/server/share/deskcon-server.desktop.in /usr/share/applications/deskcon-server.desktop
	cp $(SOURCE_DIR)/server/share/deskcon-server-settings.desktop.in /usr/share/applications/deskcon-server-settings.desktop
	ln -s $(DEST_DIR)/server/deskcon-server.py /usr/bin/deskcon-server
	ln -s $(DEST_DIR)/server/settingswindow.py /usr/bin/deskcon-server-settings
	cp $(SOURCE_DIR)/systemd/deskcon-server.service /etc/systemd/system/

gnome-shell:
	@echo "Copying files to $(GNOME_EXTENSION_DIR)..."
	mkdir -p $(GNOME_EXTENSION_DIR)
	cp -r $(SOURCE_DIR)/gnome-shell/deskcon@screenfreeze.net $(GNOME_EXTENSION_DIR)
	@echo "... done."

unity:
	@echo "Starting Unity Extension..."
	$(SOURCE_DIR)/unity/deskcon-indicator.py&

remove:
	@./runasroot.sh
	@echo "Removing DeskCon Server..."
	rm -rf $(DEST_DIR)
	rm /usr/share/applications/deskcon-server.desktop
	rm /usr/share/applications/deskcon-server-settings.desktop
	rm /usr/bin/deskcon-server
	rm /usr/bin/deskcon-server-settings
	rm /etc/systemd/system/deskcon-server.service
	@echo "... done"

sex:
	@echo "Sorry, it's 'have sex', not 'make sex'."

love:
	@echo "make: *** No rule on how to make \`love'.  Stop."

war:
	@echo "make: *** No idea how to make war. War is stupid.  Stop."
