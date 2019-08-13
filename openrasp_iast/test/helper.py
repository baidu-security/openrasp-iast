#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Copyright 2017-2019 Baidu Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import time
import pymysql
import requests

db_config = {
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "",
    "db_name": "ori"
}

def _query(sql):
    conn = pymysql.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["username"],
        passwd=db_config["password"]
    )
    cursor = conn.cursor()
    cursor._defer_warnings = True
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result

def reset_db():
    sql = "DROP DATABASE IF EXISTS `{}`;".format(db_config["db_name"])
    _query(sql)

def get_data_count(table_name):
    sql = "SELECT count(*) FROM `{}`.`{}`;".format(db_config["db_name"], table_name)
    result = _query(sql)
    return result[0][0]

def clean_table(table_name):
    sql = "TRUNCATE TABLE `{}`.`{}`".format(db_config["db_name"], table_name)
    _query(sql)

def execute_sql(sql):
    result = _query(sql)

class HttpSender(object):

    def __init__(self, host, port):
        self.url = "http://{host}:{port}".format(host=host, port=port)

    def send_json(self, json, path):
        url = self.url + path
        r = requests.post(url=url, json=json)
        return r

    def send_data(self, data, path):
        url = self.url + path
        r = requests.post(url=url, data=data)
        return r

    def test_connect(self, path):
        url = self.url + path
        for i in range(10):
            try:
                r = requests.get(url=url)
                return r
            except Exception:
                time.sleep(0.5)
        return False