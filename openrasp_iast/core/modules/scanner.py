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
import json
import time
import queue
import signal
import asyncio
import functools
import multiprocessing

from core.modules import base
from core.components import exceptions
from core.components import authorizer
from core.components import audit_tools
from core.components import result_receiver
from core.components.config import Config
from core.components.logger import Logger
from core.components.plugin import scan_plugin_base
from core.components.communicator import Communicator
from core.model.report_model import ReportModel
from core.model.config_model import ConfigModel
from core.model.new_request_model import NewRequestModel


class Scanner(base.BaseModule):

    def __init__(self, **kwargs):
        """
        初始化
        """
        # kwargs 参数初始化
        self.target_host = kwargs["host"]
        self.target_port = kwargs["port"]

        self._init_scan_config()

        # 用于记录失败请求并标记
        self.failed_task_set = set()
        Communicator().set_internal_shared("failed_task_set", self.failed_task_set)
        self.module_id = Communicator().get_module_name().split("_")[-1]

        Communicator().set_value("max_concurrent_request", 1)
        Communicator().set_value("request_interval", Config().get_config("scanner.min_request_interval"))

        self._init_db()
        self._init_plugin()
        # 更新运行时配置
        self._update_scan_config()

    def _init_scan_config(self):
        """
        获取缓存的扫描配置
        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=False, multiplexing_conn=True)
        host_port = self.target_host + "_" + str(self.target_port)
        config = config_model.get(host_port)
        if config is None:
            raise exceptions.GetRuntimeConfigFail
        self.scan_config = json.loads(config)

    def _save_scan_config(self):
        """
        存储当前扫描目标配置
        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=False, multiplexing_conn=True)
        host_port = self.target_host + "_" + str(self.target_port)
        config_model.update(host_port, json.dumps(self.scan_config))

    def _update_scan_config(self):
        """
        更新当前运行的扫描配置
        """
        config_model = ConfigModel(table_prefix="", use_async=True, create_table=False, multiplexing_conn=True)
        host_port = self.target_host + "_" + str(self.target_port)
        self.scan_config = json.loads(config_model.get(host_port))
        for plugin_name in self.scan_config["scan_plugin_status"]:
            self.plugin_loaded[plugin_name].set_enable(self.scan_config["scan_plugin_status"][plugin_name]["enable"])
            self.plugin_loaded[plugin_name].set_white_url_reg(self.scan_config["white_url_reg"])
            self.plugin_loaded[plugin_name].set_scan_proxy(self.scan_config["scan_proxy"])
            
        Logger().debug("Update scanner config to version {}, new config json is {}".format(self.scan_config["version"], json.dumps(self.scan_config)))

    def _init_plugin(self):
        """
        初始化扫描插件
        """
        self.plugin_loaded = {}
        plugin_import_path = "plugin.scanner"

        for plugin_name in self.scan_config["scan_plugin_status"].keys():
            try:
                plugin_module = __import__(
                    plugin_import_path, fromlist=[plugin_name])
            except Exception as e:
                Logger().error("Error in load plugin: {}".format(plugin_name), exc_info=e)
            else:
                plugin_instance = getattr(
                    plugin_module, plugin_name).ScanPlugin()
                if isinstance(plugin_instance, scan_plugin_base.ScanPluginBase):
                    self.plugin_loaded[plugin_name] = plugin_instance
                    Logger().debug(
                        "scanner plugin: {} load success!".format(plugin_name))
                else:
                    Logger().warning("scanner plugin {} not inherit class ScanPluginBase!".format(plugin_name))

        if len(self.plugin_loaded) == 0:
            Logger().error("No scanner plugin detected, scanner exit!")
            raise exceptions.NoPluginError

    def _init_db(self):
        """
        初始化数据库
        """
        model_prefix = self.target_host + "_" + str(self.target_port)
        self.new_scan_model = NewRequestModel(model_prefix)
        self.new_scan_model.reset_unscanned_item()
        report_model = ReportModel(model_prefix)
        Communicator().set_internal_shared("report_model", report_model)

    def _exit(self, signame, loop):
        loop.stop()

    def run(self):
        """
        模块主函数，启动协程
        """
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.async_run())
        except RuntimeError:
            Logger().info("Scanner process has been killed!")
        except Exception as e:
            Logger().error("Scanner exit with unknow error!", exc_info=e)

    async def async_run(self):
        """
        协程主函数
        """
        # 注册信号处理
        loop = asyncio.get_event_loop()
        for signame in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(
                getattr(signal, signame),
                functools.partial(self._exit, signame, loop))

        # 初始化context
        await audit_tools.context.Context().async_init()

        # 启动插件
        plugin_tasks = []
        for plugin_name in self.plugin_loaded:
            plugin_tasks.append(loop.create_task(
                self.plugin_loaded[plugin_name].async_run()))

        # 启动获取扫描结果队列的协程
        task_fetch_rasp_result = loop.create_task(self._fetch_from_queue())

        # 执行获取新扫描任务
        await self._fetch_new_scan()
        
        # 结束所有协程任务，reset共享内存
        task_fetch_rasp_result.cancel()
        await asyncio.wait({task_fetch_rasp_result})
        for task in plugin_tasks:
            task.cancel()
        await asyncio.wait(set(plugin_tasks), return_when=asyncio.ALL_COMPLETED)
        Communicator().reset_all_value()

    async def _fetch_from_queue(self):
        """
        获取扫描请求的RaspResult, 并分发给扫描插件
        """
        queue_name = "rasp_result_queue_" + self.module_id
        sleep_interval = 0.1
        continuously_sleep = 0
        Logger().debug("Fetch task is running, use queue: " + queue_name)

        while True:
            if Communicator().get_value("config_version") > self.scan_config["version"]:
                self._update_scan_config()
            try:
                data = Communicator().get_data_nowait(queue_name)
                Logger().debug("From rasp_result_queue got data: " + str(data))
                result_receiver.RaspResultReceiver().add_result(data)
                Logger().debug("Send data to rasp_result receiver: {}".format(
                    data.get_request_id()))
                continuously_sleep = 0
            except exceptions.QueueEmpty:
                if continuously_sleep < 10:
                    continuously_sleep += 1
                await asyncio.sleep(sleep_interval * continuously_sleep)

    async def _fetch_new_scan(self):
        """
        获取非扫描请求（新扫描任务），并分发给插件，=
        """
        # 扫描插件任务队列最大值
        scan_queue_max = 300
        # 已扫描的任务数量
        self.scan_num = 0
        # 扫描队列数量
        self.scan_queue_remaining = 0
        # 下次获取任务数量
        self.fetch_count = 20
        # 待标记的已扫描的最大id
        self.mark_id = 0

        while True:
            if Communicator().get_value("cancel") == 0:
                try:
                    await self._fetch_task_from_db()
                except exceptions.DatabaseError as e:
                    Logger().error("Database error occured when fetch scan task.", exc_info=e)
                except asyncio.CancelledError as e:
                    raise e
                except Exception as e:
                    Logger().error("Unexpected error occured when fetch scan task.", exc_info=e)
                if self.scan_queue_remaining == 0:
                    continue
            elif self.scan_queue_remaining == 0:
                break

            await self._check_scan_progress()

            # 调整每次获取的扫描任务数
            if self.scan_queue_remaining + self.fetch_count > scan_queue_max:
                self.fetch_count = scan_queue_max - self.scan_queue_remaining
            elif self.fetch_count < 5:
                self.fetch_count = 5

    async def _fetch_task_from_db(self):
        """
        从数据库中获取当前扫描目标的非扫描请求（新扫描任务）
        """

        await self.new_scan_model.mark_result(self.mark_id, list(self.failed_task_set))
        self.failed_task_set.clear()

        sleep_interval = 1
        continuously_sleep = 0

        while True:
            if Communicator().get_value("cancel") != 0:
                break
            data_list = await self.new_scan_model.get_new_scan(self.fetch_count)
            data_count = len(data_list)
            Logger().debug("Fetch {} task from db.".format(data_count))
            if data_count > 0 or self.scan_queue_remaining > 0:
                for item in data_list:
                    for plugin_name in self.plugin_loaded:
                        # item 格式: {"id": id, "data":rasp_result_json}
                        self.plugin_loaded[plugin_name].add_task(item)
                    Logger().debug("Send task with id: {} to plugins.".format(item["id"]))
                self.scan_queue_remaining += data_count
                return
            else:
                Logger().debug("No url need scan, fetch task sleep {}s".format(sleep_interval * continuously_sleep))
                if continuously_sleep < 10:
                    continuously_sleep += 1
                await asyncio.sleep(sleep_interval * continuously_sleep)

    async def _check_scan_progress(self):
        """
        监测扫描进度，给出下次获取的任务量
        """
        sleep_interval = 1
        sleep_count = 0
        while True:
            await asyncio.sleep(sleep_interval)
            sleep_count += 1
            scan_num_list = []
            scan_id_list = []

            for plugin_name in self.plugin_loaded:
                plugin_ins = self.plugin_loaded[plugin_name]
                plugin_scan_num, plugin_last_id = plugin_ins.get_scan_progress()
                scan_num_list.append(plugin_scan_num)
                scan_id_list.append(plugin_last_id)

            plugin_scan_min_num = min(scan_num_list)
            plugin_scan_min_id = min(scan_id_list)
            finish_count = plugin_scan_min_num - self.scan_num


            if sleep_count > 20:
                # 20个sleep内未扫描完成，每次最大获取任务量减半
                self.scan_queue_remaining -= finish_count
                self.scan_num = plugin_scan_min_num
                sleep_count = 0
                Logger().debug("Finish scan num: {}, remain task: {}, max scanned id: {}, decrease task fetch_count.".format(
                    finish_count, self.scan_queue_remaining, plugin_scan_min_id))
            elif sleep_count > 10:
                # 10-20个sleep内完成一半以上，每次最大获取任务量不变
                if self.scan_queue_remaining < finish_count * 2:
                    self.fetch_count = finish_count
                    break
            elif self.scan_queue_remaining == finish_count:
                # 10个sleep内完成，每次最大获取任务量加倍
                self.fetch_count = self.scan_queue_remaining * 2
                break

        self.scan_queue_remaining -= finish_count
        self.scan_num = plugin_scan_min_num
        self.mark_id = plugin_scan_min_id

        Logger().debug("Finish scan num: {}, remain task: {}, max scanned id: {}".format(
            finish_count, self.scan_queue_remaining, plugin_scan_min_id))