FROM php:7.2-apache

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

COPY sources.list /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y wget unzip libpng-dev mariadb-server curl netcat

RUN docker-php-source extract \
    && docker-php-ext-install mysqli gd pdo_mysql \
    && docker-php-source delete

COPY config/000-default.conf /etc/apache2/sites-available/000-default.conf
COPY config/ports.conf /etc/apache2/ports.conf

COPY config/php.ini /usr/local/etc/php/php.ini

# 安装OpenRASP 1.2
RUN cd /root && \
	wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-php-linux.tar.bz2 && \
	tar -jxf rasp-php-linux.tar.bz2 && \
    rm -rf rasp-php-linux.tar.bz2 && \
    mv rasp-php-* rasp-php && \
	cd rasp-php && \
    php install.php -d /opt/rasp \
        --app-id 6f00ed51e1b2c7a16dadd8aec673a9e8d91b8011 \
        --app-secret Z3cKrtbqZrqbpYICaBzObiZiOyFPPbvoLh75hyKpsgB \
        --backend-url http://rasp-cloud:8086 \
        --rasp-id 0000000000000001

RUN sed -i "s/openrasp.heartbeat_interval=180/openrasp.heartbeat_interval=10/" /usr/local/etc/php/conf.d/z_openrasp.ini

RUN cd /root && \
    wget https://packages.baidu.com/app/mutillidae-v2.7.11.zip -o v2.7.11.zip && \
    unzip v2.7.11.zip && \
    rm -rf v2.7.11.zip && \
    mv mutillidae* mutillidae

COPY mutillidae/.htaccess /root/mutillidae/.htaccess

COPY db.sql /root/db.sql

COPY start.sh /root/

ENTRYPOINT ["/bin/bash", "/root/start.sh"]