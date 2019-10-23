FROM webgoat/webgoat-8.0

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

USER root

RUN rm -rf /var/lib/apt/lists/* && apt-get update && apt-get clean

RUN apt-get install -y wget procps curl

WORKDIR /root/
RUN wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-java.zip && \
    unzip rasp-java.zip && \
    rm -rf rasp-java.zip && \
    mv rasp-2* rasp-java

COPY config/openrasp.yml /root/rasp-java/rasp/conf/openrasp.yml

COPY start.sh /root/

ENTRYPOINT ["/bin/bash", "/root/start.sh"]