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
import errno
import types
import pytest
import signal
import psutil
import multiprocessing

import helper
from core import modules
from core import launcher
from core.components.logger import Logger
from core.components.fork_proxy import ForkProxy
from core.components.communicator import Communicator


system_info_dict = {
    "cpu": 0,
    "mem": 0
}


def _set_system_info(cpu, mem):
    system_info_dict["cpu"] = cpu
    system_info_dict["mem"] = mem


def _refresh_info_hook(self):
    self.system_info = system_info_dict


def _wait_child(signum, frame):
        """
        处理进程terminate信号
        """
        try:
            while True:
                cpid, status = os.waitpid(-1, os.WNOHANG)
                if cpid == 0:
                    break
                exitcode = status >> 8
                Logger().warning("Module process {} exit with exitcode {}".format(cpid, exitcode))
        except OSError as e:
            if e.errno == errno.ECHILD:
                Logger().warning('Main process has no existing unwaited-for child processes.')
            else:
                Logger().error("Unknow error occurred in method _wait_child!", exc_info=e)

def _fork_proxy():
    signal.signal(signal.SIGCHLD, _wait_child)
    while True:
        ForkProxy().listen()


@pytest.fixture(scope="module")
def monitor_fixture():
    from core.components.runtime_info import RuntimeInfo
    RuntimeInfo._refresh_system_info = types.MethodType(
        _refresh_info_hook, RuntimeInfo)

    helper.reset_db()
    Communicator()
    Logger()
    ForkProxy()
    module_proc = modules.Process(modules.Monitor)
    module_proc.start()

    fork_proxy_proc = multiprocessing.Process(target=_fork_proxy)
    fork_proxy_proc.start()

    yield {"set_system_info": _set_system_info}

    root_proc = psutil.Process(module_proc.pid)
    fork_proc = psutil.Process(fork_proxy_proc.pid)
    procs = root_proc.children(recursive=True)
    procs.append(fork_proc)
    procs.append(root_proc)
    try:
        for p in procs:
            p.terminate()
            p.wait(2)
    except Exception:
        raise Exception("Module process may not be killed success!")

    module_proc.join(3)
    fork_proxy_proc.join(3)

    helper.reset_db()
    Communicator.reset()
