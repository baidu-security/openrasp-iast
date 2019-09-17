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
        self.max_scanner = Config().get_config("scanner.max_module_instance")
        self.scanner_schedulers = scanner_schedulers
        self.scanner_list = [None] * self.max_scanner
        self._init_config()

    def _init_config(self):
        """
        初始化扫描配置
        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)

        self.plugin_loaded = {}
        plugin_path = Communicator().get_main_path() + "/plugin/scanner"
        plugin_import_path = "plugin.scanner"
        
        # 需要加载插件, 提供一个假的report_model
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
                    Logger().critical("Detect scanner plugin {} not inherit class ScanPluginBase!".format(plugin_name))
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
        
        # 插件列表有更新时，删除当前缓存的所有配置
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

    def _check_alive(self):
        """
        刷新当前扫描任务存活状态
        """
        reset_list = []
        for scanner_id in range(self.max_scanner):
            if self.scanner_list[scanner_id] is not None:
                pid = Communicator().get_value("pid", "Scanner_" + str(scanner_id))
                if pid == 0:
                    reset_list.append(scanner_id)
        for scanner_id in reset_list:
            self.scanner_list[scanner_id] = None
        
    def _incremental_update_config(self, host_port, config):
        """
        增量更新扫描的运行时配置

        Paramerters:
            host_port - str, 目标主机host_port
            config - dict, 更新的config
        """

        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
        origin_config_json = config_model.get(host_port)
        if origin_config_json is None:
            origin_config_json = config_model.get("default")

        origin_config = json.loads(origin_config_json)
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

        origin_config["version"] = version + 1
        config_model.update(host_port, json.dumps(origin_config))

        for scanner_id in range(len(self.scanner_list)):
            if self.scanner_list[scanner_id] is not None:
                running_host_port = self.scanner_list[scanner_id]["host"] + "_" + str(self.scanner_list[scanner_id]["port"])
                if host_port == running_host_port:
                    self.set_boundary_value(scanner_id, origin_config["scan_rate"])
                    Communicator().set_value("config_version" , origin_config["version"], "Scanner_" + str(scanner_id))
                    break

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
        self._check_alive()
        idle_scanner = None
        for scanner_id in range(self.max_scanner):
            if self.scanner_list[scanner_id] is None:
                idle_scanner = scanner_id
                break
        if idle_scanner is None:
            raise exceptions.MaximumScannerExceede

        for item in self.scanner_list:
            if item is not None:
                if item["host"] == module_params["host"] and item["port"] == module_params["port"]:
                    raise exceptions.TargetIsScanning

        host_port = module_params["host"] + "_" + str(module_params["port"])
        self._incremental_update_config(host_port, {})

        scanner_process_kwargs = {
            "module_cls": modules.Scanner,
            "instance_id": idle_scanner,
            "module_params": {
                "host": module_params["host"],
                "port": module_params["port"]
            }
        }
        Communicator().reset_all_value("Scanner_" + str(idle_scanner))
        pid = ForkProxy().fork(scanner_process_kwargs)

        new_scanner_info = {
            "pid": pid,
            "host": module_params["host"],
            "port": module_params["port"],
            "cancel": 0,
            "pause": 0
        }
        Communicator().set_value("pid", pid, "Scanner_" + str(idle_scanner))
        self.scanner_list[idle_scanner] = new_scanner_info

    def get_config(self, module_params):
        """
        获取扫描目标的配置

        Parameters:
            module_params - dict, 结构为{
                "host":str, 目标主机, 
                "port":int, 目标端口
            }

        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
        host_port = module_params["host"] + "_" + str(module_params["port"])
        config_json = config_model.get(host_port)
        if config_json is None:
            config_json = config_model.get("default")
        return json.loads(config_json)

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
        host_port = module_params["host"] + "_" + str(module_params["port"])
        self._incremental_update_config(host_port, module_params["config"])

    def pause_scanner(self, scanner_id):
        """
        将一个扫描进程的共享内存的pause设置为1

        Parameters:
            scanner_id - int, 目标扫描进程的id
        """
        self._check_alive()
        try:
            assert self.scanner_list[scanner_id] is not None
            assert self.scanner_list[scanner_id]["pid"] != 0
        except:
            raise exceptions.InvalidScannerId
        module_name = "Scanner_" + str(scanner_id)
        self.scanner_list[scanner_id]["pause"] = 1
        Communicator().set_value("pause", 1, module_name)

    def resume_scanner(self, scanner_id):
        """
        将一个扫描进程的共享内存的pause设置为0

        Parameters:
            scanner_id - int, 目标扫描进程的id
        """
        self._check_alive()
        try:
            assert self.scanner_list[scanner_id] is not None
            assert self.scanner_list[scanner_id]["pid"] != 0
        except:
            raise exceptions.InvalidScannerId
        module_name = "Scanner_" + str(scanner_id)
        self.scanner_list[scanner_id]["pause"] = 0
        Communicator().set_value("pause", 0, module_name)

    def cancel_scanner(self, scanner_id):
        """
        将一个扫描进程的共享内存的cancel设置为1

        Parameters:
            scanner_id - int, 目标扫描进程的id
        """
        self._check_alive()
        try:
            assert self.scanner_list[scanner_id] is not None
            assert self.scanner_list[scanner_id]["pid"] != 0
        except:
            raise exceptions.InvalidScannerId
        module_name = "Scanner_" + str(scanner_id)
        self.scanner_list[scanner_id]["cancel"] = 1
        Communicator().set_value("cancel", 1, module_name)

    def kill_scanner(self, scanner_id):
        """
        强制结束一个扫描进程进程

        Parameters:
            scanner_id - int类型, 要结束的扫描进程的id

        Returns:
            成功结束返回True，否则返回false

        """
        self._check_alive()
        if (self.scanner_list[scanner_id] is None or self.scanner_list[scanner_id]["pid"] == 0):
            raise exceptions.InvalidScannerId
        pid = self.scanner_list[scanner_id]["pid"]

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
            self.scanner_list[scanner_id] = None
            module_name = "Scanner_" + str(scanner_id)
            Communicator().set_value("pid", 0, module_name)
            return True

    def is_scanning(self, host, port):
        self._check_alive()
        for scanner in self.scanner_list:
            if scanner is not None and scanner["host"] == host and scanner["port"] == port:
                return True
        return False

    async def get_running_info(self):
        """
        获取当前扫描任务信息

        Returns:
            dict, 结构：
            {
                "0":{
                    "pid": 64067, // 扫描进程pid
                    "host": "127.0.0.1", // 扫描的目标主机
                    "port": 8005, // 扫描的目标端口
                    "rasp_result_timeout": 0, // 获取rasp-agent结果超时数量
                    "waiting_rasp_request": 0, // 等待中的rasp-agent结果数量
                    "dropped_rasp_result": 0, // 收到的无效rasp-agent结果数量
                    "send_request": 0,  // 已发送测试请求
                    "failed_request": 0, // 发生错误的测试请求
                    "cpu": "0.0%", // cpu占用
                    "mem": "10.51 M", // 内存占用
                    "total": 5, // 当前url总数
                    "scanned": 2, // 扫描的url数量
                    "concurrent_request": 10, // 当前并发数
                    "request_interval": 0, // 当前请求间隔
                },
                "1":{
                    ...
                },
            }

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        self._check_alive()
        result = {}
        for scanner_id in range(self.max_scanner):
            if self.scanner_list[scanner_id] is not None:
                result[scanner_id] = copy.deepcopy(self.scanner_list[scanner_id])

        for module_id in result:
            module_name = "Scanner_" + str(module_id)
            runtime_info = RuntimeInfo().get_latest_info()[module_name]
            for key in runtime_info:
                result[module_id][key] = runtime_info[key]

            try:
                scheduler = self.scanner_schedulers[module_name]
            except KeyError:
                raise exceptions.InvalidScannerId

            table_prefix = result[module_id]["host"] + "_" + str(result[module_id]["port"])
            total, scanned, failed = await NewRequestModel(table_prefix, multiplexing_conn=True).get_scan_count()
            result[module_id]["total"] = total
            result[module_id]["scanned"] = scanned
            result[module_id]["failed"] = failed

            if "pause" in result[module_id]:
                del result[module_id]["pause"]
            if "cancel" in result[module_id]:
                del result[module_id]["cancel"]

        return result

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
        table_prefix = host + "_" + str(port)
        if url_only:
            NewRequestModel(table_prefix, multiplexing_conn=True).truncate_table()
        else:
            NewRequestModel(table_prefix, multiplexing_conn=True).drop_table()
            ReportModel(table_prefix,  multiplexing_conn=True).drop_table()
            config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
            config_model.delete(table_prefix)
        Communicator().set_clean_lru([table_prefix])

    async def get_all_target(self):
        """
        获取数据库中存在的所有目标主机的列表

        Returns:
            list, item为dict,格式为：
            正在扫描的item:
            {
                "id": 1, // 扫描任务id
                "pid": 64067, // 扫描进程pid
                "host": "127.0.0.1", // 扫描的目标主机
                "port": 8005, // 扫描的目标端口
                "cancel": 0, // 是否正在取消
                "pause": 0, // 是否被暂停
                "cpu": "0.0%", // cpu占用
                "mem": "10.51 M", // 内存占用
                "rasp_result_timeout": 0, // 获取rasp-agent结果超时数量
                "waiting_rasp_request": 0, // 等待中的rasp-agent结果数量
                "dropped_rasp_result": 0, // 收到的无效rasp-agent结果数量
                "send_request": 0,  // 已发送测试请求
                "failed_request": 0, // 发生错误的测试请求
                "total": 5, // 当前url总数
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
                "config": {...}, // 配置信息
                "last_time": 1563182956 // 最近一次获取到新url的时间
            }

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        tables = BaseModel().get_tables()
        Logger().debug("Got current tables: {}".format(", ".join(tables)))
        result = {}
        for table_name in tables:
            if table_name.lower().endswith("_resultlist"):
                host_port = table_name[:-11]
            else:
                continue
            host_port_split = host_port.split("_")

            host = "_".join(host_port_split[:-1])
            port = host_port_split[-1]
            result[host_port] = {
                "host": host,
                "port": port
            }

        running_info = await self.get_running_info()

        for scanner_id in running_info:
            host_port = running_info[scanner_id]["host"] + "_" + str(running_info[scanner_id]["port"])
            result[host_port] = running_info[scanner_id]
            result[host_port]["id"] = scanner_id
        
        result_list = []

        for host_port in result:
            new_request_model = NewRequestModel(host_port, multiplexing_conn=True)
            result[host_port]["last_time"] = await new_request_model.get_last_time()
            if result[host_port].get("id", None) is None:
                total, scanned, failed = await new_request_model.get_scan_count()
                result[host_port]["total"] = total
                result[host_port]["scanned"] = scanned
                result[host_port]["failed"] = failed

            config_model = ConfigModel(table_prefix="", use_async=True, create_table=True, multiplexing_conn=True)
            target_config = config_model.get(host_port)
            if target_config is None:
                target_config = config_model.get("default")
            result[host_port]["config"] = json.loads(target_config)


            result_list.append(result[host_port])
        result_list.sort(key=(lambda k:k["last_time"]), reverse=True)
        return result_list

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
            data = {"total":0, "data":[]}
        else:
            data = await model.get(page, perpage)
        return data

    def get_plugin_info(self, plugin_path, class_prefix):
        """
        获取指定类型插件的plugin_info

        Parameters:
            plugin_path - str, 插件目录

        Returns:
            list, 每个item为一个plugin_info dict
        """

        result = []
        plugin_names = []
        plugin_import_path = plugin_path.replace(os.sep, ".")
        for file_name in os.listdir(plugin_path):
            if os.path.isfile(plugin_path + os.sep + file_name) and file_name.endswith(".py"):
                plugin_names.append(file_name[:-3])

        for plugin_name in plugin_names:
            try:
                plugin_module = __import__(plugin_import_path, fromlist=[plugin_name])
            except Exception as e:
                Logger().warning("Error in import plugin: {}".format(plugin_name), exc_info=e)
            else:
                plugin_module = getattr(plugin_module, plugin_name)
                plugin_info = getattr(plugin_module, class_prefix + "Plugin").plugin_info
                result.append(plugin_info)
        return result

    def get_plugins(self):
        """
        获取插件列表

        Returns:
            {
                "scan":[ {"name":plugin_name, "description":xxxx}, ...],
                "dedup":[ ... ]
                "auth: [ ... ]
            }
        """
        main_path = Communicator().get_main_path()
        result = {
            # "Auth": main_path + "/plugin/authorizer",
            "Dedup": main_path + "/plugin/deduplicate",
            "Scan": main_path + "/plugin/scanner",
        }

        for key in result:
            result[key] = self.get_plugin_info(result[key], key)
        
        return result
    
    def set_boundary_value(self, scanner_id, boundary):
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
            scheduler = self.scanner_schedulers[module_name]
        except KeyError:
            raise exceptions.InvalidScannerId

        cr_max = boundary["max_concurrent_request"]
        ri_max = boundary["max_request_interval"]
        ri_min = boundary["min_request_interval"]
        scheduler.set_boundary_value(cr_max, ri_max, ri_min)

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

