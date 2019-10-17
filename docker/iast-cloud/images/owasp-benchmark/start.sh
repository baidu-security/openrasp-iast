#!/bin/bash

echo '[-] Waiting openrasp-iast start...'
while true
do
    curl openrasp-iast:25931 &>/dev/null && break
    sleep 1
done

cd /owasp/benchmark
chmod +x runRemoteAccessibleBenchmark.sh
nohup ./runRemoteAccessibleBenchmark.sh &> /dev/null &

if [ -f /testfiles/test ]; then

    echo '[-] Waiting benchmark accessable...'
    while true
    do
        curl -k -I https://owasp-benchmark:8443/benchmark/ &>/dev/null && break
        sleep 1
    done

    cp expectedresults*.csv /testfiles/benchmark-expected.csv 

    echo '[-] Start benchmark crawler...'
    chmod +x runCrawler.sh
    ./runCrawler.sh
    echo '[-] Finish benchmark crawler...'

fi

/bin/bash

