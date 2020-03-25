FROM openjdk:8-stretch

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

COPY sources.list /etc/apt/sources.list

RUN apt-get update && apt-get clean

RUN mkdir -p /usr/share/man/man1

RUN apt-get install -q -y \
     openjdk-8-jre-headless \
     openjdk-8-jdk \
     git \
     maven \
     wget \
     iputils-ping \
     curl \
     && apt-get clean

WORKDIR /root
RUN wget https://packages.baidu.com/app/Benchmark-master.zip && \
    unzip Benchmark-master.zip && \
    rm -rf Benchmark-master.zip && \
    mkdir /owasp && \
    mv Benchmark-master /owasp/benchmark

COPY settings.xml /root/.m2/settings.xml

WORKDIR /owasp/benchmark
RUN sed -i 's/<cargo.servlet.port>8443<\/cargo.servlet.port>/<cargo.jvmargs>-javaagent:\/root\/rasp-java\/rasp\/rasp.jar<\/cargo.jvmargs><cargo.servlet.port>8443<\/cargo.servlet.port>/' pom.xml
RUN sed -i 's/http:\/\/archive.apache.org\/dist\/tomcat\/tomcat-${tomcat.major.version}\/v${version.tomcat}\/bin\/apache-tomcat-${version.tomcat}.zip/https:\/\/packages.baidu.com\/app\/apache-tomcat-8\/apache-tomcat-8.5.4.zip/' pom.xml
RUN mvn clean package cargo:install

WORKDIR /root/
RUN wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-java.zip && \
    unzip rasp-java.zip && \
    rm -rf rasp-java.zip && \
    mv rasp-2* rasp-java

COPY config/openrasp.yml /root/rasp-java/rasp/conf/openrasp.yml

COPY start.sh /root

ENTRYPOINT ["/bin/bash", "/root/start.sh"]