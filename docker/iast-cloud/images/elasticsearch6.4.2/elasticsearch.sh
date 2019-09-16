#!/bin/bash

case "$1" in
    start)
        echo '[-] Starting elasticsearch'
        su elasticsearch -c "elasticsearch -d"
    ;;
    stop)
        echo '[-] Stopping elasticsearch'
        ES_ID=`ps -ef |grep elastic |grep java |awk '{print $2}'`
        kill "$ES_ID"
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