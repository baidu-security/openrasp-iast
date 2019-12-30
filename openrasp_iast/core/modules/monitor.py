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
import psutil
import shutil
import threading

from core.modules import base
from core.components import common
from core.components.logger import Logger
from core.components.config import Config
from core.components.cloud_api import CloudApi
from core.components.cloud_api import Transaction
from core.components.web_console import WebConsole
from core.components.runtime_info import RuntimeInfo
from core.components.communicator import Communicator
from core.components.scanner_manager import ScannerManager


class ScannerScheduler(object):

    def __init__(self, module_name):
        """
        初始化
        """
        self.module_name = module_name
        self.lock = threading.Lock()

        self.cr_maintain_times = 0
        self.cr_maintain_times_amplitude = 5
        self.last_schedule_decrease = False
        self.max_performance = False
        self.cr_max = Config().get_config("scanner.max_concurrent_request")
        self.ri_max = Config().get_config("scanner.max_request_interval")
        self.ri_min = Config().get_config("scanner.min_request_interval")

        self.rrt_last = 0
        self.fr_last = 0
        self.sr_last = 0

    def do_schedule(self):
        """
        出现失败的扫描请求或cpu使用率过高会降低扫描速度
        """
        if self._get_runtime_value("pid") == 0:
            return

        cpu_overused, cpu_idle = self._is_cpu_overused()
        if self._is_fail_increasing() or cpu_overused:
            self._schedule_cr(decrease=True)
        elif self._is_full_concurrency() and cpu_idle:
            self._schedule_cr(decrease=False)

    def get_boundary_value(self):
        """
        获取动态调整扫描速率的边界值
        """
        return {
            "max_concurrent_request": self.cr_max,
            "min_request_interval": self.ri_max,
            "max_request_interval": self.ri_min
        }

    def set_boundary_value(self, cr_max, ri_max, ri_min):
        """
        配置边界值，用于动态调整扫描速率

        Parameters:
            cr_max - 最大并发数
            ri_max - 请求最大间隔
            ri_min - 请求最小间隔
        """
        with self.lock:
            self.cr_max = cr_max if cr_max >= 1 else 1
            self.ri_max = ri_max if ri_max < 100000 and ri_max > 0 else 1000
            self.ri_min = ri_min if ri_min >= 0 and ri_min < ri_max else 0

    def _is_cpu_overused(self):
        """
        判断cpu是否负载过高

        Returns:
            boolean, boolean - cpu是否负载过高，cpu是否空闲
        """
        system_info = RuntimeInfo().get_system_info()
        if system_info["cpu"] > Config().get_config("monitor.max_cpu"):
            Logger().info("CPU percent is higher than limit (use:{}%, limit:{}%), scan rate will decrease.".format(
                system_info["cpu"], Config().get_config("monitor.max_cpu")))
            return True, False
        elif system_info["cpu"] < Config().get_config("monitor.min_cpu"):
            return False, True
        else:
            return False, False

    def _get_runtime_value(self, key):
        """
        获取scanner运行时的状态信息

        Parameters:
            key - 要获取的变量名

        Returns:
            变量对应的值
        """
        return RuntimeInfo().get_value(self.module_name, key)

    def _is_fail_increasing(self):
        """
        判断自上次调用本函数的时间段内，是否产生了请求超时/rasp_result获取失败

        Returns:
            boolean
        """
        rrt = self._get_runtime_value("rasp_result_timeout")
        fr = self._get_runtime_value("failed_request")
        if self.rrt_last < rrt or self.fr_last < fr:
            self.rrt_last = rrt
            self.fr_last = fr
            Logger().info("rasp_result timeout or scanner request failed increased.")
            return True
        else:
            return False

    def _is_full_concurrency(self):
        """
        判断当前并发速率是否已达到最大

        Returns:
            boolean
        """
        si = Config().get_config("monitor.schedule_interval")
        sr = self._get_runtime_value("send_request")
        max_cr = self._get_runtime_value("max_concurrent_request")
        ri = self._get_runtime_value("request_interval")
        request_send = sr - self.sr_last
        self.sr_last = sr
        if ri < 1000:
            ri = 1000
        if request_send / si * ri / 1000 >= max_cr:
            return True
        else:
            return False

    def _schedule_cr(self, decrease=False):
        """
        执行调度

        Parameters:
            decrease - boolean, 为True时执行减少并发，False时执行增加并发

        """
        if not decrease and self.max_performance:
            return
        cr = Communicator().get_value("max_concurrent_request", self.module_name)
        ri = Communicator().get_value("request_interval", self.module_name)
        with self.lock:
            if cr > self.cr_max:
                cr = self.cr_max
            if ri > self.ri_max or ri < self.ri_min:
                ri = self.ri_min

            if decrease:
                self.max_performance = False
                if self.last_schedule_decrease:
                    self.cr_maintain_times_amplitude += 1
                else:
                    self.last_schedule_decrease = True
                    self.cr_maintain_times_amplitude = 2

                self.cr_maintain_times += self.cr_maintain_times_amplitude
                if self.cr_maintain_times > 100:
                    self.cr_maintain_times = 100

                if ri < 128 and self.ri_max >= 128:
                    if ri == 0:
                        ri = 16
                    else:
                        ri *= 2
                elif cr > 1:
                    cr -= 1
                else:
                    ri += int((self.ri_max - self.ri_min) / 10)

                if ri > self.ri_max:
                    ri = self.ri_max

            else:
                self.last_schedule_decrease = False
                if self.cr_maintain_times > 0:
                    self.cr_maintain_times -= 1
                    return
                else:
                    if ri > 128:
                        ri -= int((self.ri_max - self.ri_min) / 10)
                        if ri < 128:
                            ri = 128
                    elif cr < self.cr_max:
                        cr += 1
                    else:
                        ri /= 2
                        ri = int(ri)

                    if ri <= self.ri_min:
                        ri = self.ri_min
                        if cr == self.cr_max:
                            self.max_performance = True

        Communicator().set_value("max_concurrent_request", cr, self.module_name)
        Communicator().set_value("request_interval", ri, self.module_name)
        Logger().debug("[{}]max_concurrent_request is set to {}, request_interval is set to {}ms".format(
            self.module_name, str(cr), str(ri)))


class Monitor(base.BaseModule):
    """
    用于监控运行状态、启停其他模块的模块
    """

    def __init__(self):
        """
        初始化
        """
        self.preprocessor_proc = None
        self.crash_module = None
        self.cloud_thread = None
        self.web_console_thread = None

    def _upload_report(self):
        try:
            self.cloud_api = CloudApi()
        except Exception as e:
            Logger().critical("CloudApi init failed!", exc_info=e)

        Logger().info("Init cloud_api success.")
        while True:
            time.sleep(10)
            try:
                self.cloud_api.upload_report()
            except Exception as e:
                Logger().warning("Upload report error.", exc_info=e)

    def _check_alive(self):
        """
        判断其他模块是否正常运行
        """
        ppid = os.getppid()
        if ppid <= 1:
            Logger().warning("Detect main process stopped, Monitor exit!")
            self.crash_module = "main"
            return False

        # http server存活检测
        # if not self.web_console_thread.isAlive():
        #     Logger().error("Detect monitor web console stopped, Monitor exit!")
        #     self.crash_module = "Monitor_web_console"
        #     return False

        if self.cloud_thread is not None and not self.cloud_thread.isAlive():
            Logger().error("Detect monitor cloud thread stopped, Monitor exit!")
            self.crash_module = "cloud_thread"
            return False

        if self.transaction_thread is not None and not self.transaction_thread.isAlive():
            Logger().error("Detect monitor cloud transaction thread stopped, Monitor exit!")
            self.crash_module = "transaction_thread"
            return False

        if self.preprocessor_proc is None:
            pid = Communicator().get_value("pid", "Preprocessor")
            if pid != 0:
                try:
                    self.preprocessor_proc = psutil.Process(pid)
                except Exception:
                    Logger().error("Init Preprocessor proc fail, Monitor exit!")
                    self.crash_module = "preprocessor"
                    return False
            return True

        elif not self.preprocessor_proc.is_running():
            Logger().error("Detect preprocessor stopped, Monitor exit!")
            self.crash_module = "preprocessor"
            return False

        return True

    def _terminate_modules(self):
        """
        结束其他所有模块
        """
        all_procs = []
        scanner_num = Config().get_config("scanner.max_module_instance")

        for i in range(scanner_num):
            pid = Communicator().get_value("pid", "Scanner_" + str(i))
            if pid != 0:
                all_procs.append(pid)
        all_procs.append(Communicator().get_value("pid", "Preprocessor"))
        all_procs += Communicator().get_pre_http_pid()
        for pid in all_procs:
            if pid != 0:
                self._kill_proc_tree(pid)

        ppid = os.getppid()
        if ppid > 1:
            try:
                p = psutil.Process(ppid)
                p.kill()
            except Exception as e:
                Logger().error("Kill launcher failed", exc_info=e)

    def _kill_proc_tree(self, pid):
        """
        结束进程树, 递归结束目标和其子进程

        Parameters:
            pid - 进程pid
        """
        try:
            root_proc = psutil.Process(pid)
            procs = root_proc.children(recursive=True)
            procs.append(root_proc)
            for p in procs:
                p.send_signal(psutil.signal.SIGKILL)
        except Exception:
            pass

    def _get_self_ip(self):
        """
        获取本机ip
        """
        info = psutil.net_if_addrs()
        for name, value in info.items():
            for item in value:
                if (
                    item[0] == 2 and
                    item[1].find(".") > 0 and
                    item[1] != '127.0.0.1' and
                    item[2] is not None
                ):
                    return item[1]
        return "127.0.0.1"

    def _clean_mei(self):
        """
        清理pyinstaller运行时的临时文件
        """
        if hasattr(sys, "_MEIPASS"):
            try:
                shutil.rmtree(sys._MEIPASS)
            except Exception as e:
                Logger().error("Clean pyinstaller temp path {} failed".format(sys._MEIPASS), exc_info=e)

    def run(self):
        """
        Monitor 主函数
        """

        # 多线程开始前初始化
        RuntimeInfo()

        if Config().get_config("cloud_api.enable"):
            self.cloud_thread = threading.Thread(
                target=self._upload_report,
                name="upload_report_thread",
                daemon=True
            )
            self.cloud_thread.start()

        # 初始化调度类
        scanner_schedulers = {}
        for module_name in RuntimeInfo().get_latest_info().keys():
            if module_name.startswith("Scanner"):
                scanner_schedulers[module_name] = ScannerScheduler(module_name)
        ScannerManager().init_manager(scanner_schedulers)

        # 启动后台http server
        # web_console = WebConsole()
        # self.web_console_thread = threading.Thread(
        #     target=web_console.run,
        #     name="web_console_thread",
        #     daemon=True
        # )
        # self.web_console_thread.start()

        # 向云控后台发送心跳，用于建立ws连接

        transaction = Transaction()
        self.transaction_thread = threading.Thread(
            target=transaction.run,
            name="transaction_thread",
            daemon=True
        )
        self.transaction_thread.start()

        time.sleep(1)
        if self._check_alive():
            print("[-] OpenRASP-IAST init success!")
            print("[-] Visit web console with url: http://{}:{}/".format(
                self._get_self_ip(), Config().get_config("monitor.console_port")))
            print("[-] Before start scan task, set OpenRASP agent plugin algorithmConfig option 'fuzz_server' (edit iast.js or use cloud server web console)  with url: 'http://{}:{}{}'".format(
                self._get_self_ip(), Config().get_config("preprocessor.http_port"), Config().get_config("preprocessor.api_path")))

            Logger().info("Monitor init success!")
        else:
            self._terminate_modules()
            sys.exit(1)

        while True:
            try:
                # 执行调度
                RuntimeInfo().refresh_info()
                for module_name in scanner_schedulers:
                    scanner_schedulers[module_name].do_schedule()
                time.sleep(Config().get_config("monitor.schedule_interval"))

                # 检测模块存活
                if not self._check_alive():
                    self._terminate_modules()
                    if self.crash_module == "main":
                        Logger().info("OpenRASP-IAST exit!")
                        print("[!] OpenRASP-IAST exit!")
                        self._clean_mei()
                        sys.exit(0)
                    else:
                        Logger().critical("Detect Module {} down, exit!".format(self.crash_module))
                        self._clean_mei()
                        sys.exit(1)

            except Exception as e:
                Logger().critical("Monitor module crash with unknow error!", exc_info=e)
                self._terminate_modules()
                self._clean_mei()
                sys.exit(2)
