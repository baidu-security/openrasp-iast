#!/bin/sh

case "$1" in
    start)
        echo '[-] Starting rasp-cloud'
        echo '[-] Waiting for Mongodb to start'
        while true
        do
            curl mongodb3.6:27017 &>/dev/null && break
            sleep 1
        done
        sleep 1
        echo '[-] Waiting for elasticsearch to start'
        while true
        do
            curl -I elasticsearch6.4.2:9200 &>/dev/null && break
            sleep 1
        done
        /root/rasp-cloud/rasp-cloud -d
        echo '[-] rasp-cloud start success'
    ;;
    stop)
        echo '[-] Stopping rasp-cloud'
        killall rasp-cloud
    ;;
    restart)
        $0 stop
        $0 start
    ;;
    *)
        echo Unknown action: $1
    ;;

esac