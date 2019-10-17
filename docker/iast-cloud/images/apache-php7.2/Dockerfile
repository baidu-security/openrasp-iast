FROM php:7.2-apache

LABEL MAINTAINER "OpenRASP <ext_yunfenxi@baidu.com>"

ARG RASP_VERSION

RUN apt-get update && \
    apt-get install -y wget

RUN docker-php-source extract \
    && docker-php-ext-install mysqli \
    && docker-php-source delete

COPY config/000-default.conf /etc/apache2/sites-available/000-default.conf
COPY config/ports.conf /etc/apache2/ports.conf

# 安装OpenRASP 1.2
RUN cd /root && \
	wget https://packages.baidu.com/app/openrasp/release/${RASP_VERSION}/rasp-php-linux.tar.bz2 && \
	tar -jxf rasp-php-linux.tar.bz2 && \
    rm -rf rasp-php-linux.tar.bz2 && \
    mv rasp-php-* rasp-php && \
	cd rasp-php && \
    php install.php -d /opt/rasp \
        --app-id 192d1cb737394b74b640dc9de66fc7b0b49e1423 \
        --app-secret HUL1Z0zy1BuSFOWI2lHWqzzZ2Yrq12DJDeyHFDxcEAk \
        --backend-url http://rasp-cloud:8086

RUN sed -i "s/openrasp.heartbeat_interval=180/openrasp.heartbeat_interval=10/" /usr/local/etc/php/conf.d/z_openrasp.ini

COPY start.sh /root/

ENTRYPOINT ["/bin/bash", "/root/start.sh"]