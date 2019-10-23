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

import json
import socket
import requests
from lxml import etree

from testtools import iast_api


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
        proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
        r = self.session.post(url=url, data=data, headers=headers, proxies=proxies, allow_redirects=False)
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

        path = "/SqlInjection/attack5"
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

        path = "/SqlInjection/attack6b"
        data = {
            "userid_6b": "123456"
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

    def _craw_ssrf(self):
        path = "/SSRF/task1"
        data = {
            "url": "images/tom.png"
        }
        self._post(path, data)

        path = "/SSRF/task2"
        data = {
            "url": "images/cat.png"
        }
        self._post(path, data)

    def crawl(self):
        self._login()
        self._craw_sqli_intro()
        self._craw_sqli_adv()
        self._craw_xxe()
        self._craw_xss_r()
        self._craw_xss_s()
        self._craw_ssrf()


def run():
    # ip = socket.gethostbyname("webgoat")
    ip = "127.0.0.1"
    wgc = WebGoatCrawler("http://{}:8444/WebGoat".format(ip))
    print("Crawling WebGoat...")
    wgc.crawl()
    print("WebGoat crawling complete...")
