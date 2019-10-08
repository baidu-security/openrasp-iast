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
    "start_scanner_0": {
        "host": "127.0.0.1",
        "port": 8005,
        "auth_plugin": "default",
        "scan_plugin_list": []
    },
    "start_scanner_1": {
        "host": "127.0.0.1",
        "port": 8006,
        "auth_plugin": "default",
        "scan_plugin_list": []
    },
    "cancel_scanner_0": {
        "scanner_id": 0
    },
    "kill_scanner_1": {
        "scanner_id": 1
    },
    "clean_target_0": {
        "host": "127.0.0.1",
        "port": 8005,
    },
    "clean_target_1": {
        "host": "127.0.0.1",
        "port": 8006,
    },
    "get_report": {
        "host": "127.0.0.1",
        "port": 8006,
        "page": 1,
        "perpage": 10
    }
}

http_sender = helper.HttpSender(
    "127.0.0.1", Config().get_config("monitor.console_port"))


def test_http_server_run(monitor_fixture):
    """
    测试monitor http server正常启动
    """
    r = http_sender.test_connect("/api/model/get_report")
    assert r.status_code == 405


def test_send_invalid_data(monitor_fixture):
    """
    测试json格式校验失败
    """
    json_data = http_data["invalid"]
    try:
        status_code = http_sender.send_data(
            json_data, "/api/model/get_report").status_code
    except Exception as e:
        assert False == e
    else:
        assert status_code == 415


def test_cpu(monitor_fixture):
    monitor_fixture["set_system_info"](1, 2)


def test_start_scanner(monitor_fixture):
    """
    测试启动scanner
    """
    data = http_data["start_scanner_0"]
    path = "/api/scanner/new"

    # 启动第1个scanner
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0

    # 目标已被scanner_1扫描
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 3

    data = http_data["start_scanner_1"]
    # 启动第2个scanner
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0

    # scanner数量达到上限
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 2

    data = http_data["invalid"]
    # 启动参数格式错误
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 1

    time.sleep(2)

    # 验证启动结果
    data = {}
    path = "/api/scanner/status"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0
    try:
        data = json.loads(r.text)
        data["data"]["0"]
        data["data"]["1"]
    except KeyError:
        assert False
    try:
        data["data"]["2"]
    except KeyError:
        assert True


def test_scheduler(monitor_fixture):
    max_cr_last = Communicator().get_value("max_concurrent_request", "Scanner_0")
    for i in range(5):
        Communicator().add_value("send_request", "Scanner_0", 30)
        time.sleep(Config().get_config("monitor.schedule_interval") * 1.5)
        max_cr = Communicator().get_value("max_concurrent_request", "Scanner_0")
        assert max_cr > max_cr_last or max_cr == Config(
        ).get_config("scanner.max_concurrent_request")
        max_cr_last = max_cr

    assert max_cr_last == 5

    for i in range(20):
        Communicator().add_value("send_request", "Scanner_0", 30)
        Communicator().add_value("failed_request", "Scanner_0", 1)
        time.sleep(Config().get_config("monitor.schedule_interval") * 1.5)
        max_cr = Communicator().get_value("max_concurrent_request", "Scanner_0")
        ri = Communicator().get_value("request_interval", "Scanner_0")
        assert max_cr < max_cr_last or max_cr == 1 or ri <= 256
        max_cr_last = max_cr

    assert max_cr_last == 1

    for i in range(50):
        Communicator().add_value("send_request", "Scanner_0", 30)
        time.sleep(Config().get_config("monitor.schedule_interval") * 1.5)
        max_cr = Communicator().get_value("max_concurrent_request", "Scanner_0")
        ri = Communicator().get_value("request_interval", "Scanner_0")

    assert max_cr == 1

    for i in range(50):
        Communicator().add_value("send_request", "Scanner_0", 30)
        time.sleep(Config().get_config("monitor.schedule_interval") * 1.5)
        max_cr = Communicator().get_value("max_concurrent_request", "Scanner_0")
        ri = Communicator().get_value("request_interval", "Scanner_0")
        if max_cr > 1:
            break

    assert max_cr > 1


def test_cancel_scanner(monitor_fixture):
    data = http_data["invalid"]
    path = "/api/scanner/cancel"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 1

    data = http_data["cancel_scanner_0"]
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0
    canceled = False
    for i in range(20):
        data = {}
        path = "/api/scanner/status"
        r = http_sender.send_json(data, path)
        assert r.status_code == 200
        try:
            data = json.loads(r.text)
            data["data"]["0"]
        except KeyError:
            canceled = True
            break
        else:
            time.sleep(2)
    assert canceled

    # 测试cancel 不存在的scanner
    data = http_data["cancel_scanner_0"]
    path = "/api/scanner/cancel"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 2


def test_clean_target(monitor_fixture):
    data = http_data["invalid"]
    path = "/api/model/clean_target"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 1

    data = http_data["clean_target_0"]
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0

    data = http_data["clean_target_1"]
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 2


def test_get_all_target(monitor_fixture):
    data = {}
    path = "/api/model/get_all"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    ret = json.loads(r.text)
    assert ret["status"] == 0
    assert ret["data"]["total"] == 1


def test_get_report(monitor_fixture):
    sql = """INSERT INTO `ori`.`127.0.0.1_8006_Report` VALUES (1, 'test', '123abcd', '{\"request_id\": \"php1\", \"scan_request_id\": \"\", \"web_server\": {\"host\": \"127.0.0.1\", \"port\": 8005}, \"context\": {\"json\": {}, \"server\": {\"language\": \"php\", \"name\": \"PHP\", \"version\": \"7.2.19\", \"os\": \"Linux\"}, \"body\": \"\", \"appBasePath\": \"/var/www/html\", \"remoteAddr\": \"172.17.0.1\", \"protocol\": \"http\", \"method\": \"get\", \"querystring\": \"url=http://192.168.154.200.xip.io\", \"path\": \"/011-ssrf-curl.php\", \"parameter\": {\"url\": [\"http://192.168.154.200.xip.io\"]}, \"header\": {\"host\": \"127.0.0.1:8005\", \"connection\": \"keep-alive\", \"upgrade-insecure-requests\": \"1\", \"dnt\": \"1\", \"user-agent\": \"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36\", \"accept\": \"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3\", \"referer\": \"http://127.0.0.1:8005/011-ssrf-curl.php\", \"accept-encoding\": \"gzip, deflate, br\", \"accept-language\": \"zh-CN,zh;q=0.9\"}, \"url\": \"http://127.0.0.1:8005/011-ssrf-curl.php?url=http://192.168.154.200.xip.io\"}, \"hook_info\": []}', 'payload_seq', 'test msg', 1, 0);"""

    helper.execute_sql(sql)
    data = http_data["invalid"]
    path = "/api/model/get_report"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 1

    data = http_data["get_report"]
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    ret = json.loads(r.text)
    assert ret["status"] == 0
    assert ret["data"]["total"] == 1


def test_kill_scanner(monitor_fixture):
    data = http_data["invalid"]
    path = "/api/scanner/kill"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 1

    data = http_data["kill_scanner_1"]
    r = http_sender.send_json(data, path)
    assert r.status_code == 200

    data = {}
    path = "/api/scanner/status"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 0
    try:
        data = json.loads(r.text)
        data["data"]["1"]
    except KeyError:
        pass
    else:
        assert False

    data = http_data["kill_scanner_1"]
    path = "/api/scanner/kill"
    r = http_sender.send_json(data, path)
    assert r.status_code == 200
    status = json.loads(r.text)["status"]
    assert status == 2
