PREFIX=/usr/local

SOURCE_DIR=$(shell pwd)
HOME_DIR=$(HOME)
GNOME_EXTENSION_DIR=$(HOME_DIR)/.local/share/gnome-shell/extensions
SYSTEMD_USER_DIR=/usr/lib/systemd/user

DEST_DIR=$(PREFIX)/lib/deskcon-desktop

.PHONY: all server gnome-shell

help:
	@echo "DeskCon" makefile
	@echo
	@echo Options available:
	@echo  "  % make help "
	@echo  "         display this help"
	@echo
	@echo  "  % make install"
	@echo  "        Install DeskCon Server to $(DEST_DIR)"
	@echo  "        Creates Symlinks in $(PREFIX): deskcon-server, deskcon-indicator and deskcon-server-settings"
	@echo
	@echo  "  % make install-user-gnome-shell"
	@echo  "        Install GNOME Extension on $(GNOME_EXTENSION_DIR)"
	@echo
	@echo  "  % make remove"
	@echo  "        Removes The DeskCon Server"
	@echo

install:
	@./runasroot.sh
	test ! -d $(DEST_DIR) && mkdir -p $(DEST_DIR)
	test -d $(DEST_DIR) && cp -r $(SOURCE_DIR)/deskcon.sh $(SOURCE_DIR)/server $(SOURCE_DIR)/unity $(DEST_DIR)
	cp $(SOURCE_DIR)/unity/deskcon-indicator.desktop.in $(PREFIX)/share/applications/deskcon-indicator.desktop
	cp $(SOURCE_DIR)/server/share/deskcon-server.desktop.in $(PREFIX)/share/applications/deskcon-server.desktop
	cp $(SOURCE_DIR)/server/share/deskcon-server-settings.desktop.in $(PREFIX)/share/applications/deskcon-server-settings.desktop
	ln -s $(DEST_DIR)/unity/deskcon-indicator.py $(PREFIX)/bin/deskcon-indicator
	ln -s $(DEST_DIR)/server/deskcon-server.py $(PREFIX)/bin/deskcon-server
	ln -s $(DEST_DIR)/server/settingswindow.py $(PREFIX)/bin/deskcon-server-settings
	cp $(SOURCE_DIR)/systemd/deskcon-server.service $(SYSTEMD_USER_DIR)/
	sed -i s#PREFIX#"$(PREFIX)"#g $(PREFIX)/share/applications/deskcon-indicator.desktop
	sed -i s#INSTALL_DEST_DIR#"$(DEST_DIR)"#g $(PREFIX)/share/applications/deskcon-indicator.desktop
	sed -i s#INSTALL_DEST_DIR#"$(DEST_DIR)"#g $(SYSTEMD_USER_DIR)/deskcon-server.service

install-user-gnome-shell:
	@echo "Copying files to $(GNOME_EXTENSION_DIR)..."
	mkdir -p $(GNOME_EXTENSION_DIR)
	cp -r $(SOURCE_DIR)/gnome-shell/deskcon@screenfreeze.net $(GNOME_EXTENSION_DIR)
	@echo "... done."

remove:
	@./runasroot.sh
	@echo "Removing DeskCon Server..."
	rm -rf $(DEST_DIR)
	rm -f $(PREFIX)/share/applications/deskcon-indicator.desktop
	rm -f $(PREFIX)/share/applications/deskcon-server.desktop
	rm -f $(PREFIX)/share/applications/deskcon-server-settings.desktop
	rm -f $(PREFIX)/bin/deskcon-indicator
	rm -f $(PREFIX)/bin/deskcon-server
	rm -f $(PREFIX)/bin/deskcon-server-settings
	rm -f $(SYSTEMD_USER_DIR)/deskcon-server.service
	@echo "... done"
