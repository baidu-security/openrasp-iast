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

import time
import asyncio
import collections

from core.components import exceptions
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class RaspResultReceiver(object):
    """
    缓存扫描请求的RaspResult, 并通知对应扫描进程获取结果
    """

    def __new__(cls):
        """
        单例模式初始化
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(RaspResultReceiver, cls).__new__(cls)
            # 以 request_id 为key ,每个item为一个list，结构为: [获取到result的event, 过期时间, 获取到的结果(未获取前为None)]
            # 例如 {scan_request_id_1: [event_1, expire_time1, result_dict_1] , scan_request_id_2:[event_2, expire_time2, None] ...}
            cls.instance.rasp_result_collection = collections.OrderedDict()
            cls.instance.timeout = Config().get_config("scanner.request_timeout") * \
                (Config().get_config("scanner.retry_times") + 1)
        return cls.instance

    def register_result(self, req_id):
        """
        注册待接收的扫描请求的结果id，注册后调用wait_result等待返回结果

        Parameters:
            req_id - 结果的scan_request_id
        """
        expire_time = time.time() + (self.timeout * 2)
        self.rasp_result_collection[req_id] = [
            asyncio.Event(), expire_time, None]

    def add_result(self, rasp_result):
        """
        添加一个RaspResult实例到缓存队列并触发对应的数据到达事件, 同时清空缓存中过期的实例
        若RaspResult实例的id未通过register_result方法注册，则直接丢弃

        Parameters:
            rasp_result - 待添加的RaspResult实例
        """
        scan_request_id = rasp_result.get_scan_request_id()
        try:
            self.rasp_result_collection[scan_request_id][2] = rasp_result
            self.rasp_result_collection[scan_request_id][0].set()
        except KeyError:
            Communicator().increase_value("dropped_rasp_result")
            Logger().warning("Drop no registered rasp result data: {}".format(str(rasp_result)))

        while True:
            try:
                key = next(iter(self.rasp_result_collection))
            except StopIteration:
                break
            if self.rasp_result_collection[key][1] < time.time():
                if type(self.rasp_result_collection[key][0]) is not dict:
                    Logger().debug("Rasp result with id: {} timeout, dropped".format(key))
                self.rasp_result_collection.popitem(False)
            else:
                break

    async def wait_result(self, req_id):
        """
        异步等待一个扫描请求的RaspResult结果

        Parameters:
            req_id - str, 等待请求的scan_request_id

        Returns:
            获取到的扫描请求结果的RaspResult实例

        Rasise:
            exceptions.GetRaspResultFailed - 等待超时或请求id未使用register_result方法注册时引发此异常

        """
        try:
            expire_time = self.rasp_result_collection[req_id][1]
            event = self.rasp_result_collection[req_id][0]
        except KeyError:
            Logger().warning("Try to wait not exist result with request id " + req_id)
            raise exceptions.GetRaspResultFailed
        else:
            if type(event) == dict:
                return event
            timeout = expire_time - time.time()
            timeout = timeout if timeout > 0 else 0.01
        try:
            Logger().debug("Start waiting rasp result, id: " + req_id)
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            Logger().warning("Timeout when wait rasp result, id: " + req_id)
            Communicator().increase_value("rasp_result_timeout")
            raise exceptions.GetRaspResultFailed
        else:
            result = self.rasp_result_collection.get(
                req_id, (None, None, None))[2]
            Logger().debug("Got rasp result, scan-request-id: {}".format(req_id, str(result)))
            return result
