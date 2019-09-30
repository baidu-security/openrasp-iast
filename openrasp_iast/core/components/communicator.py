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

import os
import time
import multiprocessing

from core.components import common
from core.components import exceptions
from core.components.config import Config


class Communicator(object):

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(Communicator, cls).__new__(cls)
            cls.instance.scanner_num = Config().get_config("scanner.max_module_instance")
            cls.instance.pre_http_num = Config().get_config("preprocessor.process_num")
            cls.instance._init_queues()
            cls.instance._init_shared_mem()
            cls.instance._init_shared_setting()
            cls.instance._init_main_path()
            cls.instance.init_new_module("MainProcess")
        return cls.instance

    @classmethod
    def reset(cls):
        """
        用于重置Communicator实例
        """
        if hasattr(cls, "instance"):
            del cls.instance

    def _init_shared_mem(self):
        self.pre_http_lock = self.read_lock = multiprocessing.Lock()

        preprocessor_keys = [
            "pid",
            "invalid_data",  # non-json or json format err data
            "duplicate_request",
            "new_request",
            "rasp_result_request"
        ]

        for i in range(self.pre_http_num):
            preprocessor_keys.append("http_server_pid_" + str(i))

        monitor_keys = [
            "pid",
            "shared_setting_version",
            "auto_start"
        ]

        scanner_keys = [
            "pid",
            "max_concurrent_request",
            "request_interval",
            "rasp_result_timeout",
            "waiting_rasp_request",
            "dropped_rasp_result",
            "send_request",
            "failed_request",
            "pause",  # 扫描器暂停标识，不为0时暂停扫描
            "cancel",  # 扫描器退出标识，不为0时停止扫描
            "config_version"
        ]

        data_struct = {
            "Preprocessor": dict.fromkeys(preprocessor_keys),
            "Monitor": dict.fromkeys(monitor_keys)
        }
        for i in range(self.scanner_num):
            data_struct["Scanner_" + str(i)] = dict.fromkeys(scanner_keys)

        self.shared_mem = SharedMem(data_struct)

    def _is_pid_exists(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def set_pre_http_pid(self, pid):
        with self.pre_http_lock:
            for i in range(self.pre_http_num):
                value = self.get_value(
                    "http_server_pid_" + str(i), "Preprocessor")
                if value == 0 or not self._is_pid_exists(value):
                    self.set_value("http_server_pid_" +
                                   str(i), pid, "Preprocessor")
                    return True
        return False

    def get_pre_http_pid(self):
        result = []
        for i in range(self.pre_http_num):
            result.append(self.get_value(
                "http_server_pid_" + str(i), "Preprocessor"))
        return result

    def _init_queues(self):
        self.queues = {}
        for i in range(self.scanner_num):
            self.queues["rasp_result_queue_" + str(i)] = OriQueue()

    def _init_shared_setting(self):
        self.shared_setting_obj = OriSharedObj()
        self._reset_shared_setting()
        self.shared_setting_obj.set_obj(self.shared_setting)

    def _init_main_path(self):
        file_path = os.path.abspath(__file__)
        main_path = os.path.dirname(file_path) + "/../../"
        self._main_path = os.path.realpath(main_path)

    def get_main_path(self):
        """
        获取当前代码根目录的绝对路径
        """
        return self._main_path

    def init_new_module(self, module_name):
        """
        设置当前module名,重置非共享的模块配置

        Parameters:
            module_name - 设置的module名
        """
        self.module_name = module_name
        self._reset_shared_setting()
        self.internal_shared = {}

    def set_internal_shared(self, key, value):
        """
        设置一个模块内全局变量的值

        Parameters:
            key - 变量名
            value - 变量值，可以是任意类型
        """
        self.internal_shared[key] = value

    def get_internal_shared(self, key):
        """
        获取一个模块内全局变量的值

        Parameters:
            key - 变量名

        Returns:
            对应的变量值
        """
        try:
            return self.internal_shared[key]
        except KeyError:
            raise exceptions.InternalSharedKeyError

    def get_module_name(self):
        """
        获取当前module名

        Returns:
            当前module名，String类型
        """
        return self.module_name

    def get_module_id(self):
        """
        获取当前module id,仅用于多实例module

        Returns:
            当前module id，String类型
        """
        return self.module_name.split("_")[-1]

    def get_module_cls_name(self):
        """
        获取当前module对应的class名

        Returns:
            当前module对应的class名，String类型
        """
        return self.module_name.split("_")[0]

    def _reset_shared_setting(self):
        self.shared_setting = {
            "lru_clean": {}
        }
        self.setting_version = 0

    def _clean_timeout_setting(self):
        time_now = time.time()
        for item in self.shared_setting:
            keys = self.shared_setting[item].keys()
            pop_key = []
            for key in keys:
                if self.shared_setting[item][key]["timeout"] < time_now:
                    pop_key.append(key)
            for key in pop_key:
                self.shared_setting[item].pop(key)

    def set_clean_lru(self, host_port_list):
        """
        向preprocessor模块下发清空lru配置

        Parameters:
            host_port_list - 需要清空lru的扫描目标列表, item为字符串host_port形式，如127.0.0.1_8005
        """
        version = self.get_value("shared_setting_version", "Monitor") + 1
        self._clean_timeout_setting()
        for host_port in host_port_list:
            self.shared_setting["lru_clean"][host_port] = {
                "version": version,
                "timeout": time.time() + 300
            }
        self.shared_setting_obj.set_obj(self.shared_setting)
        self.add_value("shared_setting_version", "Monitor", 1)

    def get_preprocessor_action(self):
        """
        preprocessor模块用于获取Monitor下发的指令

        Returns:
            用于表示指令的action字典，没有新指令时返回None
        """
        if self.setting_version < self.get_value("shared_setting_version", "Monitor"):
            setting = self.shared_setting_obj.get_obj()
            max_version = 0
            action = {
                "lru_clean": []
            }
            for item in setting["lru_clean"]:
                version = setting["lru_clean"][item]["version"]
                if version > self.setting_version:
                    action["lru_clean"].append(item)
                if version > max_version:
                    max_version = version

            self.setting_version = max_version
            return action
        else:
            return None

    def increase_value(self, key):
        """
        对当前module的指定key的值执行+=1运算

        Parameters:
            key - 进行+=1的key
        """
        self.shared_mem.add_value(self.module_name, key, 1)

    def decrease_value(self, key):
        """
        对当前module的指定key的值执行-=1运算

        Parameters:
            key - 进行-=1的key
        """
        self.shared_mem.add_value(self.module_name, key, -1)

    def add_value(self, key, module_name, value):
        """
        对指定module的指定key的值执行+=value运算

        Parameters:
            key - value对应的key
            value - 增加的value，可以是负数
            module_name - key所在的模块名，默认使用当前进程的module的module_name
        """
        self.shared_mem.add_value(module_name, key, value)

    def get_value(self, key, module_name=None):
        """
        获取指定module的指定key的值

        Parameters:
            key - value对应的key
            value - 设置的value
            module_name - key所在的模块名，默认使用当前进程的module的module_name

        Returns:
            返回获取到的value值
        """
        if module_name is None:
            module_name = self.module_name
        return self.shared_mem.get_value(module_name, key)

    def dump_shared_mem(self):
        """
        获取共享内存的一份拷贝

        Returns:
            {module_name:{key:value}}形式的2层字典
        """
        module_name_list = self.shared_mem.get_all_module_name()
        result = {}
        for module_name in module_name_list:
            result[module_name] = self.shared_mem.get_all_value(module_name)
        return result

    def set_value(self, key, value, module_name=None):
        """
        设置某个共享内存的value

        Parameters:
            key - value对应的key
            value - 设置的value
            module_name - key所在的模块名，默认使用当前进程的module的module_name

        """
        if module_name is None:
            module_name = self.module_name
        self.shared_mem.set_value(module_name, key, value)

    def reset_all_value(self, module_name=None):
        """
        重置某个模块的全部共享内存的value为0

        Parameters:
            module_name - 重置的模块名，默认使用当前进程的module的module_name

        """
        if module_name is None:
            module_name = self.module_name
        self.shared_mem.reset_all_value(module_name)

    def send_data(self, queue_name, data):
        """
        向指定队列发送数据，不产生阻塞

        Parameters:
            queue_name - 目标队列名
            data - 发送的数据
        """
        if queue_name in self.queues:
            self.queues[queue_name].put(data)
        else:
            raise exceptions.QueueNotExist

    def get_data(self, queue_name):
        """
        从指定队列获取数据，阻塞模式

        Parameters:
            queue_name - 目标队列名

        Returns:
            返回获取到的数据
        """
        return self.queues[queue_name].get()

    def get_data_nowait(self, queue_name):
        """
        从指定队列获取数据，非阻塞模式

        Parameters:
            queue_name - 目标队列名

        Returns:
            返回获取到的数据

        Raises:
            目标队列为空则产生exceptions.QueueEmpty异常
        """
        return self.queues[queue_name].get_nowait()


class OriQueue(object):

    def __init__(self):
        self.uuid = common.generate_uuid()
        self.read_lock = multiprocessing.Lock()
        self.write_lock = multiprocessing.Lock()
        self.pipe_receiver, self.pip_sender = multiprocessing.Pipe(False)

    def get(self):
        with self.read_lock:
            data = self.pipe_receiver.recv()
            return data

    def get_nowait(self):
        with self.read_lock:
            if self.pipe_receiver.poll():
                data = self.pipe_receiver.recv()
                return data
            else:
                raise exceptions.QueueEmpty

    def put(self, data):
        with self.write_lock:
            try:
                self.pip_sender.send(data)
            except ValueError as e:
                raise exceptions.QueueValueError


class OriSharedObj(object):
    """
    用于进程间传递配置信息
    """

    def __init__(self):
        self.lock = multiprocessing.Lock()
        self.pipe_receiver, self.pip_sender = multiprocessing.Pipe(False)

    def get_obj(self):
        with self.lock:
            if self.pipe_receiver.poll():
                obj = self.pipe_receiver.recv()
                self.pip_sender.send(obj)
                return obj
            else:
                raise exceptions.SharedSettingError

    def set_obj(self, obj):
        with self.lock:
            while self.pipe_receiver.poll():
                self.pipe_receiver.recv()
            self.pip_sender.send(obj)


class SharedMem(object):

    def __init__(self, data_struct):
        self._data_index = data_struct
        data_index = 0
        self._module_locks = {}
        for module in self._data_index:
            self._module_locks[module] = multiprocessing.Lock()
            for key in self._data_index[module]:
                self._data_index[module][key] = data_index
                data_index += 1
        self.shared_array = multiprocessing.Array('l', data_index)

    def get_all_module_name(self):
        return self._data_index.keys()

    def reset_all_value(self, module):
        module = self._data_index[module]
        for key in module:
            self.shared_array[module[key]] = 0

    def get_all_value(self, module):
        result = {}
        for key in self._data_index[module]:
            with self._module_locks[module]:
                result[key] = self.shared_array[self._data_index[module][key]]
        return result

    def add_value(self, module, key, value=1):
        with self._module_locks[module]:
            self.shared_array[self._data_index[module][key]] += value

    def get_value(self, module, key):
        value = self.shared_array[self._data_index[module][key]]
        return value

    def set_value(self, module, key, value):
        with self._module_locks[module]:
            self.shared_array[self._data_index[module][key]] = value
