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

from core.components.plugin import scan_plugin_base


class ScanPlugin(scan_plugin_base.ScanPluginBase):

    plugin_info = {
        "name": "fileupload_basic",
        "show_name": "文件上传检测插件",
        "description": "基础文件上传漏洞检测插件"
    }

    def __init__(self):
        super().__init__()

    def mutant(self, rasp_result_ins):
        """
        测试向量生成
        """
        server_language = rasp_result_ins.get_server_info()["language"]
        if not rasp_result_ins.has_hook_type("fileUpload"):
            return
        elif server_language == "java" and not rasp_result_ins.has_hook_type("writeFile"):
            return

        java_payloads = [
            ("openrasp.jsp", "openrasp.jsp"),
            ("../../openrasp.jsp", "openrasp.jsp"),
            ("openrasp.jpg.jsp", "openrasp.jpg.jsp"),
            ("openrasp.jspx", "openrasp.jspx")]

        php_payloads = [
            ("openrasp.php", ".php"),
            ("../../openrasp.php", ".php")]

        if server_language == "java":
            payload_list = java_payloads
        else:
            payload_list = php_payloads

        # 获取所有待测试参数
        request_data_ins = self.new_request_data(rasp_result_ins)
        test_params = self.mutant_helper.get_params_list(
            request_data_ins, ["files"])
        for param in test_params:
            payload_seq = self.gen_payload_seq()
            for payload in payload_list:
                request_data_ins = self.new_request_data(
                    rasp_result_ins, payload_seq, payload[1])
                request_data_ins.set_param(
                    param["type"], param["name"], payload[0])
                request_data_ins.set_param(
                    param["type"], [param["name"][0], "content_type"], "image/jpeg")
                request_data_ins.set_param(
                    param["type"], [param["name"][0], "content"], b"gif89a xxxx")
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

        server_language = rasp_result_ins.get_server_info()["language"]
        if server_language == "java":
            if self.checker.check_write_webroot(rasp_result_ins, feature):
                return "用户可上传脚本文件至web目录"
            else:
                return None
        else:
            if self.checker.check_php_file_upload(rasp_result_ins, feature):
                return "用户可上传脚本文件至web目录"
            else:
                return None
