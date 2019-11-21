FROM debian:stretch-slim 

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

RUN apt-get update && \
    apt-get install -y wget curl procps

RUN cd /root/ && \
    wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-cloud.tar.gz && \
    tar -zxf rasp-cloud.tar.gz && \
    rm -rf rasp-cloud.tar.gz && \
    mv rasp-cloud-2* rasp-cloud

COPY app.conf /root/rasp-cloud/conf/app.conf

COPY rasp-cloud.sh /etc/init.d/rasp-cloud.sh

RUN chmod +x /etc/init.d/rasp-cloud.sh

COPY start.sh /root

ENTRYPOINT ["/bin/bash", "/root/start.sh"]
