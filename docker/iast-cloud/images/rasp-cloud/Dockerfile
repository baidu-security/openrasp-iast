FROM debian:stretch-slim 

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

RUN apt-get update && \
    apt-get install -y wget curl

RUN cd /root/ && \
    wget https://packages.baidu.com/app/openrasp/release/1.2.0/rasp-cloud.tar.gz && \
    tar -zxf rasp-cloud.tar.gz && \
    rm -rf rasp-cloud.tar.gz && \
    mv rasp-cloud-2* rasp-cloud

COPY app.conf /root/rasp-cloud/conf/app.conf

COPY rasp-cloud.sh /etc/init.d/rasp-cloud.sh

COPY start.sh /root

ENTRYPOINT ["/bin/bash", "/root/start.sh"]