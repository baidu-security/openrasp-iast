#!/bin/bash

cp /usr/local/etc/php/php.ini-development /usr/local/etc/php/php.ini

echo '[-] Waiting rasp-cloud'
    while true
    do
        curl rasp-cloud:8086 &>/dev/null && break
        sleep 1
    done

/bin/bash /etc/init.d/apache2 start

curl localhost &>/dev/null && echo '[-] apache start success!'

/bin/bash
