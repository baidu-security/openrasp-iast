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
import sys
import json
import time
import requests
import asyncio

from urllib.parse import urlparse
from aiowebsocket.converses import AioWebSocket

from core.model import report_model
from core.components import exceptions
from core.components import rasp_result
from core.components.logger import Logger
from core.components.config import Config
from core.components.cloud_console import GetAllTargetHandler
from core.components.cloud_console import KillScannerHandler
from core.components.cloud_console import CleanTargetHandler
from core.components.cloud_console import RunScannerHandler
from core.components.cloud_console import AutoStartHandler
from core.components.cloud_console import AutoStartStatusHandler
from core.components.cloud_console import GetConfigHandler
from core.components.cloud_console import ScanConfigHandler


class CloudApi(object):

    def __init__(self):
        self.server_url = Config().get_config(
            "cloud_api.backend_url") + "/v1/agent/log/attack"
        self.app_secret = Config().get_config("cloud_api.app_secret")
        self.app_id = Config().get_config("cloud_api.app_id")

    def upload_report(self):
        all_report_model = []
        base_report_model = report_model.ReportModel(
            table_prefix=None, create_table=False, multiplexing_conn=True)
        tables = base_report_model.get_tables()
        for table_name in tables:
            if table_name.lower().endswith("_report"):
                all_report_model.append(table_name)

        for table_name in all_report_model:
            table_prefix = table_name[:-7]
            try:
                model_ins = report_model.ReportModel(
                    table_prefix=table_prefix, create_table=False, multiplexing_conn=True)

                while True:
                    data_list = model_ins.get_upload_report(20)
                    data_count = len(data_list)
                    if data_count == 0:
                        break
                    Logger().info("Try to upload {} report to cloud.".format(data_count))
                    if self._send_report_data(data_list):
                        model_ins.mark_report(data_count)
                    else:
                        time.sleep(5)

            except Exception as e:
                Logger().warning("Get data from report model error.", exc_info=e)

    def _send_report_data(self, data_list):
        headers = {
            "X-OpenRASP-AppSecret": self.app_secret,
            "X-OpenRASP-AppID": self.app_id
        }
        send_data = []
        try:
            for plugin_name, description, data, message, scan_time in data_list:
                # 尚未支持请求序列类型上报
                data = json.loads(data)
                rasp_result_ins = rasp_result.RaspResult(data[0])
                server_info = rasp_result_ins.get_server_info()
                vuln_hook = rasp_result_ins.get_vuln_hook()
                url = rasp_result_ins.get_url()
                if vuln_hook is not None:
                    hook_info = vuln_hook["hook_info"]
                    attack_type = vuln_hook["hook_info"]["hook_type"]
                    stack = vuln_hook.get("stack", [])
                    stack_trace = "\n".join(stack)
                    server_type = server_info.get(
                        "name", server_info.get("server", "None"))

                    req_and_resp = "HTTP Request:\n{}\n\n\nHTTP Response:\n{}".format(
                        rasp_result_ins.get_request(),
                        rasp_result_ins.get_response())
                    if len(req_and_resp) > 2 * 1024 * 1024:
                        req_and_resp = req_and_resp[:2 * 1024 * 1024] + "\n... {} more chars ...".format(len(req_and_resp) - 2 * 1024 * 1024)
                else:
                    Logger().warning("Report data with no vuln hook detect, skip upload!")
                    continue
                cloud_format_data = {
                    "rasp_id": "IAST",
                    "app_id": self.app_id,
                    "event_type": "attack",
                    "event_time": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(scan_time)),
                    "request_id": rasp_result_ins.get_request_id(),
                    "request_method": rasp_result_ins.get_method(),
                    "intercept_state": "log",
                    "target": rasp_result_ins.get_attack_target(),
                    "server_hostname": rasp_result_ins.get_server_hostname(),
                    "server_ip": rasp_result_ins.get_attack_source(),
                    "server_type": server_type,
                    "server_version": server_info["version"],
                    "server_nic": rasp_result_ins.get_server_nic(),
                    "path": rasp_result_ins.get_path(),
                    "url": url,
                    "attack_type": attack_type,
                    "attack_params": hook_info,
                    "attack_source": rasp_result_ins.get_attack_source(),
                    "client_ip": rasp_result_ins.get_client_ip(),
                    "plugin_name": plugin_name,
                    "plugin_confidence": 90,
                    "plugin_message": message,
                    "plugin_algorithm": description,
                    "header": rasp_result_ins.get_headers(),
                    "stack_trace": stack_trace,
                    # "body": base64.b64encode(rasp_result_ins.get_body()).decode("ascii"),
                    "body": req_and_resp
                }
                send_data.append(cloud_format_data)

            send_data = json.dumps(send_data)
            r = requests.post(url=self.server_url,
                              headers=headers, data=send_data)
            response = json.loads(r.text)
            if response["status"] != 0:
                Logger().warning("Upload report to cloud failed with response: {}".format(r.text))
                return False
            else:
                Logger().debug("Upload report {}!".format(send_data))
                Logger().info("Upload report to cloud success!")
                return True
        except Exception as e:
            Logger().warning("Upload report to cloud failed!", exc_info=e)
            return False


class Transaction(object):

    def __init__(self):
        self.server_url = Config().get_config("cloud_api.backend_url")
        self.app_secret = Config().get_config("cloud_api.app_secret")
        self.app_id = Config().get_config("cloud_api.app_id")
        self.monitor_port = str(Config().config_dict["monitor.console_port"])
        self.monitor_url = urlparse(self.server_url).hostname + ":" + self.monitor_port
        self.message_bucket = []

    def get_one_message(self):
        if len(self.message_bucket) == 0:
            return
        else:
            message = self.message_bucket.pop()
            return message

    async def start(self, uri, union_header):
        print("[-] Starting HandShake to cloud_api....")
        try:
            async with AioWebSocket(uri, union_header=union_header, timeout=5) as aws:
                converse = aws.manipulator
                # 客户端给服务端发送消息
                await converse.send("startup")
                while True:
                    mes = await converse.receive()
                    # from datetime import datetime
                    # print('[-] {time}-Client receive: {rec}'
                    #       .format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), rec=mes))
                    message_str = str(mes, encoding="utf-8")
                    if "order" in message_str:
                        self.message_bucket.append(message_str)
                    elif "app_id already exist!" in message_str:
                        raise exceptions.AppIdExist
                    elif "heartbeat" not in message_str:
                        Logger().error("Converse received unknown message: {}".format(message_str))
                    res = self.parse_message()
                    if isinstance(res, str):
                        await converse.send(res)
        except exceptions.AppIdExist as e:
            print("[!] Same cloud_api.app_id can only connection for once time!")
            Logger().error("Connection cloud_api failed! Same cloud_api.app_id can only connection for once time!")
            os._exit(1)

    def parse_message(self):
        message_str = self.get_one_message()
        ret = ''
        if message_str:
            message_json = json.loads(message_str)
            order = message_json["order"]
            if order == "getAllTasks":
                ret = GetAllTargetHandler().handle_request(message_json["data"])
            elif order == 'stopTask':
                ret = KillScannerHandler().handle_request(message_json["data"])
            elif order == 'cleanTask':
                ret = CleanTargetHandler().handle_request(message_json["data"])
            elif order == 'startTask':
                ret = RunScannerHandler().handle_request(message_json["data"])
            elif order == 'autoStartTask':
                ret = AutoStartHandler().handle_request(message_json["data"])
            elif order == 'autoStartStatus':
                ret = AutoStartStatusHandler().handle_request(message_json["data"])
            elif order == 'getConfig':
                ret = GetConfigHandler().handle_request(message_json["data"])
            elif order == 'setConfig':
                ret = ScanConfigHandler().handle_request(message_json["data"])
            if isinstance(ret, dict):
                app_id = message_json["data"].get("app_id", "0")
                if 'data' not in ret.keys():
                    ret['data'] = dict()
                ret['data']['app_id'] = app_id
                return json.dumps(ret)
        return

    def run(self):
        remote = self.server_url.replace("https", "wss").replace("http", "ws") + "/v1/iast"
        union_header = {
            "X-OpenRASP-AppSecret": Config().config_dict["cloud_api.app_secret"],
            "X-OpenRASP-AppID": Config().config_dict["cloud_api.app_id"]
        }
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            asyncio.get_event_loop().run_until_complete(self.start(remote, union_header))
        except Exception as e:
            Logger().error('Cloud transaction disconnected!', exc_info=e)
