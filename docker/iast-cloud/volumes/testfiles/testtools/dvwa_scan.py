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
from lxml import etree

from testtools import iast_api

dvwa_port = 18662


class DvwaCrawler(object):

    def __init__(self, url):
        self.base_url = url
        self.session = requests.Session()
        requests.utils.add_dict_to_cookiejar(
            self.session.cookies,
            {"security": "low"}
        )

    def _get(self, path):
        url = self.base_url + path
        r = self.session.get(url=url, allow_redirects=False)
        return r

    def _post(self, path, data):
        url = self.base_url + path
        r = self.session.post(url=url, data=data, allow_redirects=False)
        return r

    def _post_files(self, path, data, files):
        url = self.base_url + path
        r = self.session.post(url=url, data=data, files=files, allow_redirects=False)
        return r

    def _login(self):
        path = "/login.php"
        text = self._get(path).text
        html = etree.fromstring(text, etree.HTMLParser())
        user_token = html.xpath("//input[@name='user_token']/@value")[0]
        data = {
            "username": "admin",
            "password": "password",
            "Login": "Login",
            "user_token": user_token
        }
        r = self._post(path, data)
        assert r.headers["Location"] == "index.php"

    def _craw_exec(self):
        path = "/vulnerabilities/exec/"
        data = {
            "ip": "127.0.0.1",
            "Submit": "Submit"
        }
        r = self._post(path, data)

    def _craw_lfi(self):
        path = "/vulnerabilities/fi/?page=file1.php"
        self._get(path)

    def _craw_upfile(self):
        path = "/vulnerabilities/upload/"
        files = {'uploaded': ('upload.txt', 'some data', "text/plain")}
        data = {
            "Upload": "Upload"
        }
        self._post_files(path, data, files)

    def _craw_sqli(self):
        path = "/vulnerabilities/sqli/?id=2&Submit=Submit"
        self._get(path)
        path = "/vulnerabilities/sqli_blind/?id=1&Submit=Submit"
        self._get(path)

    def _craw_xss_r(self):
        path = "/vulnerabilities/xss_r/?name=world"
        self._get(path)

    def _craw_xss_s(self):
        path = "/vulnerabilities/xss_s/"
        data = {
            "txtName": "hi",
            "mtxMessage": "mes",
            "btnSign": "Sign+Guestbook"
        }
        self._post(path, data)

    def crawl(self):
        self._login()
        for method in self.__dir__():
            if method.startswith("_craw_"):
                getattr(self, method)()


def _get_result(host):
    sql = "select rasp_result_list from openrasp.`{}_{}_Report`".format(host, dvwa_port)
    result = iast_api._query(sql)
    vul_url_list = []
    for item in result:
        item_data = json.loads(item[0])[0]
        url = item_data["context"]["url"]
        vul_url_list.append(url)

    known_vuln_url = [
        '/DVWA-1.9/vulnerabilities/exec/',
        '/DVWA-1.9/vulnerabilities/upload/',
        "/DVWA-1.9/vulnerabilities/sqli/",
        "/DVWA-1.9/vulnerabilities/sqli_blind/",
        "/DVWA-1.9/vulnerabilities/fi/",
        "/DVWA-1.9/vulnerabilities/xss_r/",
        "/DVWA-1.9/vulnerabilities/xss_s/",
    ]

    result = ["测试用例,检测结果"]

    for vuln_url in known_vuln_url:
        item = [vuln_url, "漏报"]
        for url in vul_url_list:
            if url.find(vuln_url) != -1:
                item[1] = "OK"
                break
        result.append(",".join(item))

    with open("./result/dvwa_result.csv", "w") as f:
        f.write("\n".join(result))

    print("DVWA scan result is generated to {}/result/dvwa_result.csv".format(os.getcwd()))


def run():
    print("Starting test DVWA...")
    ip = socket.gethostbyname("apache-php7.2")
    dc = DvwaCrawler("http://{}:{}/DVWA-1.9".format(ip, dvwa_port))
    print("Crawling DVWA...")
    dc.crawl()
    print("DVWA crawling complete...")
    host = iast_api.run_task(dvwa_port, 5)
    _get_result(host)
