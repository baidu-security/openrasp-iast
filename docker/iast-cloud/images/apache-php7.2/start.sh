#!/bin/bash

cp /usr/local/etc/php/php.ini-development /usr/local/etc/php/php.ini

echo '[-] Waiting openrasp-iast start...'
while true
do
    curl openrasp-iast:25931 &>/dev/null && break
    sleep 1
done

/bin/bash /etc/init.d/apache2 start

curl localhost &>/dev/null && echo '[-] apache start success!'

/bin/bash
