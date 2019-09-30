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

import time
import queue
import multiprocessing

from core import modules
from core.components import exceptions
from core.modules.base import BaseModule
from core.components.logger import Logger


class ForkProxy(object):
    """
    用于代理启动模块
    """

    def __new__(cls):
        """
        单例模式初始化，必须由主进程初始化
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(ForkProxy, cls).__new__(cls)
            cls.instance.request_queue = multiprocessing.Queue()
            cls.instance.result_queue = multiprocessing.Queue()
        return cls.instance

    def listen(self):
        """
        监听创建模块进程队列，创建进程并返回pid
        """
        while True:
            process_kwargs = self.request_queue.get(True)
            try:
                proc = modules.Process(**process_kwargs)
                proc.start()
                pid = proc.pid
            except Exception as e:
                Logger().error("Fork proxy error when start new module!", exc_info=e)
                result = {"pid": 0}
            else:
                Logger().info("Fork module {} success with pid {}!".format(
                    process_kwargs["module_cls"].__name__, pid))
                result = {"pid": pid}
            self.result_queue.put(result)

    def fork(self, process_kwargs):
        """
        请求调用self.listen的进程创建一个基于core.module.base.BaseModule的模块进程

        Parameters:
            process_kwargs - 创建进程使用的参数，dict形式打包

        Returns:
            int, 创建的进程的pid

        Raises:
            exceptions.ForkModuleError - 创建进程失败引发
        """
        try:
            while True:
                self.result_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self.request_queue.put(process_kwargs)
            result = self.result_queue.get(True, 10)
            assert result["pid"] > 0
            return result["pid"]
        except Exception as e:
            Logger().error("Fork new module process failed!", exc_info=e)
            raise exceptions.ForkModuleError
