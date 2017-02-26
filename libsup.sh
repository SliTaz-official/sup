#!/bin/sh
#
# libsup.sh - Shared SHell functions between sup cmdline/gtk+ tools
#
# Copyright (C) 2017 SliTaz GNU/Linux - BSD License
# Author: Christophe Lincoln <pankso@slitaz.org>
#
. /lib/libtaz.sh

bin="$HOME/.local/bin"
config="$HOME/.config"
cache="$HOME/.cache/sup"
data="$HOME/.local/share"
supdb="$data/sup"
installed="$supdb/installed"
activity="$cache/activity.log"

mirror="http://scn.slitaz.org/content/sup/packages"
md5list="$supdb/packages.md5"
pkgsdb="$supdb/packages.db"

wok="$supdb/wok"
supcook="$HOME/sup-cook"
cooked="$supcook/packages"

export TEXTDOMAIN='sup-clients'
alias wget="busybox wget"

#
# Functions
#

# Set ttysize= # stty will not work if called from GTK box or CGI script
tty_size() {
	local size=$(stty size | cut -d " " -f 2)
	[ "$size" ] && local size=80
	echo ${size}
}

# Extract a sup package: extract_sup "/path/to/pkg.sup"
extract_sup() {
	pkg="$(basename ${1%.sup})"
	supfile="$(readlink -f ${1%.sup}.sup)"
		
	gettext "Uncompressing package tree..."
	rm -rf ${pkg} && mkdir -p ${pkg} && cd ${pkg}
	
	cpio -idm --quiet < "$supfile"
	unlzma -c files.lzma | cpio -idm --quiet
	
	rm files.lzma
	size="$(du -sh $dest | cut -d "	" -f 1)"
	status
}

# Install a sup package
install_sup() {
	pkg="$(basename ${1%.sup})"
	supfile="$(readlink -f ${1%.sup}.sup)"
	cache="$cache/install"
	
	rm -rf ${cache} && mkdir ${cache} 
	cp ${supfile} ${cache} && cd ${cache}
	
	# Get receip for deps
	cpio -i receip --quiet < ${supfile}
	. receip
	
	# Install sup deps || exit on missing system deps ?
	newline
	gettext "Checking dependencies for"; echo " $PACKAGE..."
	for dep in ${SUP_DEPS}; do
		if [ ! "$installed/$dep" ]; then
			echo "Missing dependency:"; colorize 35 " $dep"
		fi
	done
	. /etc/slitaz/slitaz.conf
	for dep in ${DEPENDS}; do
		if [ ! "$PKGS_DB/installed/$dep" ]; then
			echo "Missing dependency:"; colorize 35 " $dep"
		fi
	done
	
	newline
	gettext "Installing package:"; colorize 36 " $PACKAGE $VERSION"
	log "$(gettext 'Installing package:') $PACKAGE $VERSION"
	separator
	
	# Extract and source receip first to check deps
	extract_sup "$supfile"
	
	# Execute sup_install() in files/ tree so packages maintainers just
	# have to dl and move files where they were in $HOME
	cd files
	if grep -q "^sup_install" ../receip; then
		gettext "Executing install function:"
		indent $(($(tty_size) - 18)) "[ $(colorize 33 sup_install) ]"
		sup_install
	fi
	
	# Create files.list
	if [ "$verbose" ]; then
		gettext "Creating the list of installed files..."; echo
	fi
	files_list="${cache}/${PACKAGE}-${VERSION}/files.list"
	find . -type f -print > ${files_list}
	find . -type l -print >> ${files_list}
	sed -i s/'^.'/''/g ${files_list}
	
	# Back to pkg tree
	cd ${cache}/${PACKAGE}-${VERSION}
	echo "sup_size=\"$(du -sh files | cut -d "	" -f 1)\"" >> receip
	
	# Now we need a place to store package data and set $sup_size
	
	gettext "Installing files:"
	echo -n "$(colorize 35 " $(wc -l files.list | cut -d " " -f 1)")"
	data="${installed}/${PACKAGE}"
	mkdir -p ${data}
	for file in receip README files.list; do
		[ -f "$file" ] && cp -f ${file} ${data}
	done
	for file in $(ls -A files); do
		cp -rf files/${file} ${HOME}
	done && status
	newline && rm -rf ${cache}
}

# Remove a sup package
remove_sup() {
	pkg="$1"
	files_list="$installed/$pkg/files.list"
	. ${installed}/${pkg}/receip
	
	newline
	gettext "Removing package:"; colorize 36 " $PACKAGE $VERSION"
	log "$(gettext 'Removing package:') $PACKAGE $VERSION"
	separator
	
	gettext "Files to remove :"
	indent $(($(tty_size) - 8)) \
		"[ $(colorize 33 $(wc -l ${files_list} | cut -d ' ' -f 1)) ]"
	
	# Remove all files
	for file in $(cat $files_list)
	do
		# --verbose
		if [ "$verbose" ]; then
			gettext "Removing file   :"; echo -n " ${file#/}"
			rm -f "${HOME}${file}"; status
			# Empty folder ?
			if [ ! "$(ls -A ${HOME}$(dirname $file))" ]; then
				path="$(dirname $file)"
				gettext "Removing folder :"; echo -n " ${path#/}"
				rmdir "${HOME}$(dirname $file)"; status
			fi
		else
			rm -f "${HOME}${file}"
			# Empty folder ?
			if [ ! "$(ls -A ${HOME}$(dirname $file))" ]; then
				rmdir "${HOME}$(dirname $file)"
			fi
		fi
	done
	gettext "Removing packages from local database..."
	rm -rf ${installed}/${pkg}; status
	newline
}
