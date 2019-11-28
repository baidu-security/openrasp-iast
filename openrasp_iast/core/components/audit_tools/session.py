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

import aiohttp
import asyncio

from core.components import exceptions
from core.components.logger import Logger
from core.components.config import Config
from core.components.audit_tools import context


class Session(object):
    """
    用于发送http请求的session，一个扫描模块所有协程共用一个session
    """

    async def async_init(self):
        """
        初始化
        """
        cookie_jar = aiohttp.DummyCookieJar()
        conn = aiohttp.TCPConnector(limit=0)
        timeout = aiohttp.ClientTimeout(
            total=Config().get_config("scanner.request_timeout"))
        self.session = aiohttp.ClientSession(
            cookie_jar=cookie_jar,
            connector=conn,
            timeout=timeout
        )

    async def close(self):
        """
        关闭session
        """
        await self.session.close()

    async def send_request(self, request_data_ins, proxy_url=None):
        """
        异步发送一个http请求, 返回结果

        Parameters:
            request_data_ins - request_data.RequestData类的实例，包含请求的全部信息
            proxy_url - 发送请求使用的代理url, 为None时不使用代理

        Returns:
            dict, 结构:
            {
                "raw_request": 完整的raw http请求包
                "status": http响应码,
                "headers": http响应头的dict,
                "body": http响应body, bytes
            }

        Raises:
            exceptions.ScanRequestFailed - 请求发送失败时引发此异常
        """
        http_func = getattr(self.session, request_data_ins.get_method())
        request_params_dict = request_data_ins.get_aiohttp_param()
        retry_times = Config().get_config("scanner.retry_times")
        while retry_times >= 0:
            try:
                async with context.Context():
                    async with http_func(**request_params_dict, proxy=proxy_url, allow_redirects=False, ssl=False) as response:
                        response = {
                            "status": response.status,
                            "headers": response.headers,
                            "body": await response.read()
                        }
                        break
            except (asyncio.TimeoutError, aiohttp.client_exceptions.ClientError) as e:
                Logger().warning("Send scan request timeout, retrying! request params:{}".format(request_params_dict))
                await asyncio.sleep(1)
                retry_times -= 1
            except asyncio.CancelledError as e:
                raise e
            except Exception as e:
                Logger().error("Send scan request failed!", exc_info=e)
                await asyncio.sleep(1)
                retry_times -= 1
        if retry_times >= 0:
            return response
        else:
            Logger().warning("Scan request timeout many times, this request will be skipped! request params:{}".format(request_params_dict))
            raise exceptions.ScanRequestFailed
