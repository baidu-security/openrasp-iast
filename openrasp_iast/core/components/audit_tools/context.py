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
import asyncio

from core.components.communicator import Communicator


class Context(object):
    """
    HTTP请求上下文，用于统计和控制请求发送
    """
    def __new__(cls):
        """
        单例模式
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Context, cls).__new__(cls)
            cls.instance.current_requests_num = 0
        return cls.instance

    async def async_init(self):
        """
        事件循环内的初始化，仅需要调用一次
        """
        self.request_end_event = asyncio.Event()

    def _is_req_reach_limit(self):
        """
        判断并发请求是否到达上限

        Returns:
            boolean
        """
        max_req = Communicator().get_value("max_concurrent_request")
        if self.current_requests_num >= max_req:
            return True
        else:
            return False

    async def __aenter__(self):
        while self._is_req_reach_limit():
            Communicator().increase_value("waiting_rasp_request")
            self.request_end_event.clear()
            await self.request_end_event.wait()
            self.request_end_event.clear()
            Communicator().decrease_value("waiting_rasp_request")
        self.current_requests_num += 1
        Communicator().increase_value("send_request")

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            Communicator().increase_value("failed_request")
        request_interval = Communicator().get_value("request_interval")
        if request_interval > 0:
            await asyncio.sleep(request_interval / 1000)
        self.request_end_event.set()
        self.current_requests_num -= 1
