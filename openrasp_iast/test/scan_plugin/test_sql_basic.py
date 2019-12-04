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

import types
import pytest
import asyncio

from plugin.scanner import sql_basic
from core.components import rasp_result
from core.model.report_model import ReportModel
from core.components.communicator import Communicator
from core.components.plugin.scan_plugin_base import ScanPluginBase


def get_normal_response():
    response = {
        "status": "200",
        "headers": {"host": "localhost"},
        "body": b""
    }
    rasp_result_json = """
    {
        "web_server": {
            "host": "127.0.0.1", 
            "port": 8005
        }, 
        "context": {
            "requestId": "php2", 
            "json": { }, 
            "server": {
                "language": "php", 
                "name": "PHP", 
                "version": "7.2.19", 
                "os": "Linux"
            }, 
            "body": "", 
            "appBasePath": "/var/www/html", 
            "remoteAddr": "172.17.0.1", 
            "protocol": "http", 
            "method": "get", 
            "querystring": "test_param=123456", 
            "path": "/test-file.php", 
            "parameter": {
                "test_param": [
                    "123456"
                ]
            }, 
            "header": {
                "host": "localburp.com:8005", 
                "connection": "keep-alive", 
                "upgrade-insecure-requests": "1", 
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36", 
                "dnt": "1", 
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3", 
                "accept-encoding": "gzip, deflate", 
                "accept-language": "zh-CN,zh;q=0.9"
            }, 
            "url": "http://localburp.com:8005/test-file.php?test_param=123456", 
            "nic": [
                {
                    "name": "eth0", 
                    "ip": "172.17.0.2"
                }
            ], 
            "hostname": "server_host_name"
        }, 
        "hook_info": [ ]
    }
    """
    rasp_result_ins = rasp_result.RaspResult(rasp_result_json)

    result = {
        "scan_req_id": "0-a71e0906-88f6-412a-8bbe-efa94737e5c9",
        "response": response,
        "rasp_result": rasp_result_ins
    }
    return result


def get_vuln_response():
    response = {
        "status": "200",
        "headers": {"host": "localhost"},
        "body": b""
    }

    rasp_result_json = """
    {
        "web_server": {
            "host": "127.0.0.1", 
            "port": 8005
        }, 
        "context": {
           "requestId": "vuln", 
            "json": { }, 
            "server": {
                "language": "php", 
                "name": "PHP", 
                "version": "7.2.19", 
                "os": "Linux"
            }, 
            "body": "", 
            "appBasePath": "/var/www/html", 
            "remoteAddr": "172.17.0.1", 
            "protocol": "http", 
            "method": "get", 
            "querystring": "test_param[a]=123456", 
            "path": "/test-file.php", 
            "parameter": {
                "test_param": [
                    {"a": "1'openrasp"}
                ]
            }, 
            "header": {
                "host": "localburp.com:8005", 
                "connection": "keep-alive", 
                "upgrade-insecure-requests": "1", 
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36", 
                "dnt": "1", 
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3", 
                "accept-encoding": "gzip, deflate", 
                "accept-language": "zh-CN,zh;q=0.9"
            }, 
            "url": "http://localburp.com:8005/test-file.php?test_param[a]=123456", 
            "nic": [
                {
                    "name": "eth0", 
                    "ip": "172.17.0.2"
                }
            ], 
            "hostname": "server_host_name"
        }, 
        "hook_info": [
            {
                "query": "SELECT id, name FROM vuln WHERE id = 1'openrasp", 
                "server": "mysql", 
                "tokens": [
                    {
                        "start": 0, 
                        "stop": 6, 
                        "text": "SELECT"
                    }, 
                    {
                        "start": 7, 
                        "stop": 9, 
                        "text": "id"
                    }, 
                    {
                        "start": 9, 
                        "stop": 10, 
                        "text": ","
                    }, 
                    {
                        "start": 11, 
                        "stop": 15, 
                        "text": "name"
                    }, 
                    {
                        "start": 16, 
                        "stop": 20, 
                        "text": "FROM"
                    }, 
                    {
                        "start": 21, 
                        "stop": 25, 
                        "text": "vuln"
                    }, 
                    {
                        "start": 26, 
                        "stop": 31, 
                        "text": "WHERE"
                    }, 
                    {
                        "start": 32, 
                        "stop": 34, 
                        "text": "id"
                    }, 
                    {
                        "start": 35, 
                        "stop": 36, 
                        "text": "="
                    }, 
                    {
                        "start": 37, 
                        "stop": 38, 
                        "text": "1"
                    }, 
                    {
                        "start": 38, 
                        "stop": 39, 
                        "text": "'"
                    }, 
                    {
                        "start": 39, 
                        "stop": 47, 
                        "text": "openrasp"
                    }
                ], 
                "hook_type": "sql"
            }
        ]
    }
    """
    rasp_result_ins = rasp_result.RaspResult(rasp_result_json)

    result = {
        "scan_req_id": "0-a71e0906-88f6-412a-8bbe-efa94737e5c9",
        "response": response,
        "rasp_result": rasp_result_ins
    }
    return result


async def send_request(self, request_data):
    test_param = request_data.get_param("get", "test_param[a]")
    print(test_param)
    if test_param is not None and test_param.find("1'openrasp") >= 0:
        return get_vuln_response()
    else:
        return get_normal_response()


async def report(self, request_data_list, vuln_info=""):
    rasp_result_ins = request_data_list[0].get_rasp_result()
    if rasp_result_ins.get_request_id() == "vuln":
        self.has_report = True
    else:
        assert False


@pytest.fixture(scope="module")
def scan_plugin_fixture():

    report_model = ReportModel("www.test-host.com_80")
    Communicator().set_internal_shared("report_model", report_model)
    Communicator().set_internal_shared("failed_task_set", set())

    plugin_ins = sql_basic.ScanPlugin()

    plugin_ins.send_request = types.MethodType(send_request, plugin_ins)
    plugin_ins.report = types.MethodType(report, plugin_ins)

    yield plugin_ins


def test_normal(scan_plugin_fixture):

    plugin_ins = scan_plugin_fixture

    rasp_result_json = """
    {
    "web_server": {
        "host": "127.0.0.1", 
        "port": 8005
    }, 
    "context": {
        "requestId": "php2", 
        "json": { }, 
        "server": {
            "language": "php", 
            "name": "PHP", 
            "version": "7.2.19", 
            "os": "Linux"
        }, 
        "body": "", 
        "appBasePath": "/var/www/html", 
        "remoteAddr": "172.17.0.1", 
        "protocol": "http", 
        "method": "get", 
        "querystring": "test_param[a]=123456", 
        "path": "/test-file.php", 
        "parameter": {
            "test_param": [
               {"a":"123456"}
            ],
            "normal_param": [
                "123456"
            ]
        }, 
        "header": {
            "host": "localburp.com:8005", 
            "connection": "keep-alive", 
            "upgrade-insecure-requests": "1", 
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36", 
            "dnt": "1", 
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3", 
            "accept-encoding": "gzip, deflate", 
            "accept-language": "zh-CN,zh;q=0.9"
        }, 
        "url": "http://localburp.com:8005/test-file.php?test_param[a]=123456", 
        "nic": [
            {
                "name": "eth0", 
                "ip": "172.17.0.2"
            }
        ], 
        "hostname": "server_host_name"
    }, 
    "hook_info": [
            {
                "query": "SELECT id, name FROM vuln WHERE id = 123456", 
                "server": "mysql", 
                "tokens": [
                    {
                        "start": 0, 
                        "stop": 6, 
                        "text": "SELECT"
                    }, 
                    {
                        "start": 7, 
                        "stop": 9, 
                        "text": "id"
                    }, 
                    {
                        "start": 9, 
                        "stop": 10, 
                        "text": ","
                    }, 
                    {
                        "start": 11, 
                        "stop": 15, 
                        "text": "name"
                    }, 
                    {
                        "start": 16, 
                        "stop": 20, 
                        "text": "FROM"
                    }, 
                    {
                        "start": 21, 
                        "stop": 25, 
                        "text": "vuln"
                    }, 
                    {
                        "start": 26, 
                        "stop": 31, 
                        "text": "WHERE"
                    }, 
                    {
                        "start": 32, 
                        "stop": 34, 
                        "text": "id"
                    }, 
                    {
                        "start": 35, 
                        "stop": 36, 
                        "text": "="
                    }, 
                    {
                        "start": 37, 
                        "stop": 43, 
                        "text": "123456"
                    }
                ], 
                "hook_type": "sql"
            }
        ]
    }
    """
    rasp_result_ins = rasp_result.RaspResult(rasp_result_json)

    plugin_ins.has_report = False
    asyncio.run(plugin_ins._scan(0, rasp_result_ins))
    assert plugin_ins.has_report is True
