#!/bin/sh
#
# TinyCM/TazBug Plugin - Admin part splitted so less code sourced by
# TinyCM core spript. echo ENGLISH Only :-). Admin tools: handle SQLite
# packages.md5 for the mirror, clean any unconform, buggy or corrupted 
# packages in wok.
#
# Copyright (C) 2017 SliTaz GNU/Linux - BSD License
# Author: Christophe Lincoln <pankso@slitaz.org>
#
. /lib/libtaz.sh

case " $(GET sup) " in

	*\ admin\ *)
		d="SUP Admin tools"
		header
		html_header
		user_box
		if ! check_auth && admin_user; then
			echo "Only for admins"; html_footer; exit 0
		fi
		cat << EOT
<h2>${d}</h2>
<div id="tools">
	<a href="?sup">SUP Hub</a>
	<a href='?sup=db&amp;command=create'>Create SQL db</a>
	<a href="?sup=db&amp;command=testsuite">SQL Testsuite</a>
</div>

<h3>SQL Packages db</h3>
<pre>
EOT
		# SQLite commands for ?sup=db&sqlite=command
		if [ -f "$pkgsdb" ]; then
			cat << EOT			
SQLite version   : $(sqlite3 -version | cut -d " " -f 1)
Database tables  : $(sqlite3 ${pkgsdb} '.tables')
Database size    : $(du -mh ${pkgsdb} | cut -d "	" -f 1)
EOT
			sqlite3 ${pkgsdb} 'SELECT timestamp FROM info' \
				| awk '{printf "Timestamp        : %s %s\n",$1,$2 }'
			echo "</pre>"
		else
			echo "WARNING: missing : $pkgsdb"
		fi
		
		# Check/admin wok: remove packagage
		#
		echo "<h3>Public wok</h3>"
		echo "<pre>"
		echo "Wok path     : $wok"
		echo "Wok size     : $(du -smh $wok | cut -d "	" -f 1)"
		echo "Packages     : $(ls $wok | wc -l)"
		echo "README files : $(find ${wok} -name README -type f | wc -l)"
		
		#${wok}/${pkg}/receip
		#for pkg in $(ls $wok); do
			#echo "$pkg"
		#done
		echo "</pre>"
		
		html_footer && exit 0 ;;
	
	*\ db\ *)
		d="SUP packages.sql"
		command=$(GET command)
		header
		html_header
		user_box
		if ! check_auth && admin_user; then
			echo "Only for admins"; html_footer; exit 0
		fi
		
		# Tools
		cat << EOT
<h2>${d}</h2>
<div id="tools">
	<a href="?sup=admin">Admin tools</a>
	<a href="?sup=db&amp;command=testsuite">SQL Testsuite</a>
</div>
EOT
		
		# Used by command=create
		create_pkgs_table() {
			sqlite3 ${pkgsdb} << EOT
CREATE TABLE pkgs(
	name PRIMARY KEY,
	version,
	short_desc,
	maintainer,
	license,
	website,
	sup_deps,
	depends,
	cook_date,
	md5sum UNIQUE
);
EOT
		}
		create_info_table() {
			sqlite3 ${pkgsdb} << EOT
CREATE TABLE info(
	timestamp PRIMARY KEY,
	pkgs_nb
);
EOT
		}
		
		# Handle SQlite commands
		[ "$command" ] && echo "<h3>Command: ${command}</h3>"
		case "$command" in
		
			create)
				timestart="$(date -u +%s)"
				rm -f ${pkgsdb}
				echo "<pre>"
				echo -n "Creating pkgs table..."
				create_pkgs_table; status
				echo -n "Creating info table..."
				create_info_table; status
				
				for pkg in $(ls $wok)
				do
					. ${wok}/${pkg}/receip
					# Faster ? | awk '{printf $1}'
					sum=$(md5sum ${packages}/${PACKAGE}-${VERSION}.sup | cut -d " " -f 1)
					echo -n "Inserting: $PACKAGE $VERSION"
					sqlite3 ${pkgsdb} << EOT
INSERT INTO pkgs VALUES(
	"$PACKAGE",
	"$VERSION",
	"$SHORT_DESC",
	"$MAINTAINER",
	"$LICENSE",
	"$WEB_SITE",
	"$SUP_DEPS",
	"$DEPENDS",
	"$cook_date",
	"$sum"
);
EOT
					status
				done
				
				timestamp="$(date "+%Y-%m-%d %H:%M")"
				pkgs_nb=$(ls $wok | wc -l)
				sqlite3 ${pkgsdb} << EOT
INSERT INTO info VALUES("$timestamp", "$pkgs_nb");
EOT
				gentime=$(( $(date -u +%s) - ${timestart} ))
				echo "Database generated in: \
<span class='float-right value'>$gentime sec</span>"
				echo "</pre>" ;;
			
			testsuite)
				# SUP SQLite commands testsuite
				echo "<pre>"
				
				echo "Running: <span class='value'>SELECT name FROM pkgs LIMIT 4</span>"
				sqlite3 ${pkgsdb} 'SELECT name FROM pkgs LIMIT 4' && newline
				
				# .schema
				echo "<span class='value'>CREATE statements</span>"
				echo "-----------------"
				sqlite3 ${pkgsdb} '.schema'; newline
				
				echo "</pre>" ;;
				
			*) echo "<pre>Unknow or command not implemented</pre>" ;;
			
		esac
	
		echo "<pre>"
		if [ -f "$pkgsdb" ]; then
			echo -n "SQLite version : "; sqlite3 -version | cut -d " " -f 1
			echo -n "Database size  : "; du -mh ${pkgsdb} | cut -d "	" -f 1
		else
			echo "<span class='error'>WARNING: missing : $pkgsdb</span>"
		fi
		echo "</pre>"
		
		html_footer && exit 0 ;;
esac
