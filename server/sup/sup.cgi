#!/bin/sh
#
# TinyCM/TazBug Plugin - SliTaz User Packages
#
# This plugin is part of the SPI tools and services. More information
# at http://hg.slitaz.org/sup/file/ && http://scn.slitaz.org/?d=en/sup
#
# Copyright (C) 2017 SliTaz GNU/Linux - BSD License
# Author: Christophe Lincoln <pankso@slitaz.org>
#

case " $(GET sup) " in
	
	*\ pkg\ *)
		pkg="$(GET name)"
		supdb="$content/sup"
		wok="$supdb/wok"
		d="Sup package: $pkg"
		header
		html_header
		user_box
		
		cat << EOT
<h2>${d}</h2>
<div id="tools">
	<a href='?sup'>Sup hub</a>
EOT
		if check_auth; then
			cat << EOT
	<a href='?sup=debug'>Sup debug</a>
EOT
		fi
		#. ${wok}/${pkg}/receip
		cat << EOT
</div>

<pre>
$(cat ${wok}/${pkg}/receip )
</pre>
EOT
		
		html_footer && exit 0 ;;

	*\ debug\ *)
		d="Sup server debug"
		header
		html_header
		user_box
		cat << EOT
<h2>${d}</h2>
<div id="tools">
	<a href='?sup'>Sup hub</a>
</div>
EOT
		if ! check_auth; then
			echo "Only for logged users" && html_footer && exit 0
		fi
		echo "<pre>"
		echo "Checking: $content/sup/wok"
		for pkg in $(ls $content/sup/wok); do
			echo "$pkg"
		done
		echo "</pre>"
		html_footer && exit 0 ;;
	
	*\ sup\ *)
		d="SliTaz User Packages"
		supdb="$content/sup"
		wok="$supdb/wok"
		header
		html_header
		user_box
		cat << EOT
<h2>${d}</h2>
<p>
	SliTaz User Packages server services. In developement :-)
</p>

<pre>
Packages : $(ls $wok | wc -l)
Mirror   : <a href="$content/sup/packages/">Browse packages</a>
Tools    : <a href="?sup=debug">Debug page</a>
</pre>
EOT
		# Packages list
		echo "<h3>Sup packages</h3>"
		echo "<pre>"
		for pkg in $(ls $content/sup/wok); do
			echo "<a href='?sup=pkg&amp;name=$pkg'>$pkg</a>"
		done
		echo "</pre>"
		html_footer && exit 0 ;;
		
esac
