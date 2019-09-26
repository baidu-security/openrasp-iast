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
import errno
import signal
import psutil

from core import modules
from core.components.logger import Logger
from core.components.config import Config
from core.components.fork_proxy import ForkProxy
from core.components.communicator import Communicator


class Launcher(object):
    """
    工具入口类
    """

    def __init__(self):
        self.preprocessor_pid = 0
        self.monitor_pid = 0
        self.exit = False

    def _wait_child(self, signum, frame):
        """
        处理进程terminate信号
        """
        try:
            try:
                while True:
                    cpid, status = os.waitpid(-1, os.WNOHANG)
                    if cpid == 0:
                        break

                    if cpid == self.monitor_pid:
                        root_proc = psutil.Process(os.getpid())
                        procs = root_proc.children(recursive=True)
                        for p in procs:
                            p.send_signal(psutil.signal.SIGKILL)
                        if self.exit:
                            pass
                        else:
                            Logger().critical("Detect Monitor down, exit!")
                            print("[!] Detect Monitor down, OpenRASP-IAST exit!")
                            sys.exit(1)

                    exitcode = status >> 8
            except OSError as e:
                if e.errno != errno.ECHILD:
                    Logger().error("Unknow error occurred in method _wait_child!", exc_info=e)
        except KeyboardInterrupt:
            pass

    def _set_affinity(self):
        if Config().get_config("affinity.enable") is True:
            try:
                core_num = Config().get_config("affinity.core_num")
                cpu_count = psutil.cpu_count()
                if core_num <= 0 or cpu_count < core_num:
                    mask = range(1)
                    Logger().warning("Config item affinity.core_num invalid, use defaut (1)")
                else:
                    mask = range(core_num)
                os.sched_setaffinity(os.getpid(), mask)
            except Exception as e:
                Logger().error("set affinity error!", exc_info=e)

    def launch(self):
        """
        启动器主函数
        """
        self._set_affinity()
        Communicator()
        Logger().init_module_logger()
        ForkProxy()
        Logger().info("Launcher init success!")
        
        preprocessor_proc = modules.Process(modules.Preprocessor)
        preprocessor_proc.start()
        self.preprocessor_pid = preprocessor_proc.pid
        Logger().info("Preprocessor fork success!")

        monitor_proc = modules.Process(modules.Monitor)
        monitor_proc.start()
        self.monitor_pid = monitor_proc.pid
        Logger().info("Monitor fork success!")

        signal.signal(signal.SIGCHLD, self._wait_child)
        try:
            ForkProxy().listen()
        except KeyboardInterrupt:
            self.exit = True
