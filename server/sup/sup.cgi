#!/bin/sh
#
# TinyCM/TazBug Plugin - SliTaz User Packages
#
# This plugin is part of the SPI tools and services. More information
# at http://hg.slitaz.org/sup/file/ && http://scn.slitaz.org/?d=en/sup
# packages.sql is a SQLite table with all mirrored packages info, just
# for the fun of playing witg SQLite :-)
#
# Copyright (C) 2017 SliTaz GNU/Linux - BSD License
# Author: Christophe Lincoln <pankso@slitaz.org>
#

# This script is called directly on upload: get httphelper.sh functions
# and set full path to move files
if [ "$(basename $0)" == "sup.cgi" ]; then
	. /lib/libtaz.sh
	. /usr/lib/slitaz/httphelper.sh
	. paths.conf
fi

# Custom paths.conf for easier development /avois commit this file 
# with wrong paths like Pankso does! Full paths are needed for upload
# to work properly.
[ -f "${plugins}/sup/paths.conf" ] && . ${plugins}/sup/paths.conf

supdb="$content/sup"
wok="$supdb/wok"
packages="$supdb/packages"
suplog="$cache/log/sup.log"
pkgsdb="$packages/packages.sql"

# Keep the highlighter minimal :-)
receip_highlighter() {
	sed	-e s'|&|\&amp;|g' -e 's|<|\&lt;|g' -e 's|>|\&gt;|'g \
		-e s"#^\#\([^']*\)#<span class='comment'>\0</span>#"g \
		-e s"#\"\([^']*\)\"#<span class='value'>\0</span>#"g
}

case " $(GET sup) " in

	*\ pkg\ *)
		pkg="$(GET name)"
		d="SUP: $pkg"
		header
		html_header
		user_box
		if ! . ${wok}/${pkg}/receip; then
			echo "Missing or corrupted receip" && exit 1
		fi

		cat << EOT
<h2>$(gettext "Package:") $PACKAGE $VERSION</h2>
<div id="tools">
	<a title="Right click to download link: $PACKAGE-$VERSION.sup"
		href='$packages/$PACKAGE-$VERSION.sup'>Download</a>
EOT
		# Tools for logged users
		if check_auth; then
			# Only package owner can update a package MAIL is set by check_auth
			if [ "$MAINTAINER" == "$MAIL" ]; then
				cat << EOT
	<a href="?sup=upload">$(gettext "Update package")</a>
EOT
			fi
		fi
		cat << EOT
	<a href='?sup'>SUP Hub</a>
</div>
<pre>
${SHORT_DESC}
</pre>

EOT
		# Get package maintainer/user info from SCN/SliTaz user DB
		if ! . $(fgrep -l "MAIL=\"${MAINTAINER}\"" ${PEOPLE}/*/account.conf); then
			USER="unknow"
		fi
		cat << EOT
<div>
	<a href="?user=$USER">$(get_gravatar $MAINTAINER 24)</a>
	$(gettext "Maintainer:") <a href="?user=$USER">$NAME</a> -
	$(gettext "Build date:") ${cook_date} -
	$(gettext "License:") $LICENSE
</div>
EOT
		# README
		if [ -f "${wok}/${pkg}/README" ]; then
			echo "<h3>README</h3>"
			echo "<pre>"
			cat ${wok}/${pkg}/README
			echo "</pre>"
		fi
		# Receip
		cat << EOT
<h3>$(gettext "Receip")</h3>
<pre>
$(cat ${wok}/${pkg}/receip | receip_highlighter)
</pre>
EOT
		html_footer && exit 0 ;;

	*\ upload\ *)
		# HTML Form: use cloud plugin CSS style
		header
		html_header
		user_box
		if ! check_auth; then
			header "Location: $HTTP_REFERER"
		fi
		d="SUP Upload"
		cat << EOT
<h2>${d}</h2>
<p>
	$(gettext "User:") <a href="?user=$user">$user</a> - Mail: $MAIL
</p>

<div id="cloud-upload">

	<form method="post"
		action="plugins/sup/sup.cgi?sup=supQA&amp;user=$user&amp;mail=$MAIL"
		enctype="multipart/form-data">
		<input type="file" name="supfile" size="150" />
		<input type="submit" value="Upload" />
	</form>

</div>
EOT
		html_footer && exit 0 ;;

	*\ supQA\ *)
		# SUP Upload Quality assurance. Check package in cache before
		# publishing. We need full path for upload to work ../../
		#
		# This is the geeky part for users, QA output in cmdline style
		# and to be transparent on what is going on :-)
		#
		header
		d="SUP Upload QA"
		supfile=$(FILE supfile name)
		tmpfile=$(FILE supfile tmpname)
		wok="$scn/content/sup/wok"
		packages="$scn/content/sup/packages"
		cache="$scn/cache/sup/${supfile%.sup}"
		pkgsdb="$scn/content/sup/packages/packages.sql"
		suplog="$scn/cache/log/sup.log"
		error=0

		# clean_error "Message"
		clean_error() {
			echo "<span class='error'>ERROR: ${1}</span>"
			[ -d "$cache" ] && rm -rf ${cache}
			[ -d "$(dirname $tmpfile)" ] && rm -rf $(dirname $tmpfile)
		}

		# Use COOKIE to make sure user is logged in SCN/SUP Hub
		user="$(echo $(COOKIE auth) | cut -d ':' -f 1)"
		if [ "$(COOKIE auth)" ] && [ "$user" != "$(GET user)" ]; then
			clean_error "user auth cookie"; exit 1
		fi

		# Is it a .sup file ?
		if [ "$supfile" != "${supfile%.sup}.sup" ]; then
			clean_error "not a .sup package: $supfile"; exit 1
		fi

		cat << EOT
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>$d</title>
	<link rel="stylesheet" type="text/css" href="${host}style.css" />
	<style type="text/css">body { margin: 40px 80px; }</style>
</head>
<body>
<h2>$d</h2>
<pre>
SUP Hub user   : <a href="${host}?user=$user">$user</a>
Package file   : ${supfile}
EOT
		# Server sanity Check
		if [ ! -f "$pkgsdb" ]; then
			clean_error "missing : $(basename $pkgsdb)"
			echo "</pre>" && exit 1
		fi

		mkdir -p ${cache}
		if ! mv -f ${tmpfile} ${cache}/${supfile}; then
			clean_error "moving: ${tmpfile} to ${supfile}"
			echo "</pre>" && exit 1
		fi

		# Show MD5sum
		echo -e "MD5sum         : $(md5sum $cache/$supfile | cut -d ' ' -f 1)\n"

		# Extract receip: sup cook already check vor empty var. Make
		# sure SCN user name match package MAINTAINER.
		gettext "Extracting receip..."
		cd ${cache}
		if ! cpio -i receip --quiet < ${supfile}; then
			echo ""
			clean_error "Can't extract receip"
			echo "</pre>" && exit 1
		fi; status

		if ! . receip; then
			clean_error "Can't source receip"
			echo "</pre>" && exit 1
		fi
		echo "Build date: <span class='float-right value'>$cook_date</span>"

		# README
		gettext "Checking for a README file..."
		cpio -i README --quiet < ${supfile}
		if [ -f "README" ]; then
			echo " <span class='float-right color32'>$(gettext 'yes')</span>"
		else
			echo " <span class='float-right value'>$(gettext 'no')</span>"
		fi

		# Logged user is maintainer ?
		if [ "$MAINTAINER" != "$(GET mail)" ]; then
			error=1
			echo -e "\n<span class='error'>WARNING: user mail not matching</span>"
			gettext "User mail  :"; echo " $(GET mail)"
			gettext "MAINTAINER :"; echo " $MAINTAINER"
		fi

		# Publish and display pkg url's if no error
		if [ "$error" == "0" ]; then
			gettext "Moving package to mirror..."
			mv -f ${supfile} ${packages}; status
			gettext "Moving receip to public wok..."
			mkdir -p ${wok}/${PACKAGE} && mv -f receip ${wok}/${PACKAGE}; status
			[ -f "README" ] && mv -f README ${wok}/${PACKAGE}

			# Handle packages.md5


			# Log activity date|user|mail|pkg|version|short_desc
			cat >> ${suplog} << EOT
$(date '+%Y-%m-%d %H:%M')|$user|$MAINTAINER|$PACKAGE|$VERSION|$SHORT_DESC
EOT
			echo "</pre><p>
Package page: <a href='${host}?sup=pkg&amp;name=$PACKAGE'>$PACKAGE $VERSION</a>"
		else
			echo "</pre>
<a href='${host}?sup=upload'>SUP Upload page</a>"
			# Show receip on error
			echo "<h2>receip</h2>"
			echo "<pre>"
			cat ${cache}/receip | receip_highlighter
			echo "</pre>"
		fi
		# HTML Footer
		echo "</p>
	</body>
</html>"
		rm -rf ${cache} $(dirname $tmpfile) && exit 0 ;;
	
	*\ dbsum\ *)
		# Used by client to check for newer packages.sql
		header "Content-Type: text/plain"
		md5sum ${pkgsdb} | awk '{printf $1}'; exit 0 ;;

	*\ admin\ *|*\ db\ *)
		. ${plugins}/sup/sup-admin.cgi ;;

	*\ sup\ *)
		d="SUP - SliTaz User Packages"
		header
		html_header
		user_box
		echo "<h2>${d}</h2>"
		# Tools for logged users and admins
		if check_auth; then
			if admin_user; then
				tools='<a href="?sup=admin">Admin tools</a>'
			fi
			cat << EOT
<div id="tools">
	<a href="?sup=upload">Upload package</a>
	$tools
</div>
EOT
		fi
		cat << EOT
<p>
	SliTaz User Packages hub: beta testing :-)
	- Packages: $(ls $wok | wc -l)
	- <a href="$packages/">Browse mirror</a>
	- <a href="http://scn.slitaz.org/index.cgi?d=en/sup">Documentation</a>
</p>

<h3>$(gettext "Latest uploads")</h3>
<pre>
EOT
		# Latest uploads from sup.log
		IFS="|"
		tac ${suplog} | head -n 6 | while read date user mail pkg version short_desc
		do
			cat << EOT
<a href="?user=$user">$(get_gravatar $mail 20)</a> \
<span class="date">$(echo $date | cut -d " " -f 1)</span> \
<a href="?sup=pkg&amp;name=$pkg">$pkg $version</a> - \
$(echo ${short_desc} | cut -c 1-34)...
EOT
		done
		unset IFS
		echo "</pre>"

		# Packages listing: if one day, too much packages, then this should
		# move to ?sup=list
		cat << EOT
<h3>$(gettext "SUP packages")</h3>
<div id="plugins">
<table>
	<thead>
		<td>$(gettext "Package name")</td>
		<td>$(gettext "Version")</td>
		<td>$(gettext "Short description")</td>
	</thead>
EOT
		for pkg in $(ls $wok); do
		. ${wok}/${pkg}/receip
		cat << EOT
	<tr>
		<td><a href='?sup=pkg&amp;name=$pkg'>$pkg</a></td>
		<td>$VERSION</td>
		<td>$SHORT_DESC</td>
	</tr>
EOT
		done
		echo "</table></div>"
		html_footer && exit 0 ;;

esac
