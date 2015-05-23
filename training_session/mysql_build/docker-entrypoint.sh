#!/bin/bash

set -e
MYSQL_ROOT_PASSWORD=secret

MYSQL_DATABASE=test
MYSQL_USER=test
MYSQL_PASSWORD=test

# read DATADIR from the MySQL config
DATADIR="/var/lib/mysql"

if [ ! -d "$DATADIR/mysql" ]; then
	if [ -z "$MYSQL_ROOT_PASSWORD" -a -z "$MYSQL_ALLOW_EMPTY_PASSWORD" ]; then
		echo >&2 'error: database is uninitialized and MYSQL_ROOT_PASSWORD not set'
		echo >&2 '  Did you forget to add -e MYSQL_ROOT_PASSWORD=... ?'
		exit 1
	fi
	
	echo 'Running mysql_install_db ...'
	chown -R mysql:mysql "$DATADIR"
	mysql_install_db --datadir="$DATADIR"
	echo 'Finished mysql_install_db'
	
	# These statements _must_ be on individual lines, and _must_ end with
	# semicolons (no line breaks or comments are permitted).
	# TODO proper SQL escaping on ALL the things D:
	
	tempSqlFile='/tmp/mysql-first-time.sql'
	cat > "$tempSqlFile" <<-EOSQL
		DELETE FROM mysql.user ;
		CREATE USER 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}' ;
		GRANT ALL ON *.* TO 'root'@'%' WITH GRANT OPTION ;
		DROP DATABASE IF EXISTS test ;
	EOSQL
	
	if [ "$MYSQL_DATABASE" ]; then
		echo "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` ;" >> "$tempSqlFile"
	fi
	
	if [ "$MYSQL_USER" -a "$MYSQL_PASSWORD" ]; then
		echo "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD' ;" >> "$tempSqlFile"
		
		if [ "$MYSQL_DATABASE" ]; then
			echo "GRANT ALL ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%' ;" >> "$tempSqlFile"
		fi
	fi
	
	echo 'FLUSH PRIVILEGES ;' >> "$tempSqlFile"
	
fi


mysqld --init-file="$tempSqlFile" &

sleep 12

time1=$(date +"%s")

cd /sql-bench
perl run-all-tests.sh --user test --pass test --server=MySQL --fast --small-tables --loop-count 1

time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "$diff\n" >> "/shared_volume/run_time_mysql"

