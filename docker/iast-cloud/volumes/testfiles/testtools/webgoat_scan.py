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

import os
import json
import socket
import requests

from testtools import iast_api

webgoat_port = 8444


class WebGoatCrawler(object):

    def __init__(self, url):
        self.base_url = url
        self.session = requests.Session()

    def _get(self, path):
        url = self.base_url + path
        r = self.session.get(url=url, allow_redirects=False)
        return r

    def _post(self, path, data, headers={}):
        url = self.base_url + path
        r = self.session.post(url=url, data=data, headers=headers, allow_redirects=False)
        return r

    def _put(self, path, data):
        url = self.base_url + path
        r = self.session.put(url=url, data=data, allow_redirects=False)
        return r

    def _post_files(self, path, data, files):
        url = self.base_url + path
        r = self.session.post(url=url, data=data, files=files, allow_redirects=False)
        return r

    def _register(self):
        path = "/register.mvc"
        data = {
            "username": "admin123",
            "password": "admin123",
            "matchingPassword": "admin123",
            "agree": "agree"
        }
        text = self._post(path, data)

    def _login(self):
        self._register()
        path = "/login"
        data = {
            "username": "admin123",
            "password": "admin123"
        }
        r = self._post(path, data)
        assert r.headers["Location"].endswith("welcome.mvc")

    def _craw_sqli_intro(self):
        path = "/SqlInjection/attack2"
        data = {
            "query": "select department from employees where userid= 96134"
        }
        self._post(path, data)

        path = "/SqlInjection/attack3"
        self._post(path, data)

        path = "/SqlInjection/attack4"
        self._post(path, data)

        path = "/SqlInjection/assignment5a"
        data = {
            "account": "Smith",
            "operator": "or",
            "injection": "1 = 1"
        }
        self._post(path, data)

        path = "/SqlInjection/assignment5b"
        data = {
            "login_count": "1",
            "userid": "2",
        }
        self._post(path, data)

        path = "/SqlInjection/attack8"
        data = {
            "name": "lastname",
            "auth_tan": "tan"
        }
        self._post(path, data)

        path = "/SqlInjection/attack9"
        data = {
            "name": "lastname",
            "auth_tan": "tan"
        }
        self._post(path, data)

        path = "/SqlInjection/attack10"
        data = {
            "action_string": "abc123"
        }
        self._post(path, data)

    def _craw_sqli_adv(self):
        path = "/SqlInjection/attack6a"
        data = {
            "userid_6a": "basename"
        }
        self._post(path, data)

        path = "/SqlInjection/challenge"
        data = {
            "username_reg": "admin",
            "email_reg": "abc@123.com",
            "password_reg": "123456",
            "confirm_password_reg": "123456"
        }
        self._put(path, data)

    def _craw_xxe(self):
        path = "/xxe/simple"
        headers = {'Content-Type': 'application/xml'}
        data = '<?xml version="1.0"?><comment><text>123</text></comment>'
        self._post(path, data, headers)

        path = "/xxe/blind"
        headers = {'Content-Type': 'application/xml'}
        data = '<?xml version="1.0"?><comment><text>123</text></comment>'
        self._post(path, data, headers)

    def _craw_xss_r(self):
        path = "/CrossSiteScripting/attack5a?QTY1=1&QTY2=1&QTY3=1&QTY4=12&field1=4128+3214+0002+1999&field2=111"
        self._get(path)

    def _craw_xss_s(self):
        path = "/CrossSiteScripting/stored-xss"
        headers = {'Content-Type': 'application/json'}
        data = '{"text":"xsss"}'
        self._post(path, data, headers)

    def crawl(self):
        self._login()
        for method in self.__dir__():
            if method.startswith("_craw_"):
                getattr(self, method)()


def _get_result(host):
    sql = "select rasp_result_list from openrasp.`{}_{}_Report`".format(host, webgoat_port)
    result = iast_api._query(sql)
    vul_url_list = []
    for item in result:
        item_data = json.loads(item[0])[0]
        url = item_data["context"]["url"]
        vul_url_list.append(url)

    known_vuln_url = [
        "/WebGoat/SqlInjection/attack2",
        "/WebGoat/SqlInjection/attack3",
        "/WebGoat/SqlInjection/attack4",
        "/WebGoat/SqlInjection/attack6a",
        "/WebGoat/SqlInjection/attack8",
        "/WebGoat/SqlInjection/attack9",
        "/WebGoat/SqlInjection/attack10",
        "/WebGoat/SqlInjection/assignment5a",
        "/WebGoat/SqlInjection/assignment5b",
        "/WebGoat/SqlInjection/challenge",
        "/WebGoat/xxe/simple",
        "/WebGoat/xxe/blind",
        "/WebGoat/CrossSiteScripting/attack5a"
        "/WebGoat/CrossSiteScripting/stored-xss"
    ]

    result = ["测试用例,检测结果"]

    for vuln_url in known_vuln_url:
        item = [vuln_url, "漏报"]
        for url in vul_url_list:
            if url.find(vuln_url) != -1:
                item[1] = "OK"
                break
        result.append(",".join(item))

    with open("./result/webgoat_result.csv", "w") as f:
        f.write("\n".join(result))

    print("webgoat scan result is generated to {}/result/webgoat_result.csv".format(os.getcwd()))


def run():
    print("Starting test WebGoat...")
    ip = socket.gethostbyname("webgoat")
    wgc = WebGoatCrawler("http://{}:{}/WebGoat".format(ip, webgoat_port))
    print("Crawling WebGoat...")
    wgc.crawl()
    print("WebGoat crawling complete...")
    host = iast_api.run_task(webgoat_port, 5)
    _get_result(host)
