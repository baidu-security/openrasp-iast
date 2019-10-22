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
import copy
import json
import aiohttp
import binascii
import urllib.parse
import http.cookies

from core.components import common
from core.components import exceptions
from core.components.logger import Logger
from core.components.communicator import Communicator


class RequestData(object):
    """
    用于构造一个http测试请求信息的类
    """

    http_methods = ["get", "post", "head",
                    "push", "delete", "options", "patch"]

    def __init__(self, rasp_result_ins, payload_seq=None, payload_feature=None):
        """
        初始化

        Parameters:
            rasp_result_ins - RaspResult实例，使用其中的信息构造原始http请求
            payload_seq - string, 随机字符序列，用于区分当前请求正在被测试的参数防止多次报警
            payload_feature - 用于检测payload是否成功投放的特征
        """
        self.rasp_result_ins = rasp_result_ins
        url = rasp_result_ins.get_scan_url()
        self.method = rasp_result_ins.get_method().lower()
        if not self._is_valid_method(self.method):
            raise exceptions.UnsupportedHttpData

        data = {}
        json = None
        cookies = None
        body = None
        files = []
        self.content_type = rasp_result_ins.get_content_type()
        if self.content_type.startswith("application/x-www-form-urlencoded"):
            data = rasp_result_ins.get_post_data_dict()
        elif self.content_type.startswith("application/json"):
            json = copy.deepcopy(rasp_result_ins.get_json())
        elif self.content_type.startswith("multipart/form-data"):
            data = rasp_result_ins.get_post_data_dict()
            files = rasp_result_ins.get_upload_files()
        elif self.content_type.startswith("text/xml"):
            body = rasp_result_ins.get_body()
        else:
            content_length = rasp_result_ins.get_content_length()
            if content_length < 4 * 1024:
                body = rasp_result_ins.get_body()
            else:
                raise exceptions.UnsupportedHttpData

        raw_cookie = rasp_result_ins.get_cookies()
        if raw_cookie is not None:
            cookie_obj = http.cookies.SimpleCookie()
            cookie_obj.load(raw_cookie)
            cookies = {}
            for key, morsel in cookie_obj.items():
                cookies[key] = morsel.value

        headers = copy.deepcopy(rasp_result_ins.get_headers())
        del_keys = []
        for key in headers:
            if key.lower() == "cookie":
                del_keys.append(key)
        for key in del_keys:
            del headers[key]

        self.http_data = {
            "url": rasp_result_ins.get_scan_url(),
            "headers": headers,
            "params": rasp_result_ins.get_query_param_dict(),
            "data": data,
            "cookies": cookies,
            "json": json,
            "body": body,
            "files": files
        }
        keys = list(self.http_data["headers"].keys())
        for key in keys:
            if key.lower() == "content-length":
                del self.http_data["headers"][key]

        try:
            self.queue_id = Communicator().get_module_id()
        except TypeError:
            self.queue_id = "1"

        self.payload_info = {
            # payload序列号, 同一测试点相同类型payload序列号应相同，保证报警不重复
            "seq": payload_seq,
            # 用于检测payload是否生效的特征
            "feature": payload_feature
        }

        # 请求返回的HTTP结果
        self.response = {}
        # 请求对应的rasp_result
        self.rasp_result = None

    def _is_valid_method(self, method):
        """
        判定http方法是否支持

        Parameters:
            method - str, 小写的http方法

        Returns:
            boolean
        """
        if method in self.http_methods:
            return True
        else:
            return False

    def _make_multipart(self):
        """
        构造multipart/form-data 类型的aiohttp请求参数

        Returns:
            aiohttp.MultipartWriter实例
        """
        mpwriter = aiohttp.MultipartWriter('form-data')
        post_data = self.http_data["data"]
        for key in post_data:
            part = mpwriter.append(post_data[key])
            part.set_content_disposition("form-data", name=key)
            part.headers.pop(aiohttp.hdrs.CONTENT_LENGTH, None)
            part.headers.pop(aiohttp.hdrs.CONTENT_TYPE, None)

        files = self.http_data["files"]
        for file_item in files:
            content_type = file_item.get(
                "content_type", 'application/octet-stream')
            part = mpwriter.append(file_item["content"], {
                                   'CONTENT-TYPE': content_type})
            part.set_content_disposition(
                "form-data", filename=file_item["filename"], name=file_item["name"])
            part.headers.pop(aiohttp.hdrs.CONTENT_LENGTH, None)

        Logger().debug("Make multipart data from dict: {}".format(post_data))
        return mpwriter

    def set_param(self, para_type, para_name, value):
        """
        设置HTTP请求的某个变量，覆盖原有值，不存在时创建

        Parameters:
            para_type - str, 参数类型，可选get, post, cookies, headers, json, files, body
            para_name - str/list, 参数名或参数路径,
                        当para_type为json时, para_name应为一个list,包含json path每一级的key
                        当para_type为files时, para_name应为一个包含两个item的list, 第一个指定要设置的files dict的下标, 第二个指定dict key， 当设置content时，类型必须为bytes
                        例如: files: [ {"name":"file", "filename":"name.txt", "content":"xxx"} ...]  设置第一个item的filename -> [0, "filename"]

            value - str, 要设置的值

        Raises:
            exceptions.DataParamError - 参数错误引发此异常
        """
        if para_type == "cookies":
            self.http_data["cookies"][para_name] = urllib.parse.quote(value)
        elif para_type == "get":
            self.http_data["params"][para_name] = value
        elif para_type == "post":
            self.http_data["data"][para_name] = value
        elif para_type == "headers":
            self.http_data["headers"][para_name] = urllib.parse.quote(value)
        elif para_type == "json":
            # 如果para_name为空，将root节点为设为value
            if len(para_name) == 0:
                self.http_data["json"] = value
                return
            json_target = self.http_data["json"]
            for i in range(len(para_name)):
                name = para_name[i]
                obj = json_target.get(name, None)
                if len(para_name) == i + 1:
                    json_target[name] = value
                elif obj is None:
                    if type(para_name[i]) is int:
                        json_target[name] = []
                    else:
                        json_target[name] = {}
        elif para_type == "files":
            if para_name[1] == "content" and type(value) is not bytes:
                Logger().error("RequestData files content must set with bytes type!")
                raise exceptions.DataParamError
            else:
                self.http_data["files"][para_name[0]][para_name[1]] = value
        elif para_type == "body":
            self.http_data["body"] = value
        else:
            Logger().error("Use an invalid para_type in set_param method!")
            raise exceptions.DataParamError

    def get_content_type(self):
        """
        获取请求的content-type

        Returns:
            str, content-type
        """
        return self.content_type

    def get_param(self, para_type, para_name):
        """
        获取HTTP请求的某个变量

        Parameters:
            para_type - str, 参数类型，可选get, post, cookies, headers, json, files, body
            para_name - str, 参数名, 当para_type为json时, para_name应为一个list,包含json path每一级的key
                        当para_type为files时, para_name应为一个包含两个item的list, 第一个指定要获取的files dict的下标, 第二个指定在dict中获取的key, 同set_param

        Returns:
            获取目标变量的值

        Raises:
            exceptions.DataParamError - 参数错误引发此异常
        """
        if para_type == "cookies":
            return self.http_data["cookies"].get(para_name, None)
        elif para_type == "get":
            return self.http_data["params"].get(para_name, None)
        elif para_type == "post":
            return self.http_data["data"].get(para_name, None)
        elif para_type == "headers":
            return self.http_data["headers"].get(para_name, None)
        elif para_type == "json":
            json_target = self.http_data["json"]
            for name in para_name:
                json_target = json_target[name]
            return json_target
        elif para_type == "files":
            return self.http_data["files"][para_name[0]][para_name[1]]
        elif para_type == "body":
            return self.http_data["body"]
        else:
            Logger.error("Use an invalid para_type in get_param method!")
            raise exceptions.DataTypeNotExist

    def get_all_param(self, param_type_list=None):
        """
        获取当前http请求的所有变量

        Parameters:
            param_type_list - list, 获取的参数类型列表，可以包含"get"、"post"、"json"、"headers"、"cookies"、"files"、"body"
                默认为None时获取 "get" "post" "json" "headers" "cookie" 五类参数

        Returns:
            dict，变量类型para_type为key, 类型对应的变量集合为value，
            json类型value与json相同, 
            files类型value为包含name、filename、content三个key的dict
            其余value为dict类型
        """
        if param_type_list is None:
            param_type_list = ["get", "post",
                               "json", "headers", "cookie", "json"]
        result = {}
        if "get" in param_type_list:
            result["get"] = self.http_data["params"]
        if "post" in param_type_list:
            result["post"] = self.http_data["data"]
        if "headers" in param_type_list:
            result["headers"] = copy.deepcopy(self.http_data["headers"])
        if "json" in param_type_list and self.http_data["json"] is not None:
            result["json"] = self.http_data["json"]
        if "cookies" in param_type_list:
            if self.http_data["cookies"] is not None:
                result["cookies"] = self.http_data["cookies"]
        if "files" in param_type_list and len(self.http_data["files"]) > 0:
            if len(self.http_data["files"]) > 0:
                result["files"] = self.http_data["files"]
        if "body" in param_type_list and self.http_data["body"] is not None:
            result["body"] = {"body": self.http_data["body"]}
        return result

    def get_aiohttp_param(self):
        """
        获取调用aiphttp发送http请求相关方法所需的参数

        Returns:
            dict, 字典形式的参数
        """
        result = {
            "url": self.http_data["url"],
            "headers": self.http_data["headers"],
            "params": self.http_data["params"],
            "cookies": self.http_data["cookies"]
        }
        if self.content_type.startswith("application/json"):
            result["json"] = self.http_data["json"]
        elif self.content_type.startswith("multipart/form-data"):
            result["data"] = self._make_multipart()
            if self.http_data["headers"].get("content-type", None) is not None:
                del result["headers"]["content-type"]
        elif self.http_data["body"] is not None:
            result["data"] = self.http_data["body"]
        else:
            result["data"] = self.http_data["data"]
        return result

    async def get_aiohttp_raw(self):
        """
        获取调用aiphttp发送http请求时发送的raw request

        Returns:
            str - raw request
        """
        class Writer():
            def __init__(self):
                self.body = b""

            async def write(self, body_str):
                """
                用于MultipartWriter调用
                """
                self.body += body_str

            def get_body(self):
                """
                获取输出
                """
                return self.body

        if self.content_type.startswith("application/json"):
            body = json.dumps(self.http_data["json"])
        elif self.content_type.startswith("multipart/form-data"):
            body = self._make_multipart()
            w = Writer()
            await body.write(w)
            body = w.get_body()
            try:
                body = body.decode("utf-8")
            except UnicodeDecodeError:
                body = body.decode("latin-1")
        elif self.http_data["body"] is not None:
            body = self.http_data["body"]
            try:
                body = body.decode("utf-8")
            except UnicodeDecodeError:
                body = body.decode("latin-1")
        else:
            body = ""
            for key, value in self.http_data["data"].items():
                body += "{}={}&".format(key, value)
            body = body[:-1]

        parse_result = urllib.parse.urlparse(self.http_data["url"])
        raw_request = []
        raw_request.append(self.method.upper() + " " + parse_result.path + "?" + parse_result.query + " HTTP/1.1")
        for key in self.http_data["headers"]:
            raw_request.append(key + ": " + self.http_data["headers"][key])

        if self.http_data["cookies"] is not None:
            cookie_obj = http.cookies.SimpleCookie()
            cookie_obj.load(self.http_data["cookies"])
            output = cookie_obj.output().split("\r\n")
            cookie = "Cookie: "
            for item in output:
                cookie += item[12:] + ";"
            raw_request.append(cookie)

        raw_request.append("")
        raw_request.append(body)
        raw_request = "\r\n".join(raw_request)
        return raw_request

    def get_method(self):
        """
        获取当前请求的http方法名

        Returns:
            str, 小写方法名
        """
        return self.method

    def gen_scan_request_id(self):
        """
        生成扫描请求的id，并写入http header的scan-request-id字段

        Returns:
            str, 生成的id
        """
        uuid = common.generate_uuid()
        scan_id = self.queue_id + "-" + uuid
        self.http_data["headers"]["scan-request-id"] = scan_id
        return scan_id

    def is_param_concat_in_hook(self, hook_type, param_value):
        """
        判断参数值与hook点参数是否存在相似部分

        Parameters:
            hook_type - str, 检查的hook点类型
            param_value - str, 参数值

        Returns:
            Boolean
        """
        if len(param_value) == 0:
            return False

        hook_info = self.rasp_result_ins.get_hook_info()

        for hook_item in hook_info:
            if hook_item["hook_type"] == hook_type:
                if hook_type in ("command", "sql"):
                    if self._is_token_concat(param_value, hook_item["tokens"]):
                        return True
                    if "env" in hook_item:
                        for env_item in hook_item["env"]:
                            env_part = env_item.split("=")
                            for part in env_part:
                                if str(param_value).find(str(part)) >= 0:
                                    return True
                elif hook_type in ("ssrf", "include"):
                    if self._is_url_concat(param_value, hook_item["url"]):
                        return True
                elif hook_type in ("directory", "readFile", "writeFile"):
                    if self._is_url_concat(param_value, hook_item["path"]):
                        return True
                else:
                    hook_item_map = {
                        "webdav": ["source", "dest"],
                        "fileUpload": ["filename"],
                        "rename": ["source", "dest"],
                        "xxe": ["entity"],
                        "ognl": ["expression"],
                        "deserialization": ["clazz"],
                        "eval": ["code"]
                    }
                    for key in hook_item_map[hook_type]:
                        if hook_item[key].find(str(param_value)) >= 0:
                            return True
        return False

    def _split_str_word(self, input_str):
        """
        按照单词和符号分割字符串

        Parameters:
            input_str - str, 待分割字符串

        Returns:
            list - 分割后的字符串
        """
        split_value = []
        char = input_str[0]
        if char > '\xff' or re.search(r'[a-zA-Z0-9_]', char):
            word = True
        else:
            word = False
        start = 0
        index = 0
        for char in input_str:
            if char > '\xff' or re.search(r'[a-zA-Z0-9_]', char):
                word_char = True
            else:
                word_char = False

            if word != word_char:
                split_value.append(input_str[start:index])
                word = not word
                start = index
            index += 1
        if index - start >= 3:
            split_value.append(input_str[start:])

        return split_value

    def _is_token_concat(self, param_value, tokens):
        """
        判断token是否被参数影响

        Parameters:
            param_value - str, 参数值
            tokens - token列表，由iast.js的tokenize获取

        Returns:
            Boolean
        """
        param_value = param_value.strip()
        for token in tokens:
            if len(token["text"]) >= len(param_value) and token["text"].find(param_value) != -1:
                return True

        split_value = self._split_str_word(param_value)
        if len(param_value) > 3:
            for token in tokens:
                for item in split_value:
                    if len(token["text"]) * len(item) < 10000:
                        if len(token["text"]) <= 3:
                            if param_value.find(token["text"]) != -1:
                                return True
                        else:
                            cs = common.lcs(token["text"], item)
                            if len(cs) > 3:
                                return True
                    elif len(token["text"]) >= len(item) and token["text"].find(item) != -1:
                        return True
        return False

    def _is_url_concat(self, param_value, url):
        """
        判断url是否被参数影响

        Parameters:
            param_value - str, 参数值
            url - str, url

        Returns:
            Boolean
        """
        try:
            parse_result = urllib.parse.urlparse(url)
            url_items = {
                "scheme": parse_result.scheme,
                "netloc": parse_result.netloc,
                "path": parse_result.path,
                "query": parse_result.query
            }
        except Exception as e:
            return False

        for key in url_items:
            if url_items[key].find(param_value) != -1:
                return True

        if len(param_value) > 3:
            for key in url_items:
                path_part = url_items[key].replace("\\", "/").split("/")
                split_value = self._split_str_word(param_value)
                for item in split_value:
                    for part in path_part:
                        if len(part) * len(item) < 10000:
                            cs = common.lcs(part, item)
                            if len(cs) > 3:
                                return True
                        elif len(part) >= len(item) and part.find(item) != -1:
                            return True
        return False

    def get_payload_info(self):
        """
        获取当前请求的payload信息

        Returns:
            dict, 当前请求的payload信息
        """
        return self.payload_info

    def set_response(self, response):
        """
        设置请求的response

        Parameters:
            status_code - int, http状态码
            headers - dict, http头信息
            body - bytes, http body
        """
        self.response["status"] = response["status"]
        self.response["headers"] = response["headers"]
        self.response["body"] = response["body"]

    def get_response(self):
        """
        获取请求的response

        Returns:
            dict, 格式：
            {
                "status_code": 200,  # int, http状态码
                "headers": {"host":"localhost", ...},  # dict, http头信息
                "body": b"xxxx"  # bytes, http body
            }
        """
        return self.response

    def set_rasp_result(self, rasp_result):
        """
        添加请求对应的rasp_result

        Parameters:
            rasp_result - RaspResult实例
        """
        self.rasp_result = rasp_result

    def get_rasp_result(self):
        """
        获取请求对应的rasp_result, 未设置时返回None

        Reuters:
            RaspResult实例
        """
        return self.rasp_result

