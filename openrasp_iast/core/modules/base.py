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
import time
import threading
import multiprocessing


from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class BaseModule(object):
    """
    module的基础类，所有module继承自此类
    """

    def run(self):
        """ 新进程的入口函数 """
        raise NotImplementedError


class Process(multiprocessing.Process):
    """
    对multiprocessing.Process的封装, 用于启动module的进程
    """

    def __init__(self, module_cls, instance_id=None, module_params={}):
        assert issubclass(module_cls, BaseModule)
        self.module_cls = module_cls
        self.module_name = module_cls.__name__
        self.module_params = module_params
        if instance_id != None:
            self.module_name += "_" + str(instance_id)
        super(Process, self).__init__(name=self.module_name, daemon=True)

    def run(self):
        """ 初始化并启动module线程 """
        Communicator().init_new_module(self.module_name)
        Communicator().set_value("pid", os.getpid())
        Logger().init_module_logger()
        Logger().debug("Init proc_comm success, current module_name is: " +
                       Communicator().get_module_name())
        try:
            self._run_module()
        except KeyboardInterrupt:
            pass

    def _run_module(self):
        """ module线程主函数 """
        try:
            Logger().info("Module started!")
            module = self.module_cls(**self.module_params)
            module.run()
        except Exception as e:
            Logger().error("Module down with exception:", exc_info=e)
        else:
            Logger().info("Module stopped!")
