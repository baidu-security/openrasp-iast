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

vulns_port = 18662


class VulnsCrawler(object):

    def __init__(self, url):
        self.base_url = url
        self.session = requests.Session()

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

    def _craw_dir(self):
        path = "/001-dir.php?dir=/proc/"
        self._get(path)

    def _craw_file_read(self):
        path = "/002-file-read.php?file=/etc/hosts"
        self._get(path)

    def _craw_cmd_1(self):
        path = "/004-command-1.php?cmd=cp /etc/passwd /tmp/"
        self._get(path)

    def _craw_cmd_2(self):
        path = "/004-command-2.php?cmd=cat /etc/resolv.conf"
        self._get(path)

    def _craw_file_write(self):
        path = "/005-file-write.php"
        data = {
            "name": "user.txt",
            "data": "123"
        }
        self._post(path, data)

    def _craw_file_upload(self):
        path = "/008-file-upload.php"
        files = {'file': ('upload.txt', 'some data', "text/plain")}
        data = {}
        self._post_files(path, data, files)

    def _craw_sqli(self):
        path = "/vulnerabilities/sqli/?id=2&Submit=Submit"
        self._get(path)
        path = "/vulnerabilities/sqli_blind/?id=1&Submit=Submit"
        self._get(path)

    def _craw_rename(self):
        path = "/009-file-rename.php?from=uploads/hello.txt&to=uploads/hello.php"
        self._get(path)

    def _craw_lfi(self):
        path = "/010-file-include.php?file=header.php"
        self._get(path)

    def _craw_ssrf(self):
        path = "/011-ssrf-curl.php?url=http://127.0.0.1"
        self._get(path)

    def _craw_sqli(self):
        path = "/012-mysqli.php?server=mysql5.6&id=0"
        self._get(path)

    def _craw_xss(self):
        path = "/017-xss.php?input=saysomething"
        self._get(path)

    def _craw_eval(self):
        path = "/018-eval.php?val=$a=1; echo $a;"
        self._get(path)

    def crawl(self):
        for method in self.__dir__():
            if method.startswith("_craw_"):
                getattr(self, method)()


def _get_result(host):
    sql = "select rasp_result_list from openrasp.`{}_{}_Report`".format(host, vulns_port)
    result = iast_api._query(sql)
    vul_url_list = []
    for item in result:
        item_data = json.loads(item[0])[0]
        url = item_data["context"]["url"]
        vul_url_list.append(url)

    known_vuln_url = [
        '/vulns/001-dir.php',
        '/vulns/002-file-read.php',
        '/vulns/004-command-1.php',
        '/vulns/004-command-2.php',
        '/vulns/005-file-write.php',
        '/vulns/008-file-upload.php',
        '/vulns/009-file-rename.php',
        '/vulns/010-file-include.php',
        '/vulns/011-ssrf-curl.php',
        '/vulns/012-mysqli.php'
    ]

    result = ["测试用例,检测结果"]

    for vuln_url in known_vuln_url:
        item = [vuln_url, "漏报"]
        for url in vul_url_list:
            if url.find(vuln_url) != -1:
                item[1] = "OK"
                break
        result.append(",".join(item))

    with open("./result/vulns_result.csv", "w") as f:
        f.write("\n".join(result))

    print("Vulns scan result is generated to {}/result/vulns_result.csv".format(os.getcwd()))


def run():
    print("Starting test Vulns...")
    ip = socket.gethostbyname("apache-php7.2")
    vc = VulnsCrawler("http://{}:{}/vulns".format(ip, vulns_port))
    print("Crawling Vulns...")
    vc.crawl()
    print("Vulns crawling complete...")
    host = iast_api.run_task(vulns_port, 5)
    _get_result(host)
