#!/bin/bash

/bin/bash /etc/init.d/mongodb.sh start

if [ -d "/root/openrasp_data" ]; then
    mongorestore -h localhost -d openrasp --drop /root/openrasp_data
    rm -rf /root/openrasp_data
fi

/bin/bash
