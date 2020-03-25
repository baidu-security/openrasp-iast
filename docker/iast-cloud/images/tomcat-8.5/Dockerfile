FROM tomcat:8.5.49-jdk8-openjdk

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

COPY sources.list /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y wget unzip libpng-dev mariadb-server curl netcat

COPY config/server.xml /usr/local/tomcat/conf/

# 安装OpenRASP 1.2
RUN cd /root && \
	wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-java.zip && \
	unzip rasp-java.zip && \
    rm -rf rasp-java.zip && \
    mv rasp-2* rasp-java && \
	cd rasp-java && \
    java -jar RaspInstall.jar \
        -install /usr/local/tomcat \
        -heartbeat 10 \
        -appid 6f00ed51e1b2c7a16dadd8aec673a9e8d91b8011 \
        -appsecret Z3cKrtbqZrqbpYICaBzObiZiOyFPPbvoLh75hyKpsgB \
        -backendurl http://rasp-cloud:8086 \
        -raspid 0000000000000004 && \
    cd .. && \
    rm -rf rasp-java && \
    cd /usr/local/tomcat/webapps && \
    wget https://packages.baidu.com/app/openrasp/testcases/vulns.war

COPY db.sql /root/db.sql

COPY start.sh /root/

ENTRYPOINT ["/bin/bash", "/root/start.sh"]