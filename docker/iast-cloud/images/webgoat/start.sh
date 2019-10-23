#!/bin/bash

echo '[-] Waiting openrasp-iast start...'
while true
do
    curl openrasp-iast:25931 &>/dev/null && break
    sleep 1
done


nohup java --add-opens java.base/jdk.internal.loader=ALL-UNNAMED \
      -javaagent:"/root/rasp-java/rasp/rasp.jar" \
      -Djava.security.egd=file:/dev/./urandom \
      -jar /home/webgoat/webgoat.jar \
      --server.port=8444 \
      --server.address=0.0.0.0 \
      >& /dev/null &

/bin/bash

