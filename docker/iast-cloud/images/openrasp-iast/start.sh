#!/bin/bash

echo '[-] Waiting for mysql start'
while true
do
    nc -z mysql5.6 3306 && break
    sleep 1
done

echo '[-] Waiting for rasp-cloud start'
while true
do
    curl -I rasp-cloud:8086 &>/dev/null && break
    sleep 1
done

echo '[-] starting OpenRASP-IAST ...'
if [ -f /testfiles/test ]; then
    python3 /root/openrasp-iast-code/main.py start -c /root/openrasp-iast/test-config.yaml
else
    python3 /root/openrasp-iast-code/main.py start
fi
echo '[-] OpenRASP-IAST started'

/bin/bash