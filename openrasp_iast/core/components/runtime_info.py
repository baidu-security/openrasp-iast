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
import psutil
import threading

from core.components import common
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class RuntimeInfo(object):
    """
    用于监控模块的运行状态信息
    """
    def __new__(cls):
        """
        单例模式初始化
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(RuntimeInfo, cls).__new__(cls)
            cls.instance.history_num = 2
            cls.instance.lock = threading.Lock()
            cls.instance.system_info = {
                "cpu": 0,
                "mem": 0
            }
            cls.instance.psutil_proc_dict = {}
            cls.instance._init_history()
        return cls.instance

    def _init_history(self):
        """
        初始化状态历史信息
        """
        self.history_info = [None] * self.history_num
        for i in range(self.history_num):
            self.refresh_info()

    def _refresh_system_info(self):
        """
        刷新系统资源使用信息
        """
        self.system_info["cpu"] = psutil.cpu_percent(interval=None)
        self.system_info["mem"] = psutil.virtual_memory().percent

    def _get_module_proc(self, pid, module_name):
        """
        初始化并缓存module进程和子进程对应的psutil.Process实例

        Parameters:
            pid - int, module进程的pid
            module_name - str, 模块名
        """
        proc = psutil.Process(pid)
        subproc_list = proc.children()
        self.psutil_proc_dict[module_name] = {
            "pid": pid,
            "proc": proc,
            "subprocs": subproc_list
        }

    def _get_psutil_proc(self, pid, module_name):
        """
        初始化并缓存module进程和子进程对应的psutil.Process实例，若已缓存，则直接返回缓存的实例

        Parameters:
            pid - int, module进程的pid
            module_name - str, 模块名

        Returns:
            dict, 结构为
            {
                "pid": 主进程pid,
                "proc": 主进程psutil.Process实例
                "subprocs": 子进程psutil.Process实例列表
            }
        """
        if ((module_name not in self.psutil_proc_dict) or (not self.psutil_proc_dict[module_name]["proc"].is_running())):
            self._get_module_proc(pid, module_name)
        else:
            module_proc = self.psutil_proc_dict[module_name]
            if len(module_proc["subprocs"]) != len(module_proc["proc"].children()):
                self._get_module_proc(pid, module_name)
            else:
                for proc in self.psutil_proc_dict[module_name]["subprocs"]:
                    if not proc.is_running():
                        self._get_module_proc(pid, module_name)
                        break
        return self.psutil_proc_dict[module_name]

    def refresh_info(self):
        """
        获取当前所有模块的运行状态，并存入历史记录
        """
        self._refresh_system_info()
        shared_info = Communicator().dump_shared_mem()
        for module_name in shared_info:
            try:
                pid = shared_info[module_name]["pid"]
                if pid == 0:
                    continue
                module_procs = self._get_psutil_proc(pid, module_name)
                psutil_proc = module_procs["proc"]
                sub_procs = module_procs["subprocs"]
                cpu = psutil_proc.cpu_percent(interval=None)
                mem = psutil_proc.memory_info().rss
                for subproc in sub_procs:
                    try:
                        cpu += subproc.cpu_percent(interval=None)
                        mem += subproc.memory_info().rss
                    except Exception:
                        pass
                shared_info[module_name]["cpu"] = str(cpu) + "%"
                shared_info[module_name]["mem"] = common.bytes2human(mem)
            except psutil.Error as e:
                Logger().warning("Detect module {} may exited!".format(module_name))
                if module_name != "Preprocessor":
                    Communicator().set_value("pid", 0, module_name)
                    shared_info[module_name]["cpu"] = -1
                    shared_info[module_name]["mem"] = -1
        with self.lock:
            self.history_info.pop(0)
            self.history_info.append(shared_info)

    def get_value(self, module_name, key):
        """
        获取指定模块的指定运行状态变量

        Parameters:
            module_name - str, 获取的模块名
            key - str, 获取的变量名
        
        Returns:
            变量值，int 或 String
        """
        with self.lock:
            return self.history_info[-1][module_name][key]

    def get_value_in_history(self, module_name, key):
        """
        获取指定模块的指定运行状态变量在历史记录中的所有值

        Parameters:
            module_name - str, 获取的模块名
            key - str, 获取的变量名
        
        Returns:
            list, item为变量值，int 或 String类型，时间顺序排列
        """
        result = []
        with self.lock:
            for his_item in self.history_info:
                result.append(his_item[module_name][key])
        return result

    def get_system_info(self):
        """
        获取当前系统资源信息

        Returns:
            { 
                "cpu": int类型cpu使用率,
                "mem": int类型内存rss使用率
            }
        """
        return {
            "cpu": self.system_info["cpu"],
            "mem": self.system_info["mem"]
        }

    def get_latest_info(self):
        """
        获取最近一次的刷新获得的状态信息

        Returns:
            dict, 结构
            {
                "模块名":{模块信息key:value, ...},
                ...
            }
        """
        with self.lock:
            return copy.deepcopy(self.history_info[-1])

    def get_all_history(self):
        """
        获取全部历史记录

        Returns:
            list, 每个item为
            {
                "模块名":{模块信息key:value, ...},
                ...
            }
        """
        result = []
        with self.lock:
            for i in range(self.history_num):
                result.append(copy.deepcopy(self.history_info[-i]))
        return result
