#!/bin/bash

case "$1" in
    start)
		echo '[-] Starting MySQL'

		# MySQL 5.6，创建下 general log 文件
		if [[ -e /var/run/mysqld ]]; then
			touch /var/log/mysql-query.log
    	    chown -R mysql:mysql /var/lib/mysql /var/run/mysqld /var/log/mysql*
    	else
    		chown -R mysql:mysql /var/lib/mysql /var/log/mariadb
    	fi

		nohup mysqld_safe --datadir=/var/lib/mysql &>/dev/null &

		echo '[-] Waiting for MySQL to start ...'
		while true
		do
			mysql -uroot -e 'select 1' &>/dev/null && break
			sleep 1
		done
    ;;
    stop)
		echo '[-] Stopping MySQL'
        killall -9 mysqld
    ;;
    restart)
		$0 stop
		$0 start
	;;
    *)
		echo Unknown action: $1
	;;

esac
