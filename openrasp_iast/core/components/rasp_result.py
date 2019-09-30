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

import re
import json
import pickle
import hashlib
import binascii
import jsonschema
import urllib.parse

from core.components import common
from core.components import exceptions
from core.components.logger import Logger


class RaspResult(object):
    """
    用于表示一个http请求的rasp_result
    """
    schema = {
        "type": "object",
        "required": ["context", "hook_info"],
        "properties": {
            "context": {
                "type": "object",
                "required": ["requestId", "json", "server", "body", "method", "querystring", "path", "parameter", "header", "nic", "hostname"],
                "properties": {
                    "requestId": {"type": "string"},
                    "server": {"type": "object"},
                    "parameter": {"type": "object"},
                    "header": {"type": "object"},
                    "body": {"type": "string"},
                    "method": {"type": "string"},
                    "querystring": {"type": "string"},
                    "path": {"type": "string"},
                    "hostname": {"type": "string"},
                    "nic": {"type": "array"},
                    "target": {"type": "string"},
                    "source": {"type": "string"},
                }
            },
            "hook_info": {"type": "array"}
        }
    }
    rasp_result_validtor = jsonschema.Draft7Validator(schema)

    host_reg = re.compile(r'^[a-zA-Z0-9.\-]+$')

    def __init__(self, rasp_result_json):
        """
        初始化

        Parameters:
            rasp_result_json - 接收自rasp agent的rasp_result json字符串 或 其反序列化后的dict
        """
        self.hash_str = ""
        try:
            if type(rasp_result_json) is dict:
                self.rasp_result_dict = rasp_result_json
            else:
                self.rasp_result_dict = json.loads(rasp_result_json)
            self.rasp_result_validtor.validate(self.rasp_result_dict)
        except (UnicodeDecodeError, ValueError, TypeError) as e:
            Logger().warning(
                "RaspResult init with non-json data:{}".format(rasp_result_json), exc_info=e)
            raise exceptions.ResultJsonError
        except jsonschema.exceptions.ValidationError as e:
            Logger().warning(
                "RaspResult init with invalid format data!", exc_info=e)
            raise exceptions.ResultInvalid
        self._check_target(rasp_result_json)

    def _check_target(self, rasp_result_json):
        """
        检查rasp_result中是否包含target，不包含则从context->host中获取

        Parameters:
            rasp_result_json - 接收自rasp agent的rasp_result json字符串
        """
        try:
            self.rasp_result_dict["context"]["header"]["scan-request-id"]
        except KeyError:
            try:
                self.rasp_result_dict["web_server"]["port"]
                self.rasp_result_dict["web_server"]["host"] = self.rasp_result_dict["web_server"]["host"].replace(
                    "_", "-")
                if not self.host_reg.match(self.rasp_result_dict["web_server"]["host"]):
                    raise KeyError
            except KeyError:
                Logger().warning("RaspResult host get fail, data:{}".format(rasp_result_json))
                raise exceptions.ResultHostError

    def __str__(self):
        """
        用于序列化
        """
        return json.dumps(self.rasp_result_dict)

    def __getitem__(self, attr):
        return self.rasp_result_dict[attr]

    def is_scan_result(self):
        """
        判断是否为扫描请求

        Returns:
            boolean
        """
        if self.rasp_result_dict["context"]["header"].get("scan-request-id", "") != "":
            return True
        else:
            return False

    def dump(self):
        """
        用于序列化
        """
        return json.dumps(self.rasp_result_dict)

    def get_hash(self):
        """
        获取当前请求hash

        Returns:
            str, 请求hash字符串
        """
        return self.hash_str

    def set_hash(self, hash_str):
        """
        设置当前请求hash

        Parameters:
            hash_str - str, 要设置的hash字符串
        """
        self.hash_str = hash_str

    def get_request_id(self):
        """
        获取当前请求的request_id

        Returns:
            string, request_id
        """
        return self.rasp_result_dict["context"]["requestId"]

    def get_server_hostname(self):
        """
        获取当前请求对应Server的hostname

        Returns:
            str, hostname
        """
        return self.rasp_result_dict["context"]["hostname"]

    def get_server_nic(self):
        """
        获取当前请求对应Server的网卡信息

        Returns:
            list, 包含多个dict
            {
                "name": "eth0", 
                "ip": "172.17.0.2"
            }
        """
        return self.rasp_result_dict["context"]["nic"]

    def get_result_queue_id(self):
        """
        获取当前请求的result_queue_id, 即对应扫描器的队列

        Returns:
            string, result_queue_id

        Raises:
            exceptions.GetQueueIdError 无此id的请求(非扫描请求)引发此异常
        """
        scan_request_id = self.get_scan_request_id()
        if scan_request_id != "":
            return scan_request_id.split("-")[0]
        else:
            raise exceptions.GetQueueIdError

    def get_scan_request_id(self):
        """
        获取当前请求的scan_request_id

        Returns:
            string, scan_request_id, 不存在返回空
        """
        return self.rasp_result_dict["context"]["header"].get("scan-request-id", "")

    def get_server_info(self):
        """
        获取服务器信息

        Returns:
            dict , 格式为
            {
                'name': 'Tomcat / JBoss / Jetty',
                'version': '8',
                'os': 'Linux',
                'language': 'java / php' 
             }
        """
        return self.rasp_result_dict["context"]["server"]

    def get_app_base_path(self):
        """
        获取服务器web目录

        Returns:
            str, '/home/tomcat/webapps'
        """
        return self.rasp_result_dict["context"]["appBasePath"]

    def get_host(self):
        """
        获取当前请求的host

        Returns:
            string, 获取的host
        """
        return self.rasp_result_dict["web_server"]["host"]

    def get_port(self):
        """
        获取当前请求的port

        Returns:
            int, 请求的port
        """
        return self.rasp_result_dict["web_server"]["port"]

    def get_host_port(self):
        """
        获取当前请求的host_port

        Returns:
            string, 获取的host_port
        """
        server = self.rasp_result_dict["web_server"]
        return server["host"] + "_" + str(server["port"])

    def get_attack_target(self):
        """
        获取当前请求的server ip, 不存在时返回空

        Returns:
            string, 获取的ip
        """
        return self.rasp_result_dict["context"].get("target", "")

    def get_attack_source(self):
        """
        获取当前请求的发送者的ip(tcp连接的client), 不存在时返回空

        Returns:
            string, 获取的ip
        """
        return self.rasp_result_dict["context"].get("source", "")

    def get_client_ip(self):
        """
        获取当前请求的client ip(由header中client-ip获取), 不存在时返回空

        Returns:
            string, 获取的ip
        """
        return self.rasp_result_dict["context"].get("clientIp", "")

    def get_method(self):
        """
        获取当前请求的http方法

        Returns:
            string, 小写形式
        """
        return self.rasp_result_dict["context"]["method"].lower()

    def get_path(self):
        """
        获取当前请求的url path

        Returns:
            string, 获取的path
        """
        return self.rasp_result_dict["context"]["path"]

    def get_url(self):
        """
        获取当前请求的url

        Returns:
            string, 获取的url
        """
        return self.rasp_result_dict["context"]["url"]

    def get_scan_url(self):
        """
        获取重放当前请求使用的url

        Returns:
            string, 获取的url
        """
        if self.rasp_result_dict["context"]["url"].startswith("https"):
            protocol = "https://"
        else:
            protocol = "http://"
        host_port = ":".join(self.get_host_port().rsplit("_", 1))
        path = self.get_path()
        return protocol + host_port + path

    def get_query_string(self):
        """
        获取当前请求的url query

        Returns:
            string, 获取的query
        """
        return self.rasp_result_dict["context"]["querystring"]

    def get_headers(self):
        """
        获取当前请求的http header

        Returns:
            dict, 每个header字段对应一个key-value
        """
        return self.rasp_result_dict["context"]["header"]

    def get_parameters(self):
        """
        获取当前请求的所有参数

        Returns:
            dict, 每个参数字段对应一个key-value
        """
        return self.rasp_result_dict["context"]["parameter"]

    def get_query_parameters(self):
        """
        获取当前请求的所有url中的参数

        Returns:
            dict, 每个参数字段对应一个key-value, value为list，包含所有同名参数
        """
        return urllib.parse.parse_qs(self.rasp_result_dict["context"]["querystring"], keep_blank_values=True)

    def get_query_param_dict(self):
        """
        获取当前请求的所有url中的参数

        Returns:
            dict, 每个参数字段对应一个key-value
        """
        result = {}
        params = urllib.parse.parse_qsl(
            self.rasp_result_dict["context"]["querystring"], keep_blank_values=True)
        rasp_params = self.get_parameters()
        for item in params:
            if item[0] not in result:
                result[item[0]] = item[1]
            else:
                rasp_para_value = rasp_params.get(item[0], [None])
                if type(rasp_para_value[0]) == str:
                    result[item[0]] = rasp_para_value[0]
        return result

    def get_post_data_dict(self):
        """
        获取当前请求的所有post参数

        Returns:
            dict, 每个参数字段对应一个key-value
        """
        all_params = self.get_parameters()
        get_params = self.get_query_parameters().keys()
        result = {}
        for para_name in all_params:
            if para_name not in get_params and type(all_params[para_name][0]) == str:
                result[para_name] = all_params[para_name][0]
            elif len(all_params[para_name]) == 2 and type(all_params[para_name][1]) == str:
                result[para_name] = all_params[para_name][1]
        return result

    def get_cookies(self):
        """
        获取当前请求的header的cookie字段

        Returns:
            str, cookie字段
        """
        for header_name in self.rasp_result_dict["context"]["header"]:
            if header_name.lower() == "cookie":
                result = self.rasp_result_dict["context"]["header"][header_name]
                return result
        return None

    def get_content_type(self):
        """
        获取当前请求的header的content-type字段

        Returns:
            str, content-type, 不存在时为空
        """
        result = ""
        for header_name in self.rasp_result_dict["context"]["header"]:
            if header_name.lower() == "content-type":
                result = self.rasp_result_dict["context"]["header"][header_name]
        return result

    def get_content_length(self):
        """
        获取当前请求的header的content-length字段

        Returns:
            str, content-length
        """
        result = 0
        for header_name in self.rasp_result_dict["context"]["header"]:
            if header_name.lower() == "content-length":
                try:
                    result = int(
                        self.rasp_result_dict["context"]["header"][header_name])
                except Exception:
                    pass
        return result

    def get_json(self):
        """
        对content-type为json的请求，获取其body的json

        Returns:
            json.loads后返回的对象，非json请求或不存在时返回{}
        """
        return self.rasp_result_dict["context"]["json"]

    def get_body(self):
        """
        获取当前请求的http body

        Returns:
            json.loads返回的对象，非json请求或不存在时返回{}
        """
        return bytes.fromhex(self.rasp_result_dict["context"]["body"])

    def get_hook_info(self):
        """
        获取当前请求的hook信息

        Returns:
            list, 每个item为一个hook点的dict，没有时为空
        """
        return self.rasp_result_dict["hook_info"]

    def has_hook_type(self, hook_type):
        """
        判断当前请求的hook信息中，是否包含某一类型的hook点

        Parameters:
            hook_type - string, hook点类型

        Returns:
            boolean
        """
        for item in self.rasp_result_dict["hook_info"]:
            if item["hook_type"] == hook_type:
                return True
        return False

    def get_upload_files(self):
        """
        获取当前请求中包含的upload hook类型中的文件上传参数

        Returns:
            list, 其中的每个item为一个dict, 存储上传文件的参数, 结构为
            {
                "name": "param_name",
                "filename": "file.txt",
                "content": "xxxxx"
            }
        """
        result = []
        for item in self.rasp_result_dict["hook_info"]:
            if item["hook_type"] == "fileUpload":
                upfile = {
                    "name": item["name"],
                    "filename": item["filename"],
                    "content": item["content"].encode("utf-8")
                }
                result.append(upfile)
        return result

    def get_json_struct(self):
        """
        获取当前请求的json结构的序列化字符串

        Returns:
            string, json结构字符串
        """
        json_data = self.rasp_result_dict["context"]["json"]
        result = []
        parse_stack = [json_data]
        while len(parse_stack) > 0:
            cur_obj = parse_stack.pop()
            if cur_obj is None:
                result.append("N|")
            elif type(cur_obj) is int:
                result.append("I|")
            elif type(cur_obj) is str:
                result.append("S|")
            elif type(cur_obj) is list:
                length = len(cur_obj)
                for item in cur_obj:
                    parse_stack.append(item)
                result.append("L:" + str(length) + "|")
            elif type(cur_obj) is dict:
                key_list = []
                for key in cur_obj:
                    key_list.append(key.replace(",", "\\,"))
                    parse_stack.append(cur_obj[key])
                result.append("D:" + ",".join(key_list) + ",|")
        return "".join(result)

    def get_all_stack_hash(self):
        """
        获取当前请求所有hook点调用栈的hash

        Returns:
            string, md5字符串
        """
        hook_str_list = []
        for hook_info in self.rasp_result_dict["hook_info"]:
            try:
                hook_stack_str = "".join(hook_info["stack"])
                hook_str_list.append(hook_stack_str)
            except KeyError:
                pass
        contact_str = "".join(hook_str_list).encode("utf-8")
        return hashlib.md5(contact_str).hexdigest()

    def set_vuln_hook(self, hook_item):
        """
        设置当前请求的漏洞信息

        Parameters:
            hook_item - dict, 取自请求的hook_info
        """
        try:
            hook_stack_str = "".join(hook_item["stack"]).encode("latin-1")
            stack_hash = hashlib.md5(hook_stack_str).hexdigest()
        except KeyError:
            stack_hash = "random-" + common.random_str(32)

        self.rasp_result_dict["vuln_hook"] = {
            "hook_info": hook_item,
            "stack_hash": stack_hash
        }

    def get_vuln_hook(self):
        """
        获取当前请求的漏洞信息

        Returns:
            dict,  {"hook_info": hook_info列表中包含漏洞的hook_item, "stack_hash": 堆栈hash}, 不存在时返回None
        """
        try:
            return self.rasp_result_dict["vuln_hook"]
        except KeyError:
            return None
