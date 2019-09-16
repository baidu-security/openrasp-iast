#!/bin/bash

case "$1" in
    start)
		echo '[-] Starting MySQL'
		chmod 777 -R /mysql_database/
		nohup mysqld_safe --datadir=/mysql_database/ &>/dev/null &

		echo '[-] Waiting for MySQL to start ...'
		while true
		do
			mysql -uroot -e 'select 1' &>/dev/null && break
			sleep 1
		done

        echo '[-] MySQL started !'
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
