# Makefile for SliTaz User Packages
#

PREFIX?=/usr
CGI_BIN?=/var/www/cgi-bin
DESTDIR?=
LINGUAS?=fr

all: msgfmt

# i18n.

pot:
	xgettext -o po/clients/sup-clients.pot -L Shell \
		--package-name="Sup Clients" \
		./sup ./libsup.sh

msgmerge:
	@for l in $(LINGUAS); do \
		if [ -f "po/clients/$$l.po" ]; then \
			echo -n "Updating $$l po file."; \
			msgmerge -U po/clients/$$l.po po/clients/sup-clients.pot ; \
		fi;\
	done;

msgfmt:
	@for l in $(LINGUAS); do \
		if [ -f "po/clients/$$l.po" ]; then \
			echo "Compiling sup clients $$l mo file..."; \
			mkdir -p po/clients/mo/$$l/LC_MESSAGES; \
			msgfmt -o po/clients/mo/$$l/LC_MESSAGES/sup-clients.mo \
				po/clients/$$l.po ; \
		fi;\
	done;

# Installation

install:
	install -m 0755 -d $(DESTDIR)$(PREFIX)/bin
	install -m 0755 -d $(DESTDIR)$(PREFIX)/lib/slitaz
	install -m 0755 -d $(DESTDIR)$(PREFIX)/share/applications
	install -m 0755 -d $(DESTDIR)$(PREFIX)/share/locale
	install -m 0755 sup $(DESTDIR)$(PREFIX)/bin
	install -m 0755 libsup.sh $(DESTDIR)$(PREFIX)/lib/slitaz
	install -m 0644 data/*.desktop $(DESTDIR)$(PREFIX)/share/applications
	cp -rf po/clients/mo/* $(DESTDIR)$(PREFIX)/share/locale
	# Demo & skeleton
	install -m 0755 -d $(DESTDIR)$(PREFIX)/share/sup/wok
	cp -rf wok/sup-demo $(DESTDIR)$(PREFIX)/share/sup/wok
	cp -rf wok/sup-skel $(DESTDIR)$(PREFIX)/share/sup/wok

# Use DESTDIR for TinyCM install path
# Example: make DESTDIR=/home/tux/Public/cgi-bin/tinycm server-install
install-server:
	install -m 0755 -d $(DESTDIR)/plugins
	install -m 0755 -d $(DESTDIR)/content/sup/packages
	install -m 0755 -d $(DESTDIR)/content/sup/wok
	cp -a server/* $(DESTDIR)/plugins
	chown -R www.www $(DESTDIR)/plugins
	chown -R www.www $(DESTDIR)/content/sup

# Uninstallation

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/sup
	rm -f $(DESTDIR)$(PREFIX)/lib/slitaz/libsup.sh
	rm -f $(DESTDIR)$(PREFIX)/share/applications/sup
	rm -f $(DESTDIR)$(PREFIX)/share/applications/sup-*.desktop
	rm -rf $(DESTDIR)$(PREFIX)/share/locale/*/LC_MESSAGES/sup-client.mo

# Clean

clean:
	rm -rf po/*/*~
	rm -rf po/*/mo
