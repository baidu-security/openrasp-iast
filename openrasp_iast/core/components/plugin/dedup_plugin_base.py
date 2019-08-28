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

import hashlib

from core.components import logger

class DedupPluginBase(object):

    plugin_info = {
        "name": "No_name_plugin",  # 使用数字字母下划线命名, 应与文件名（不含扩展名）相同
        "description": "No description"
    }

    def get_hash_str(self, rasp_result_ins):
        """
        获取传入的RaspResult实例对应的去重hash

        Parameters:
            rasp_result_ins - RaspResult实例
        
        Returns:
            str, 对应的hash字符串
        """
        try:
            return str(self.get_hash(rasp_result_ins))
        except Exception as e:
            logger.error("Deduplicate plugin error, use default dedup algorithm, rasp_result: {}".format(rasp_result_ins), exc_info=e)
            return self.get_hash_default(rasp_result_ins)

    def get_hash(self, rasp_result_ins):
        """
        子类实现，返回一个用于区分重复请求的hash string
        """
        raise NotImplementedError

    def get_hash_default(self, rasp_result_ins):
        """
        默认hash生成算法

        Returns:
            str, 32位md5字符串
        """
        path_str = rasp_result_ins.get_path()
        stack_hash = rasp_result_ins.get_all_stack_hash()
        param_keys = "".join(sorted(rasp_result_ins.get_parameters().keys()))
        query_keys = "".join(sorted(rasp_result_ins.get_query_parameters().keys()))
        json_struct = rasp_result_ins.get_json_struct()
        files = rasp_result_ins.get_upload_files()
        file_names = []
        for file_item in files:
            file_names.append(file_item["name"])
        file_keys = "".join(sorted(file_names))
        
        contact_str = "".join([path_str, stack_hash, param_keys, json_struct, query_keys, file_keys]).encode("utf-8")
        return hashlib.md5(contact_str).hexdigest()