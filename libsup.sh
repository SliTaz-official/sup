#!/bin/sh
#
# libsup.sh - Shared SHell functions between sup cmdline/gtk+ tools
#
# Copyright (C) 2017 SliTaz GNU/Linux - BSD License
# Author: Christophe Lincoln <pankso@slitaz.org>
#
. /lib/libtaz.sh

config="$HOME/.config"
cache="$HOME/.cache/sup"
local="$HOME/.local"
data="$local/share"
supdb="$local/share/sup"
installed="$supdb/installed"
activity="$cache/activity.log"

server="http://scn.slitaz.org/"
mirror="${server}content/sup/packages"
pkgsdb="$supdb/packages.sql"

wok="$supdb/wok"
supcook="$HOME/sup-cook"
cooked="$supcook/packages"

export TEXTDOMAIN='sup-clients'
alias wget="busybox wget"

#
# Functions
#

# --> get_cols
tty_size() {
	if ! stty size | cut -d " " -f 2; then
		echo 80
	fi
}

# Print info a la status way: info [color] [content]
info() {
	local info="$2"
	local char="$(echo $info | wc -L)"
	local in=$((7 + ${char}))
	indent $(($(get_cols) - ${in})) "[ $(colorize $1 $info) ]"
}

# Pretty Busybox wget output. Usage: download [name] [url] [dest]
# Download in current dir if $3 is not set
download() {
	name="$1"
	url="$2"
	dest=${3:-$(pwd)}
	file=$(basename $url)
	trap "echo -e '\nExiting...'; rm -f ${dest%/}/$file" SIGINT INT TERM
	# i18n
	dl="$(gettext 'Downloading')"
	
	# Get download name chars to adjust progress bar placement
	char="$(echo $dl $name | wc -L)"
	in=$((3 + ${char}))
	
	echo -n "$dl $(colorize 035 $name →)"
	wget -c -P ${dest} "$url" 2>&1 | while read file pct progress null
	do
		case "$progress" in
			"|"*) echo -n "$(indent ${in} $progress)" | sed s'!*!-!'g ;;
		esac
	done
	
	case "$?" in
		0)
			# Handle 4.0K 46.0M
			size="$(du -mh ${dest%/}/$(basename $2) | awk '{print $1}')"
			char="$(echo $size | wc -L)"
			in=$((7 + ${char}))
			indent $(($(tty_size) - ${in})) "[ $(colorize 035 $size) ]" ;;
		1) status ;;
	esac
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

# System dependencies: exit on missing system deps ?
check_sys_deps() {
	. /etc/slitaz/slitaz.conf # PKGS_DB
	for dep in ${DEPENDS}; do
		if [ ! -d "$PKGS_DB/installed/$dep" ]; then
			gettext "Missing dependency:"; colorize 31 " $dep"; return 1
		fi
	done
}

# Install a sup package
install_sup() {
	pkg="$(basename ${1%.sup})"
	supfile="$(readlink -f ${1%.sup}.sup)"
	
	rm -rf ${cache}/install && mkdir ${cache}/install
	cp ${supfile} ${cache}/install && cd ${cache}/install
	
	# Get receip for deps
	cpio -i receip --quiet < ${supfile}
	. receip
	
	# Install sup deps
	gettext "Checking package dependencies"
	deps="$(echo $SUP_DEPS $DEPENDS | wc -w)"
	in=$((8 + ${deps}))
	indent $(($(tty_size) - ${in})) "[ $(colorize 033 $deps) ]"
	
	for dep in ${SUP_DEPS}; do
		if [ ! -d "$installed/$dep" ]; then
			gettext "Missing dependency:"; colorize 35 " $dep"
			sup -i "$dep"
		fi
	done
	check_sys_deps
	
	# Remove existing package files to avoid untracked files
	if [ -d "$installed/$PACKAGE" ]; then
		gettext "Removing existing package files..."
		remove_sup "$PACKAGE" >/dev/null; status
	fi
	
	newline
	echo -n "$(colorize 33 $(gettext 'Installing package:'))"
	colorize 36 " $PACKAGE $VERSION"
	log "$(gettext 'Installing package:') $PACKAGE $VERSION"
	separator
	
	# Extract and source receip first to check deps
	md5sum=$(md5sum $supfile | awk '{print $1}')
	extract_sup "$supfile"
	
	# Execute sup_install() in files/ tree so packages maintainers just
	# have to dl and move files where they were in $HOME
	cd files
	if grep -q "^sup_install" ../receip; then
		gettext "Executing install function:"
		indent $(($(tty_size) - 18)) "[ $(colorize 033 sup_install) ]"
		sup_install
	fi
	
	# Create files.list
	if [ "$verbose" ]; then
		gettext "Creating the list of installed files..."; echo
	fi
	files_list="${cache}/install/${PACKAGE}-${VERSION}/files.list"
	find . -type f -print > ${files_list}
	find . -type l -print >> ${files_list}
	sed -i sed s'/^.//'g ${files_list}
	
	# Back to pkg tree
	cd ${cache}/install/${PACKAGE}-${VERSION}
	echo "sup_size=\"$(du -sh files | cut -d "	" -f 1)\"" >> receip
	echo "md5_sum=\"${md5sum}\"" >> receip
	
	# Now we need a place to store package data and set $sup_size
	echo -n "$(colorize 036 $(gettext 'Installing files:'))"
	echo -n " $(colorize 033 $(wc -l files.list | cut -d ' ' -f 1))"
	
	data="${installed}/${PACKAGE}"
	mkdir -p ${data}
	
	for file in receip README files.list; do
		[ -f "$file" ] && cp -f ${file} ${data}
	done
	for file in $(ls -A files); do
		cp -rf files/${file} ${HOME}
	done
	status
	
	newline && rm -rf ${cache}/install
}

# Remove a sup package
remove_sup() {
	pkg="$1"
	files_list="$installed/$pkg/files.list"
	. ${installed}/${pkg}/receip
	
	newline
	echo -n "$(colorize 33 $(gettext 'Removing package:'))"
	colorize 36 " $PACKAGE $VERSION"
	log "$(gettext 'Removing package:') $PACKAGE $VERSION"
	separator
	
	gettext "Files to remove :"
	files="$(wc -l ${files_list} | cut -d ' ' -f 1)"
	char="$(echo $files | wc -L)"
	in=$((7 + ${char}))
	indent $(($(tty_size) - ${in})) "[ $(colorize 033 $files) ]"
	
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
