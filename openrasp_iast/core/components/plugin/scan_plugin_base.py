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
import sys
import copy
import queue
import types
import asyncio
import aiohttp

from core.components import common
from core.components import exceptions
from core.components import audit_tools
from core.components import result_receiver
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class ScanPluginBase(object):

    plugin_info = {
        "name": "No_name_plugin",  # 使用数字字母下划线命名, 应与文件名（不含扩展名）相同
        "show_name": "No_show_name", # 插件在console展示时的名字, 自定义
        "description": "No description" # 插件描述
    }

    audit_tools = audit_tools 

    def __init__(self):
        """
        初始化
        """
        is_scanner = Communicator().get_module_name().startswith("Scanner")
        if is_scanner:
            self.logger = Logger().get_scan_plugin_logger(self.plugin_info["name"])
        else:
            self.logger = Logger()
        
        self._enable = True # 插件是否启用
        self._white_reg = None # 扫描url白名单
        self._proxy_url = None # 扫描使用的代理
        self._scan_queue = queue.Queue() # 任务队列
        self._last_scan_id = 0 # 最近扫描完成的任务在数据库中的id
        self._scan_num = 0 # 当前已扫描url数量
        self._request_timeout = Config().get_config("scanner.request_timeout")
        self._max_concurrent_task = Config().get_config("scanner.max_concurrent_request")

        # 共享的report_model 和 failed_task_set 需要在实例化ScanPluginBase类之前设置
        try:
            self._report_model = Communicator().get_internal_shared("report_model")
            self._failed_set = Communicator().get_internal_shared("failed_task_set")
        except exceptions.InternalSharedKeyError as e:
            Logger().error("Try to init scan_plugin before set internal shared key in Communicator! Check 'error.log' for more information.")
            sys.exit(1)

        self._request_session = audit_tools.Session()
        self._request_data = audit_tools.RequestData

        self.mutant_helper = audit_tools.MutantHelper()
        self.checker = audit_tools.Checker()

        if is_scanner:
            self.logger.info("Scanner plugin {} init success!".format(self.plugin_info["name"]))

    def get_scan_progress(self):
        """
        获取当前扫描进度

        Returns:
            扫描请求数，最近一个扫描完成的请求在数据库中的id
        """
        return self._scan_num, self._last_scan_id

    def get_max_concureent_task(self):
        """
        Returns:
            最大并发扫描线程数
        """
        return self._max_concurrent_task

    def set_enable(self, is_enable):
        """
        设置是否启用插件

        Parameters:
            is_enable - bool
        """
        self._enable = is_enable
    
    def set_white_url_reg(self, reg_str):
        """
        设置扫描url白名单, 为空时设置为None

        Parameters:
            reg_str - str
        """
        if reg_str == "":
            self._white_reg = None
        else:
            self._white_reg = re.compile(reg_str)
    
    def set_scan_proxy(self, proxy_url):
        """
        设置扫描代理, 为空时设置为None

        Parameters:
            reg_str - str
        """
        if proxy_url == "":
            self._proxy_url = None
        else:
            self._proxy_url = proxy_url

    async def async_run(self):
        """
        主函数，执行扫描任务
        """
        await self._request_session.async_init()
        self._scan_queue_event = asyncio.Event()
        while True:
            if not self._scan_queue.empty():
                self._has_failed_reuqest = False
                self._task = self._scan_queue.get_nowait()
                if self._enable:
                    rasp_result_ins = self._task["data"]
                    try:
                        await self._scan(self._task["id"], rasp_result_ins)
                    except asyncio.CancelledError as e:
                        raise e
                    except Exception as e:
                        self.logger.error("scanner plugin: [{}] error:".format(
                            self.plugin_info["name"]), exc_info=e)

                    if self._has_failed_reuqest:
                        self._failed_set.add(self._task["id"])

                self._last_scan_id = self._task["id"]
                self._scan_num += 1
            else:
                self._scan_queue_event.clear()
                await self._scan_queue_event.wait()
        # if break but not exit, do close
        await self._request_session.close()

    def add_task(self, task):
        """
        向扫描插件添加任务的接口

        Parameters:
            task - RaspResult实例，要添加的任务
        """
        self.logger.debug("Add task with id: {} to scan list.".format(task["id"]))
        self._scan_queue.put(task)
        self._scan_queue_event.set()

    def mutant(self, rasp_result_ins):
        """
        实现测试向量列表的生成

        Parameters:
            rasp_result_ins - 待扫描请求对应的RaspResult实例
        """
        raise NotImplementedError

    async def check(self, request_data_list):
        """
        实现测试向量列表的生成

        Parameters:
            check_target_list - 待扫检测的请求-结果列表
        """
        raise NotImplementedError

    def new_request_data(self, rasp_result_ins, payload_seq=None, payload_feature=None):
        """
        基于一个RaspResult实例创建一个core.components.audit_tools.RequestData实例

        Parameters:
            rasp_result_ins - RaspResult实例, 用于初始化core.components.audit_tools.RequestData实例
            payload_seq - string, 随机字符序列，用于区分当前请求正在被测试的参数防止多次报警
            payload_feature - 用于检测payload是否成功投放的特征
        
        Returns:
            创建的core.components.audit_tools.RequestData实例
        """
        return self._request_data(rasp_result_ins, payload_seq, payload_feature)

    def gen_payload_seq(self):
        """
        生成32位随机字符串

        Returns:
            str
        """
        return common.random_str(32)

    def _register_result(self, req_id):
        """
        封装RaspResultReceiver的方法
        """
        result_receiver.RaspResultReceiver().register_result(req_id)

    async def _wait_result(self, req_id):
        """
        封装RaspResultReceiver的方法
        """
        return await result_receiver.RaspResultReceiver().wait_result(req_id)

    async def send_request(self, request_data):
        """
        发送http请求，返回response、rasp_result组成的dict

        Parameters:
            request_data - core.components.audit_tools.request_data.RequestData 对象实例

        Returns:
            {
                "response": {
                    "status": HTTP状态码,
                    "headers": 返回包的headers字典,
                    "body": 返回包的body, bytes类型
                    }
                "rasp_result": core.components.rasp_result.RaspResult 对象实例，未获取到时为None
            }

        Raises:
            请求发送失败时，引发exceptions.ScanRequestFailed异常
            获取RaspResult失败时，引发exceptions.GetRaspResultFailed异常
        """

        request_id = request_data.gen_scan_request_id()
        self._register_result(request_id)
        try:
            self.logger.debug("Send scan request with id: {}, content: {}".format(request_id, request_data.get_aiohttp_param()))
            response = await self._request_session.send_request(request_data, self._proxy_url)
            self.logger.debug("Request with id: {} get response: {}".format(request_id, response))
            rasp_result_ins = await self._wait_result(request_id)
            self.logger.debug("Request with id: {} get rasp_result: {}".format(request_id, rasp_result_ins.dump()))
        except (exceptions.ScanRequestFailed, exceptions.GetRaspResultFailed) as e:
            self._has_failed_reuqest = True
            self.logger.debug("Request with id {} of task id {} has failed many times, skip!".format(request_id, self._task["id"]))
            raise e

        ret = {
            "response": response,
            "rasp_result": rasp_result_ins
        }
        return ret

    async def _scan(self, task_id, rasp_result_ins):
        """
        使用协程并行方式对mutant生成的请求进行发送和结果检测

        Parameters:
            task_id - int, 扫描task对应的id
            rasp_result_ins - RaspResult实例
        """
        if self._white_reg is not None:
            uri = rasp_result_ins.get_path() + "?" + rasp_result_ins.get_query_string()
            if self._white_reg.search(uri) is not None:
                self.logger.info("Skip task with task_id: {}, request_id:{}, url match white reg, request url:{}".format(
                    task_id,
                    rasp_result_ins.get_request_id(),
                    rasp_result_ins.get_url()
                ))
                return

        mutant_generator = self.mutant(rasp_result_ins)
        self.logger.info("Start task with task_id: {}, request_id:{}, url:{}".format(
                task_id,
                rasp_result_ins.get_request_id(),
                rasp_result_ins.get_url()
        ))
        self.logger.debug("request json: {}".format(rasp_result_ins.dump()))

        if not isinstance(mutant_generator, types.GeneratorType):
            self.logger.error("Scan plugin error, the mutant method should return a Generator!")
            return

        max_task = self.get_max_concureent_task()
        tasks = []
        for i in range(max_task):
            tasks.append(asyncio.create_task(self._test_mutant_task(mutant_generator)))
        for task in tasks:
            await task
        self.logger.info("Finish task with request_id:{}".format(rasp_result_ins.get_request_id()))

    async def _test_mutant_task(self, mutant_generator):
        """
        test_in_coroutine 方法使用的协程任务函数

        Parameters:
            mutant_generator - 测试请求序列生成器
        """
        while True:
            try:
                request_data_list = mutant_generator.__next__()
            except StopIteration:
                break

            try:
                for req_data in request_data_list:
                    ret = await self.send_request(req_data)
                    req_data.set_response(ret["response"])
                    self.logger.debug("Send scan request: {}".format(req_data.get_aiohttp_param()))
                    req_data.set_rasp_result(ret["rasp_result"])
            except (exceptions.ScanRequestFailed, exceptions.GetRaspResultFailed):
                continue

            message = self.check(request_data_list)
            if type(message) is str:
                if await self.report(request_data_list, message):
                    self.logger.info("Plugin {} find vuln!".format(self.plugin_info["name"]))

    async def report(self, request_data_list, message=""):
        """
        向扫描结果中添加一条漏洞信息

        Parameters:
            request_data_list - list, RequestData类的实例组成的列表, 发现漏洞的测试请求序列
            message - str, 漏洞描述信息

        Returns:
            bool, 成功写入(没有重复)返回true

        Raises:
            exceptions.DatabaseError - 数据库发生错误时引发
        """
        message = "OpenRASP-IAST漏洞扫描 - " + message
        return await self._report_model.put(request_data_list, self.plugin_info["name"], self.plugin_info["description"], message)
