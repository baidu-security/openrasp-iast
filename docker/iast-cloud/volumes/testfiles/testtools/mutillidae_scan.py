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

mutillidae_port = 18662


class MutillidaeCrawler(object):

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

    def _craw_dns_lookup(self):
        # command exec
        path = "/index.php?page=dns-lookup.php"
        data = {
            "target_host": "targethost.com",
            "dns-lookup-php-submit-button": "Lookup DNS"
        }
        r = self._post(path, data)

    def _craw_user_info(self):
        # sqli
        path = "/index.php?page=user-info.php&username=admin&password=123456&user-info-php-submit-button=View+Account+Details"
        r = self._get(path)

    def _craw_login(self):
        # sqli
        path = "/index.php?page=login.php"
        data = {
            "username": "admin",
            "password": "123456",
            "login-php-submit-button": "Login"
        }
        r = self._post(path, data)

    def _craw_add_blog(self):
        # sqli
        path = "/index.php?page=add-to-your-blog.php"
        data = {
            "csrf-token": "",
            "blog_entry": "add to blog",
            "add-to-your-blog-php-submit-button": "Save Blog Entry"
        }
        r = self._post(path, data)

    def _craw_register(self):
        # sqli
        path = "/index.php?page=register.php"
        data = {
            "csrf-token": "",
            "username": "admin",
            "password": "passwd",
            "confirm_password": "passwd",
            "my_signature": "sig is none",
            "register-php-submit-button": "Create Account"
        }
        r = self._post(path, data)

    def _craw_rest_user_account(self):
        # sqli
        path = "/webservices/rest/ws-user-account.php?username=adrian"
        r = self._get(path)

    def _craw_pop_up_help_context_generator(self):
        # sqli
        path = "/includes/pop-up-help-context-generator.php?pagename=capture-data.php"
        r = self._get(path)

    def _craw_lookup_pen_test_tool(self):
        # sqli
        path = "/ajax/lookup-pen-test-tool.php"
        data = {
            "ToolID": "11"
        }
        r = self._post(path, data)

    def _craw_pen_test_tool_lookup(self):
        # sqli
        path = "/index.php?page=pen-test-tool-lookup.php"
        data = {
            "ToolID": "4",
            "pen-test-tool-lookup-php-submit-button": "Lookup Tool"
        }
        r = self._post(path, data)

    def _craw_user_poll(self):
        # sqli
        path = "/index.php?page=user-poll.php&csrf-token=&choice=Cain&initials=123456&user-poll-php-submit-button=Submit Vote"
        r = self._get(path)

    def _craw_password_generator(self):
        # xss
        path = "/index.php?page=password-generator.php&username=admin"
        r = self._get(path)

    def _craw_echo(self):
        # cmdi
        path = "/index.php?page=echo.php"
        data = {
            "message": "msgxxxxxxx",
            "echo-php-submit-button": "Echo Message"
        }
        r = self._post(path, data)

    def _craw_source_viewer(self):
        # lfi
        path = "/index.php?page=source-viewer.php"
        data = {
            "page": "secret-administrative-pages.php",
            "phpfile": "password-generator.php",
            "source-file-viewer-php-submit-button": "View File"
        }
        r = self._post(path, data)

    def _craw_text_file_viewer(self):
        # ssrf/rfi
        path = "/index.php?page=text-file-viewer.php"
        data = {
            "textfile": "http://apache-php7.2/index.html",
            "text-file-viewer-php-submit-button": "View File"
        }
        r = self._post(path, data)

    def _craw_repeater(self):
        # xss
        path = "/index.php?page=repeater.php"
        data = {
            "string_to_repeat": "input_string",
            "times_to_repeat_string": "1",
            "repeater-php-submit-button": "Repeat String"
        }
        r = self._post(path, data)

    def crawl(self):
        for method in self.__dir__():
            if method.startswith("_craw_"):
                getattr(self, method)()


def _get_result(host):
    sql = "select rasp_result_list from openrasp.`{}_{}_Report`".format(host, mutillidae_port)
    result = iast_api._query(sql)
    vul_url_list = []
    for item in result:
        item_data = json.loads(item[0])[0]
        url = item_data["context"]["url"]
        vul_url_list.append(url)

    known_vuln_url = [
        "mutillidae/index.php?page=dns-lookup.php",
        "mutillidae/index.php?page=user-info.php",
        "mutillidae/index.php?page=login.php",
        "mutillidae/index.php?page=add-to-your-blog.php",
        "mutillidae/index.php?page=register.php",
        "mutillidae/webservices/rest/ws-user-account.php",
        "mutillidae/ajax/lookup-pen-test-tool.php",
        "mutillidae/index.php?page=pen-test-tool-lookup.php",
        "mutillidae/index.php?page=user-poll.php",
        "mutillidae/index.php?page=password-generator.php",
        "mutillidae/index.php?page=echo.php",
        "mutillidae/index.php?page=source-viewer.php",
        "mutillidae/index.php?page=text-file-viewer.php",
        "mutillidae/index.php?page=repeater.php"
    ]

    result = ["测试用例,检测结果"]

    for vuln_url in known_vuln_url:
        item = [vuln_url, "漏报"]
        for url in vul_url_list:
            if url.find(vuln_url) != -1:
                item[1] = "OK"
                break
        result.append(",".join(item))

    with open("./result/mutillidae_result.csv", "w") as f:
        f.write("\n".join(result))

    print("Mutillidae scan result is generated to {}/result/mutillidae_result.csv".format(os.getcwd()))


def run():
    print("Starting test Mutillidae...")
    ip = socket.gethostbyname("apache-php7.2")
    # ip = "127.0.0.1"
    dc = MutillidaeCrawler("http://{}:{}/mutillidae".format(ip, mutillidae_port))
    print("Crawling Mutillidae...")
    dc.crawl()
    print("Mutillidae crawling complete...")
    host = iast_api.run_task(mutillidae_port, 5)
    _get_result(host)
