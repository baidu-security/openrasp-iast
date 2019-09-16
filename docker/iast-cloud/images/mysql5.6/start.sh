#!/bin/bash

/etc/init.d/mysql.sh start

if [ -f /root/db.sql ]; then
      mysql -u root < /root/db.sql
      rm -rf /root/db.sql
fi

/bin/bash
