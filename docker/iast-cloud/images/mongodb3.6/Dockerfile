FROM mongo:3.6-stretch

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

COPY mongod.conf /etc/mongod.conf

COPY mongodb.sh /etc/init.d/
RUN chmod +x /etc/init.d/mongodb.sh

COPY openrasp_data /root/openrasp_data
COPY start.sh /root/start.sh

ENTRYPOINT ["/bin/bash", "/root/start.sh"]