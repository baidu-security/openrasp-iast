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

import copy

from core.components import common
from core.components import exceptions
from core.components.audit_tools import request_data

class MutantHelper(object):
    """
    获取测试请求参数的工具
    """
    
    def get_params_list(self, request_data_ins, param_type_list=None):
        """
        获取所有指定参数组成的列表

        Parameters:
            request_data_ins - RequestData实例, 用于获取参数
            param_type_list - list, 获取的参数类型列表，可以包含
                              "get"、"post"、"json"、"headers"、"cookies"、"files"、"body"
                              默认为None时获取 "get" "post" "json" "headers" "cookies" 五类参数

        Returns:
            list, item为dict, 结构如下
            {
                "type": "get",
                "name": "id",
                "value": 1
            }
            当type为json时, name为数组形式, value为对应的类型(只取int/str类型)
            当type为files时, name为数组形式, value为包含"filename" "content" "content_type"三个key的dict
        """
        test_params = []
        all_param = request_data_ins.get_all_param(param_type_list)
        for param_type in all_param:
            if param_type == "json":
                json_params = self._get_json_test_params(all_param["json"])
                for item in json_params:
                    if item["value"] is None:
                        continue
                    test_params.append({
                            "type": "json",
                            "name": item["json_path"],
                            "value": item["value"]
                        })
            elif param_type == "body":
                test_params.append({
                    "type": "body",
                    "name": "body",
                    "value": all_param["body"]["body"]
                })
            elif param_type == "files":
                for i in range(len(all_param["files"])):
                    test_params.append({
                        "type": "files",
                        "name": [i, "filename"],
                        "value": all_param["files"][i]
                    })
            else:
                for param_name in all_param[param_type]:
                    test_params.append({
                        "type": param_type,
                        "name": param_name,
                        "value": all_param[param_type][param_name]
                    })
        return test_params

    def _get_json_test_params(self, json_obj):
        """
        获取json中的str、int字段的json path

        Return:
            list, item为一个dict, 格式:
            {
                "json_path":[key1, key2, ...], 
                "value": json_value
            }
        """

        result = []
        if type(json_obj) in (int, str):
            result.append({"json_path": [], "value": json_obj})
            return result
        elif type(json_obj) in (bool, type(None)):
            return result
        else:
            if type(json_obj) is list:
                keys = list(range(len(json_obj)))
            else:
                keys = list(json_obj.keys())
            deep_stack = [(json_obj, keys)]
            cur_name_list = []
            while True:
                cur_obj, cur_keys = deep_stack.pop()
                try:
                    cur_key = cur_keys.pop()
                except IndexError:
                    try:
                        cur_name_list.pop()
                        continue
                    except IndexError:
                        break
                deep_stack.append((cur_obj, cur_keys))
                cur_name_list.append(cur_key)
                if type(cur_obj[cur_key]) in (int, str, type(None)):
                    result.append(
                        {
                            "json_path": copy.deepcopy(cur_name_list),
                            "value": cur_obj[cur_key]
                        }
                    )
                    cur_name_list.pop()
                elif type(cur_obj[cur_key]) is list:
                    next_obj = cur_obj[cur_key]
                    next_keys = list(range(len(cur_obj[cur_key])))
                    deep_stack.append((next_obj, next_keys))
                elif type(cur_obj[cur_key]) is dict:
                    next_obj = cur_obj[cur_key]
                    next_keys = list(cur_obj[cur_key].keys())
                    deep_stack.append((next_obj, next_keys))
                else:
                    # boolean
                    cur_name_list.pop()
            return result

    def _init_xxe_mutant(self):
        """
        初始化xxe类型payload生成器, 当没有请求需要生成时返回False

        Reuters:
            boolean, 当没有请求需要生成时返回False

        """
        # 初始化
        self.end = False
        self.payload_index = 0
        self.test_params = []
        # 获取所有待测试参数
        request_data_ins = request_data.RequestData(self.rasp_result_ins)
        all_param = request_data_ins.get_all_param(self.mutant_config["param_type_list"])

        for param_type in all_param:
            if param_type == "json":
                json_params = self._get_json_test_params(all_param["json"])
                for item in json_params:
                    if item["value"] is None:
                        continue
                    if item["value"].find("<?xml", 0, 20) >= 0:
                        self.test_params.append((item["json_path"], "json"))
            elif param_type == "files":
                for i in range(len(all_param["files"])):
                    if all_param["files"][i]["content"].find(b"<?xml", 0, 20) >= 0:
                        self.test_params.append([i, "content"], "files")
            else:
                for param_name in all_param[param_type]:
                    if all_param[param_type][param_name].find("<?xml", 0, 20) >= 0:
                        self.test_params.append((param_name, param_type))
        # 初始化当前参数
        try:
            self.cur_param = self.test_params.pop()
            self.payload_seq = common.random_str(32)
        except IndexError:
            self.end = True
            return False
        else:
            return True

    def _gen_xxe_mutant(self):
        """
        生成一个payload为xxe类型的RequestData实例的列表和对应的checker

        Returns:
            dict, 格式为:
            {
                "request_data_list": [request_data_1 , ...]  # item为RequestData实例,
                "checker": request_data_list对应的checker
            }
            当无实例可以生成(payload用尽)时, 返回None
        """
        if not self.gen_init:
            raise exceptions.MutantNotInitError

        if self.end:
            return None

        if len(self.payload_list) == self.payload_index:
            try:
                self.cur_param = self.test_params.pop()
            except IndexError:
                self.end = True
                return None
            else:
                self.payload_index = 0
                self.payload_seq = common.random_str(32)

        param_name = self.cur_param[0]
        param_type = self.cur_param[1]
        payload = self.payload_list[self.payload_index]
        request_data_ins = request_data.RequestData(
            self.rasp_result_ins, self.payload_seq, payload[1])
        self.payload_index += 1
        request_data_ins.set_param(param_type, param_name, payload[0])
        if param_type == "files":
            param_name[1] = "content_type"
            request_data_ins.set_param(param_type, param_name, "application/xml")

        request_data_list = [request_data_ins]

        check_config = {
            "type": "xxe",
            "check_type": self.mutant_config["check_type"]
        }
        result = {
            "request_data_list": request_data_list,
            "checker": self.checker_cls(request_data_list, check_config)
        }
        return result