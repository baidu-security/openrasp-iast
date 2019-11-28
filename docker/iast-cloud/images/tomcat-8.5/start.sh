#!/bin/bash

/etc/init.d/mysql start

echo '[-] Waiting mysql start...'
while true
do
    nc -z mysql5.6 3306 && break
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

/usr/local/tomcat/bin/startup.sh

while true
do
    sleep 1
    curl localhost:18663 &>/dev/null && break
done

echo '[-] tomcat start success!'

/bin/bash
