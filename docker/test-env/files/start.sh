#!/bin/bash

/etc/init.d/httpd.sh start
/etc/init.d/mysql.sh start

echo '[-] Accessing 127.0.0.1 for the first time'
curl 127.0.0.1 &>/dev/null
echo "OK, test env start success!"

if [ $# == 0 ]
then
    cd /code && make clean && cd openrasp_iast && pytest3 --cov=./ --cov-report=html test/
else
    bash -c "$1"
fi