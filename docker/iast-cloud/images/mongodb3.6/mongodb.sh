#!/bin/bash

case "$1" in
    start)
        echo '[-] Starting mongodb'
        mongod --fork -f /etc/mongod.conf --logpath /root/mongod.log
    ;;
    stop)
        echo '[-] Stopping mongodb'
        kill -15 $(pidof mongod)
    ;;
    restart)
		$0 stop
        sleep 1
		$0 start
	;;
    *)
		echo Unknown action: $1
	;;

esac
