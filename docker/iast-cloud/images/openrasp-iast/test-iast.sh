#!/bin/bash


echo "OpenRASP-IAST vuln test start!"


echo '[-] Waiting apache accessable...'
while true
do
    curl apache-php7.2:18662 &>/dev/null && break
    sleep 1
done

echo '[-] Waiting benchmark accessable...'
while true
do
    curl -k -I https://owasp-benchmark:8443/benchmark/ &>/dev/null && break
    sleep 1
done

python3 /testfiles/run-test.py

echo "OpenRASP-IAST test finish!"
