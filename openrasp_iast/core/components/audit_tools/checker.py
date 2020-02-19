#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Copyright 2017-2020 Baidu Inc.

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

from core.components import exceptions
from core.components.logger import Logger


class Checker(object):
    """
    用于分析测试请求结果，判断是否存在漏洞
    """

    def check_concat_in_hook(self, rasp_result_ins, hook_type, feature):
        """
        在扫描请求结果的RaspResult实例的hook信息中检测payload对应的feature，在检测到feature时，
        会调用rasp_result_ins的set_vuln_hook方法标记包含feature的hook为漏洞

        Parameters:
            rasp_result_ins - 扫描结果的RaspResult实例
            hook_type - str, 检测的hook点
            feature - str, 检测的特征字符串

        Returns:
            boolean
        """
        hook_info = rasp_result_ins.get_hook_info()
        hook_list = [
            hook_item for hook_item in hook_info if hook_item["hook_type"] == hook_type]

        token_check_item = {
            "sql": "query",
            "command": "command"
        }
        endswith_check_item = {
            "writeFile": "realpath",
            "readFile": "realpath",
            "directory": "realpath",
            "include": "realpath"
        }
        equal_check_item = {
            "ssrf": "hostname",
        }
        concat_check_item = {
            "eval": "code",
        }
        if hook_type in token_check_item:
            for hook_item in hook_list:
                if self._is_token_injected(hook_item[token_check_item[hook_type]], feature, hook_item["tokens"]):
                    rasp_result_ins.set_vuln_hook(hook_item)
                    return True
                if "env" in hook_item:
                    for env_item in hook_item["env"]:
                        env_part = env_item.split("=")
                        for part in env_part:
                            if str(feature).find(str(part)) >= 0:
                                rasp_result_ins.set_vuln_hook(hook_item)
                                return True

        elif hook_type in endswith_check_item:
            for hook_item in hook_list:
                if hook_item[endswith_check_item[hook_type]].endswith(feature):
                    rasp_result_ins.set_vuln_hook(hook_item)
                    return True
        elif hook_type in equal_check_item:
            for hook_item in hook_list:
                if hook_item[equal_check_item[hook_type]] == feature:
                    rasp_result_ins.set_vuln_hook(hook_item)
                    return True
        elif hook_type in concat_check_item:
            for hook_item in hook_list:
                if hook_item[concat_check_item[hook_type]].find(feature) >= 0:
                    rasp_result_ins.set_vuln_hook(hook_item)
                    return True
        return False

    def _is_token_injected(self, code, feature, tokens):
        """
        基于词法分析的token检测代码是否被注入

        Parameters:
            code - str, 待检测的原始代码
            feature - str, 预期被注入的内容
            tokens - list, hook信息中解析产生的tokens

        Returns:
            boolean
        """
        feature_index = code.find(feature)
        if feature_index == -1:
            return False

        distance = 1
        feature_len = len(feature)
        end = len(tokens)
        start = 0

        for i in range(end):
            if tokens[i]["stop"] > feature_index:
                start = i
                break

        if start + distance > end:
            return False

        for i in range(start, start + distance):
            if tokens[i]["stop"] > feature_index + feature_len:
                end = i
        if end - start > distance:
            return True
        else:
            return False

    def check_write_webroot(self, rasp_result_ins, feature):
        """
        检测目标文件是否写入web目录

        Parameters:
            rasp_result_ins - 扫描结果的RaspResult实例
            feature - str, 检测的特征字符串(文件名)

        Returns:
            boolean
        """
        web_root = rasp_result_ins.get_app_base_path()
        hook_info = rasp_result_ins.get_hook_info()
        hook_list = [
            hook_item for hook_item in hook_info if hook_item["hook_type"] == "writeFile"]
        for hook_item in hook_list:
            if (hook_item["realpath"].find(feature) != -1 and hook_item["realpath"].startswith(web_root)):
                rasp_result_ins.set_vuln_hook(hook_item)
                return True

    def check_php_file_upload(self, rasp_result_ins, feature):
        """
        检测php文件上传

        Parameters:
            rasp_result_ins - 扫描结果的RaspResult实例
            feature - str, 检测的特征字符串(扩展名)

        Returns:
            boolean
        """
        web_root = rasp_result_ins.get_app_base_path()
        hook_info = rasp_result_ins.get_hook_info()
        hook_list = [
            hook_item for hook_item in hook_info if hook_item["hook_type"] == "fileUpload"]
        for hook_item in hook_list:
            if (hook_item["dest_realpath"].endswith(feature) != -1 and hook_item["dest_realpath"].startswith(web_root)):
                rasp_result_ins.set_vuln_hook(hook_item)
                return True

    def check_xxe(self, rasp_result_ins, feature):
        """
        检测是否触发xxe

        Parameters:
            rasp_result_ins - 扫描结果的RaspResult实例
            feature - str, 检测的特征字符串

        Returns:
            boolean
        """
        if rasp_result_ins.has_hook_type("xxe"):
            for hook_item in rasp_result_ins.get_hook_info():
                if hook_item["hook_type"] == "xxe" and hook_item["entity"] == feature:
                    rasp_result_ins.set_vuln_hook(hook_item)
                    return True
        return False
