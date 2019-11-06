#!/bin/bash

/etc/init.d/mysql start

echo '[-] Waiting mysql start...'
while true
do
    curl localhost:3306 &>/dev/null && break
    sleep 1
done

if [ -f /root/db.sql ]; then
    mysql -uroot < /root/db.sql
    rm -rf /root/db.sql
fi

echo '[-] Waiting openrasp-iast start...'
while true
do
    curl openrasp-iast:25931 &>/dev/null && break
    sleep 1
done

/bin/bash /etc/init.d/apache2 start

while true
do
    curl localhost:80 &>/dev/null && break
done

echo '[-] apache start success!'

/bin/bash
