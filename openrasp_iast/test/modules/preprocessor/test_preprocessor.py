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
import time
import pytest

import helper
from core.components.config import Config
from core.components.communicator import Communicator


http_data = {
    "invalid": {
        "json": "Test"
    },
    "rasp_result": {
        "web_server": {
            "host": "x.com",
            "port": 0
        },
        "context": {
            "requestId": "kci12",
            "json": {},
            "server": {
                "language": "php",
                "name": "PHP",
                "version": "7.2.18",
                "os": "Linux"
            },
            "body": "2323",
            "appBasePath": "/var/www/html",
            "remoteAddr": "172.17.0.1",
            "protocol": "http",
            "method": "post",
            "querystring": "a=1",
            "path": "/cmdo2.php",
            "parameter": {},
            "header": {
                "host":"www.test-host.com:80",
                "scan-request-id": "0-34abcd"
            },
            "url": "http://localname.com:8889/cmd.php",
            "nic": [
                {
                    "name": "eth0", 
                    "ip": "172.17.0.2"
                }
            ], 
            "hostname": "server_host_name"
        },
        "hook_info": []
    },
    "new_request_1": {
        "web_server": {
           
        },
        "context": {
            "requestId": "kci13",
            "json": {},
            "server": {
                "language": "php",
                "name": "PHP",
                "version": "7.2.18",
                "os": "Linux"
            },
            "body": "2323",
            "appBasePath": "/var/www/html",
            "remoteAddr": "172.17.0.1",
            "protocol": "http",
            "method": "post",
            "querystring": "a=1",
            "path": "/cmdo2.php",
            "parameter": {},
            "header": {
                "host":"www.test-host.com:80",
                "scan-request-id": "",
            },
            "url": "http://localname.com:8889/cmd.php",
            "nic": [
                {
                    "name": "eth0", 
                    "ip": "172.17.0.2"
                }
            ], 
            "hostname": "server_host_name"
        },
        "hook_info": []
    },
    "new_request_2": {
        "web_server": {
            "host": "www.test-host.com",
            "port": 80
        },
        "context": {
            "requestId": "kci13",
            "json": {},
            "server": {
                "language": "php",
                "name": "PHP",
                "version": "7.2.18",
                "os": "Linux"
            },
            "body": "2323",
            "appBasePath": "/var/www/html",
            "remoteAddr": "172.17.0.1",
            "protocol": "http",
            "method": "post",
            "querystring": "a=1",
            "path": "/cmd.php",
            "parameter": {},
            "header": {
            },
            "url": "http://localname.com:8889/cmd.php",
            "nic": [
                {
                    "name": "eth0", 
                    "ip": "172.17.0.2"
                }
            ], 
            "hostname": "server_host_name"
        },
        "hook_info": []
    }
}


http_sender = helper.HttpSender("127.0.0.1", Config().get_config("preprocessor.http_port"))
api_path = Config().get_config("preprocessor.api_path")

def test_http_server_run(preprocessor_fixture):
    r = http_sender.test_connect(api_path)
    assert r.status_code == 405


def test_send_invalid_data(preprocessor_fixture):
    """
    测试json格式校验失败
    """
    json_data = http_data["invalid"]
    try:
        r = http_sender.send_data(json_data, api_path)
    except Exception as e:
        assert False == e
    else:
        assert r.status_code == 200
        assert json.loads(r.text)["status"] == 1


def test_send_rasp_result_data(preprocessor_fixture):
    """
    测试rasp_result型json data处理
    """
    json_data = http_data["rasp_result"]
    try:
        r = http_sender.send_json(json_data, api_path)
    except Exception as e:
        assert False == e
    else:
        assert r.status_code == 200
        assert json.loads(r.text)["status"] == 0
        data = None
        for i in range(10):
            try:
                data = Communicator().get_data_nowait("rasp_result_queue_0")
            except Exception:
                time.sleep(0.5)
        assert data.get_request_id() == json_data["context"]["requestId"]


def test_send_new_request_data(preprocessor_fixture):
    """
    测试new_request型json data处理
    """
    try:
        r1 = http_sender.send_json(http_data["new_request_1"], api_path)
        r2 = http_sender.send_json(http_data["new_request_2"], api_path)
    except Exception as e:
        assert False
    else:
        assert r1.status_code == 200 and r2.status_code == 200
        assert json.loads(r1.text)["status"] == 0 and json.loads(r2.text)["status"] == 0

        assert helper.get_data_count("www.test-host.com_80_ResultList") == 2


def test_send_duplicate_data(preprocessor_fixture):
    """
    测试重复的new_request类json处理
    """
    try:
        r2 = http_sender.send_json(http_data["new_request_2"], api_path)
        r1 = http_sender.send_json(http_data["new_request_1"], api_path)
    except Exception as e:
        assert False
    else:
        assert r1.status_code == 200 and r2.status_code == 200
        assert json.loads(r1.text)["status"] == 0 and json.loads(r2.text)["status"] == 0
        assert helper.get_data_count("www.test-host.com_80_ResultList") == 2


def test_clean_lru(preprocessor_fixture):
    """
    测试清除lru
    """
    helper.clean_table("www.test-host.com_80_ResultList")
    Communicator().set_clean_lru(["www.test-host.com_80"])
    try:
        r = http_sender.send_json(http_data["new_request_1"], api_path)
    except Exception as e:
        assert False
    else:
        assert r.status_code == 200
        assert json.loads(r.text)["status"] == 0
        assert helper.get_data_count("www.test-host.com_80_ResultList") == 1

# @pytest.mark.test_test
# def test_passing2(preprocessor_fixture):
#     print(preprocessor_fixture)
#     assert (1, 3, 3) == (1, 2, 3)
