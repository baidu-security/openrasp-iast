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
import sys
import time
import json
import copy
import psutil

from core import modules
from core.components import common
from core.components import exceptions
from core.components.logger import Logger
from core.components.config import Config
from core.components.plugin import scan_plugin_base
from core.components.fork_proxy import ForkProxy
from core.components.runtime_info import RuntimeInfo
from core.components.communicator import Communicator
from core.model.base_model import BaseModel
from core.model.report_model import ReportModel
from core.model.config_model import ConfigModel
from core.model.new_request_model import NewRequestModel


class ScannerManager(object):

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(ScannerManager, cls).__new__(cls)
        return cls.instance

    def init_manager(self, scanner_schedulers):
        """
        初始化

        Parameters:
            scanner_schedulers - 所有扫描任务调度类组成的dict, key为扫描任务的Module_name
        """
        self._scanner_info = ScannerInfo()
        self._config = ScannerConfig(self._scanner_info, scanner_schedulers)
        self._target_status = TargetStatus()

    def new_scanner(self, module_params):
        """
        创建一个新的扫描任务

        Parameters:
            module_params - dict, 结构为{
                "host":str, 目标主机,
                "port":int, 目标端口
                "config": dict, 配置信息
            }

        Raises:
            exceptions.MaximumScannerExceede - 扫描任务数量到达上限，引发此异常
            exceptions.TargetIsScanning - 指定目标正在被其他任务扫描，引发此异常
        """

        host = module_params["host"]
        port = module_params["port"]
        host_port = common.concat_host(host, port)
        if self._scanner_info.is_scanning(host_port):
            raise exceptions.TargetIsScanning

        idle_scanner = self._scanner_info.get_idle_scanner()
        if idle_scanner is None:
            raise exceptions.MaximumScannerExceede

        # 确保数据库中存在扫描配置
        self._config.mod_config(host_port, {})

        # 启动扫描进程
        scanner_process_kwargs = {
            "module_cls": modules.Scanner,
            "instance_id": idle_scanner,
            "module_params": {
                "host": host,
                "port": port
            }
        }
        Communicator().reset_all_value("Scanner_" + str(idle_scanner))
        pid = ForkProxy().fork(scanner_process_kwargs)

        # 在共享内存中记录pid
        Communicator().set_value("pid", pid, "Scanner_" + str(idle_scanner))

        # 记录扫描器id相关信息
        self._scanner_info.set_scanner_info(idle_scanner, pid, host, port)

    def kill_scanner(self, scanner_id):
        """
        强制结束一个扫描进程进程

        Parameters:
            scanner_id - int类型, 要结束的扫描进程的id

        Returns:
            成功结束返回True，否则返回false

        """
        pid = self._scanner_info.get_pid(scanner_id)
        if pid is None:
            raise exceptions.InvalidScannerId

        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            Logger().warning("Try to kill not running scanner!")
            raise exceptions.InvalidScannerId
        proc.terminate()

        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        if proc.is_running():
            return False
        else:
            self._scanner_info.remove_scanner_info(scanner_id)
            module_name = "Scanner_" + str(scanner_id)
            Communicator().set_value("pid", 0, module_name)
            return True

    def clean_target(self, host, port, url_only=False):
        """
        清空目标对应的数据库，同时重置预处理lru

        Parameters:
            host - str, 目标host
            port - int, 目标port
            url_only - bool, 是否仅清空url

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        host_port = common.concat_host(host, port)
        if self._scanner_info.get_scanner_id(host_port) is not None:
            raise exceptions.TargetIsScanning
        if url_only:
            NewRequestModel(host_port, multiplexing_conn=True).truncate_table()
        else:
            NewRequestModel(host_port, multiplexing_conn=True).drop_table()
            ReportModel(host_port, multiplexing_conn=True).drop_table()
            self._config.del_config(host_port)
        Communicator().set_clean_lru([host_port])

    async def get_all_target(self, page=1):
        """
        获取数据库中存在的所有目标主机的列表

        Parameters:
            page - int, 获取的页码，每页10个主机

        Returns:
            list - 获取到的数据, int - 数据总数

            其中数据item为dict,格式为：
            正在扫描的item:
            {
                "id": 1, // 扫描任务id
                "pid": 64067, // 扫描进程pid
                "host": "127.0.0.1", // 扫描的目标主机
                "port": 8005, // 扫描的目标端口
                "cpu": "0.0%", // cpu占用
                "mem": "10.51 M", // 内存占用
                "rasp_result_timeout": 0, // 获取rasp-agent结果超时数量
                "waiting_rasp_request": 0, // 等待中的rasp-agent结果数量
                "dropped_rasp_result": 0, // 收到的无效rasp-agent结果数量
                "send_request": 0,  // 已发送测试请求
                "failed_request": 0, // 发生错误的测试请求
                "total": 5, // 当前url总数
                "failed": 1, // 扫描失败的url数量
                "scanned": 2, // 扫描的url数量
                "concurrent_request": 10, // 当前并发数
                "request_interval": 0, // 当前请求间隔
                "config": {...}, // 配置信息
                "last_time": 1563182956 // 最近一次获取到新url的时间
            }

            未在扫描的item:
            {
                "host": "127.0.0.1", // 扫描的目标主机
                "port": 8005, // 扫描的目标端口
                "total": 5, // 当前url总数
                "scanned": 2, // 扫描的url数量
                "failed": 1, // 扫描失败的url数量
                "config": {...}, // 配置信息
                "last_time": 1563182956 // 最近一次获取到新url的时间
            }

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        result_tables = self._target_status.get_tables()
        Logger().debug("Got current tables: {}".format(", ".join(result_tables)))

        total_target = len(result_tables)
        if page <= 0 or (page - 1) * 10 > total_target:
            page = 1
        result_tables = result_tables[(page - 1) * 10:page * 10]

        result = {}
        for host_port in result_tables:
            host, port = common.split_host(host_port)

            # 如果是运行中的扫描，获取运行状态的信息
            scanner_id = self._scanner_info.get_scanner_id(host_port)
            info = {
                "host": host,
                "port": port
            }

            if scanner_id is not None:
                info["id"] = scanner_id
                module_name = "Scanner_" + str(scanner_id)
                runtime_info = RuntimeInfo().get_latest_info()[module_name]
                info.update(runtime_info)
            result[host_port] = info

        # 获取扫描目标进度信息
        scan_count_info = BaseModel.get_scan_count(result.keys())
        for host_port in scan_count_info:
            result[host_port].update(scan_count_info[host_port])

        # 获取扫描信息上次更新时间
        scan_time_info = BaseModel.get_last_time(result.keys())
        for host_port in scan_time_info:
            result[host_port].update(scan_time_info[host_port])

        # 转换为列表
        result_list = list(result.values())

        return result_list, total_target

    async def get_report(self, host_port, page, perpage):
        """
        获取扫描结果

        Parameters:
            host_port - str, 获取的目标主机的 host + "_" + str(port) 组成
            page - int, 获取的页码
            perpage - int, 每页条数

        Returns:
            {"total":数据总条数, "data":[ RaspResult的json字符串, ...]}

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            model = ReportModel(
                host_port, create_table=False, multiplexing_conn=True)
        except exceptions.TableNotExist:
            data = {"total": 0, "data": []}
        else:
            data = await model.get(page, perpage)
        return data

    def get_auto_start(self):
        """
        获取自动启动扫描开关状态

        Returns:
            bool, 是否开启自启动扫描
        """

        if Communicator().get_value("auto_start", "Monitor") == 1:
            return True
        else:
            return False

    def set_auto_start(self, auto_start):
        """
        设置自动启动扫描开关(请求首次接收时启动扫描)

        Parameters:
            auto_start - bool, 是否开启自启动扫描
        """

        if auto_start is True:
            Communicator().set_value("auto_start", 1, "Monitor")
        else:
            Communicator().set_value("auto_start", 0, "Monitor")

    def get_urls(self, host_port, page=0, status=0):
        """
        获取指定状态的的url列表

        Parameters:
            page - int, 获取的页数，每页10条
            status - int, url的状态 未扫描：0, 已扫描：1, 正在扫描：2, 扫描中出现错误: 3

        Returns:
            total, urls - total为数据总数, int类型，urls为已扫描的url, list类型, item形式为tuple (url对应id, url字符串)
        """

        try:
            model = NewRequestModel(host_port, create_table=False, multiplexing_conn=True)
        except exceptions.TableNotExist as e:
            raise e

        return model.get_urls(page, status)

    def get_config(self, module_params):
        """
        获取扫描目标的配置

        Parameters:
            module_params - dict, 结构为{
                "host":str, 目标主机,
                "port":int, 目标端口
            }

        Returns:
            dict - 配置信息
        """
        host_port = common.concat_host(module_params["host"], module_params["port"])
        return self._config.get_config(host_port)

    def mod_config(self, module_params):
        """
        修改扫描目标的配置

        Parameters:
            module_params - dict, 结构为{
                "host":str, 目标主机,
                "port":int, 目标端口
                "config": dict, 配置信息
            }

        """
        host_port = common.concat_host(module_params["host"], module_params["port"])
        self._config.mod_config(host_port, module_params["config"])


class ScannerInfo(object):

    def __init__(self):
        self._max_scanner = Config().get_config("scanner.max_module_instance")
        self._scanner_list = [None] * self._max_scanner
        self._scanner_map = {}

    def _check_alive(self, scanner_id=None, host_port=None):
        """
        刷新当前扫描任务存活状态
        """
        if host_port is not None:
            scanner_info = self._scanner_map.get(host_port, None)
            if scanner_info is None:
                return
            else:
                scanner_id = scanner_info["scanner_id"]

        check_list = range(self._max_scanner) if scanner_id is None else [scanner_id, ]
        reset_list = []

        for scanner_id in check_list:
            if self._scanner_list[scanner_id] is not None:
                pid = Communicator().get_value("pid", "Scanner_" + str(scanner_id))
                if pid == 0:
                    reset_list.append(scanner_id)
        for scanner_id in reset_list:
            self.remove_scanner_info(scanner_id)

    def set_scanner_info(self, scanner_id, pid, host, port):
        """
        添加一条scanner信息

        Parameters:
            scanner_id - int, 指定的scanner的id, 该id必须未使用
            pid - int, 进程pid
            host - str, 目标host
            port - int, 目标端口
        """
        scanner_info = {
            "scanner_id": scanner_id,
            "pid": pid,
            "host": host,
            "port": port
        }
        self._scanner_list[scanner_id] = scanner_info
        self._scanner_map[common.concat_host(host, port)] = scanner_info

    def remove_scanner_info(self, scanner_id):
        """
        删除指定的scanner信息

        Parameters:
            scanner_id - int
        """
        host = self._scanner_list[scanner_id]["host"]
        port = self._scanner_list[scanner_id]["port"]
        host_port = common.concat_host(host, port)
        del self._scanner_map[host_port]
        self._scanner_list[scanner_id] = None

    def get_scanner_id(self, host_port):
        """
        获取host_port对应的scanner的id

        Parameters:
            host_port - str

        Returns:
            int - scanner_id, 不存在返回None
        """
        self._check_alive(host_port=host_port)
        scanner_info = self._scanner_map.get(host_port, None)
        if scanner_info is None:
            return None
        else:
            return scanner_info["scanner_id"]

    def get_pid(self, scanner_id):
        """
        获取scanner对应的pid

        Parameters:
            scanner_id - int, 获取的目标id

        Returns:
            pid - int, 无对应pid时返回None
        """
        self._check_alive(scanner_id=scanner_id)
        if self._scanner_list[scanner_id] is not None:
            return self._scanner_list[scanner_id]["pid"]
        else:
            return None

    def is_scanning(self, host_port):
        """
        判断目标是否正在被扫描

        Parameters:
            host_port - str, 目标主机_端口
        """
        self._check_alive(host_port=host_port)
        return host_port in self._scanner_map

    def get_idle_scanner(self):
        """
        获取当前空闲的扫描器

        Returns:
            int, 空闲扫描器id, 无空闲进程返回None

        Raises:
            无空闲进程返回
        """
        self._check_alive()
        for scanner_id in range(self._max_scanner):
            if self._scanner_list[scanner_id] is None:
                return scanner_id
        return None


class ScannerConfig(object):

    def __init__(self, scanner_info, scanner_schedulers):
        """
        初始化扫描配置
        """
        self._scanner_schedulers = scanner_schedulers
        self._scannner_info = scanner_info

        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)

        self.plugin_loaded = {}
        plugin_path = Communicator().get_main_path() + "/plugin/scanner"
        plugin_import_path = "plugin.scanner"

        # 需要加载插件, 提供一些dummy对象
        Communicator().set_internal_shared("report_model", None)
        Communicator().set_internal_shared("failed_task_set", None)

        plugin_names = []
        for file_name in os.listdir(plugin_path):
            if os.path.isfile(plugin_path + os.sep + file_name) and file_name.endswith(".py"):
                plugin_names.append(file_name[:-3])

        for plugin_name in plugin_names:
            try:
                plugin_module = __import__(
                    plugin_import_path, fromlist=[plugin_name])
            except Exception as e:
                Logger().critical("Error in load plugin: {}".format(plugin_name), exc_info=e)
                sys.exit(1)
            else:
                plugin_instance = getattr(
                    plugin_module, plugin_name).ScanPlugin()
                if isinstance(plugin_instance, scan_plugin_base.ScanPluginBase):
                    self.plugin_loaded[plugin_name] = plugin_instance
                    Logger().debug(
                        "scanner plugin: {} preload success!".format(plugin_name))
                else:
                    Logger().critical(
                        "Detect scanner plugin {} not inherit class ScanPluginBase!".format(plugin_name))
                    sys.exit(1)

        plugin_status = {}
        for plugin_name in self.plugin_loaded:
            plugin_status[plugin_name] = {
                "enable": True,
                "show_name": self.plugin_loaded[plugin_name].plugin_info["show_name"],
                "description": self.plugin_loaded[plugin_name].plugin_info["description"]
            }

        default_config = {
            "scan_plugin_status": plugin_status,
            "scan_rate": {
                "max_concurrent_request": Config().get_config("scanner.max_concurrent_request"),
                "max_request_interval": Config().get_config("scanner.max_request_interval"),
                "min_request_interval": Config().get_config("scanner.min_request_interval")
            },
            "white_url_reg": "",
            "scan_proxy": "",
            "version": 0
        }

        # 插件列表有更新时，删除当前缓存的所有插件启用配置
        origin_default_config = config_model.get("default")
        if origin_default_config is not None:
            origin_default_config = json.loads(origin_default_config)
            if len(origin_default_config["scan_plugin_status"]) != len(default_config["scan_plugin_status"]):
                config_model.delete("all")
            else:
                for plugin_names in origin_default_config["scan_plugin_status"]:
                    if plugin_names not in default_config["scan_plugin_status"]:
                        config_model.delete("all")
                        break

        config_model.update("default", json.dumps(default_config))
        self._default_config = default_config
        self._config_cache = {}

    def _set_boundary_value(self, scanner_id, boundary):
        """
        配置扫描速率范围

        Parameters:
            scanner_id - int, 配置的scanner的id
            boundary - dict, 配置项, 格式
            {
                "max_concurrent_request": 10,
                "max_request_interval": 1000,
                "min_request_interval: 0
            }

        Raises:
            exceptions.InvalidScannerId - 目标id不存在引发此异常
        """
        module_name = "Scanner_" + str(scanner_id)
        try:
            scheduler = self._scanner_schedulers[module_name]
        except KeyError:
            raise exceptions.InvalidScannerId

        cr_max = boundary["max_concurrent_request"]
        ri_max = boundary["max_request_interval"]
        ri_min = boundary["min_request_interval"]
        scheduler.set_boundary_value(cr_max, ri_max, ri_min)

    def _incremental_update_config(self, host_port, config):
        """
        增量更新扫描的运行时配置

        Paramerters:
            host_port - str, 目标主机host_port
            config - dict, 更新的config
        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)

        if host_port not in self._config_cache:
            origin_config_json = config_model.get(host_port)
            if origin_config_json is None:
                origin_config = copy.deepcopy(self._default_config)
            else:
                origin_config = json.loads(origin_config_json)
        else:
            origin_config = self._config_cache[host_port]

        version = origin_config["version"]
        if "scan_plugin_status" in config:
            for plugin_name in config["scan_plugin_status"]:
                origin_config["scan_plugin_status"][plugin_name]["enable"] = config["scan_plugin_status"][plugin_name]["enable"]

        if "scan_rate" in config:
            for key in config["scan_rate"]:
                if config["scan_rate"][key] >= 0:
                    origin_config["scan_rate"][key] = config["scan_rate"][key]
            if origin_config["scan_rate"]["min_request_interval"] > origin_config["scan_rate"]["max_request_interval"]:
                origin_config["scan_rate"]["max_request_interval"] = origin_config["scan_rate"]["min_request_interval"]

        if "white_url_reg" in config:
            origin_config["white_url_reg"] = config["white_url_reg"]

        if "scan_proxy" in config:
            origin_config["scan_proxy"] = config["scan_proxy"]

        # 更新db、cache、和共享内存中的配置version
        origin_config["version"] = version + 1
        config_model.update(host_port, json.dumps(origin_config))
        self._config_cache[host_port] = origin_config

        # 更新速率控制
        scanner_id = self._scannner_info.get_scanner_id(host_port)
        if scanner_id is not None:
            self._set_boundary_value(scanner_id, origin_config["scan_rate"])
            Communicator().set_value("config_version", origin_config["version"], "Scanner_" + str(scanner_id))

    def get_config(self, host_port):
        """
        获取扫描目标的配置

        Parameters:
            host_port - str, 目标主机端口

        Returns:
            dict - 配置信息
        """
        if host_port not in self._config_cache:
            config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
            config_json = config_model.get(host_port)
            if config_json is None:
                self._config_cache[host_port] = copy.deepcopy(self._default_config)
            else:
                self._config_cache[host_port] = json.loads(config_json)

        return self._config_cache[host_port]

    def mod_config(self, host_port, config):
        """
        修改扫描目标的配置

        Parameters:
            host_port - str, 目标主机端口
            config - dict, 配置信息

        """
        self._incremental_update_config(host_port, config)

    def del_config(self, host_port):
        """
        删除扫描目标的配置

        Parameters:
            host_port - str, 目标主机端口

        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
        config_model.delete(host_port)
        if host_port in self._config_cache:
            del self._config_cache[host_port]


class TargetStatus(object):

    def __init__(self):
        self._table_status = -1
        self._table_list = []

    def get_tables(self):
        """
        获取所有扫描目标对应的数据库表前缀
        """
        table_status = Communicator().get_target_list_status()
        if table_status > self._table_status:
            tables = BaseModel(multiplexing_conn=True).get_tables()
            result_tables = []
            for table_name in tables:
                if table_name.lower().endswith("_resultlist"):
                    host_port = table_name[:-11]
                    result_tables.append(host_port)
            self._table_list = result_tables
            self._table_status = table_status
        return self._table_list
