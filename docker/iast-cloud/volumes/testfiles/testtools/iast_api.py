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
import requests

from testtools import config


def _make_request(path, json_data):
    url = config.console_url + path
    r = requests.post(url=url, json=json_data)
    assert r.status_code == 200
    res = json.loads(r.text, encoding="utf-8")
    assert res["status"] == 0
    return res.get("data")


def get_all():
    json_data = {
        "page": 1
    }
    path = "/api/model/get_all"
    data = _make_request(path, json_data)
    hosts = data["result"]
    total = data["total"]

    if total > 10:
        for i in range(1, int(total / 10)):
            json_data = {
                "page": i + 2
            }
            data = _make_request(path, json_data)
            hosts = hosts + data["result"]

    return hosts


def new_scan(host, port):
    json_data = {
        "host": host,
        "port": int(port)
    }
    path = "/api/scanner/new"
    _make_request(path, json_data)


def kill_scan(sid):
    json_data = {
        "scanner_id": sid
    }
    path = "/api/scanner/kill"
    _make_request(path, json_data)
