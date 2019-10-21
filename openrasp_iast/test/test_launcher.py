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
import pytest
import time
import psutil
import multiprocessing

from core.launcher import Launcher
from core.components.config import Config
from core.components.communicator import Communicator

# @pytest.fixture(scope='session', autouse=True)
# def sess_scope2():
#     pass


def test_launcher():
    proc = multiprocessing.Process(target=Launcher().launch)
    proc.start()
    time.sleep(2)
    module_procs = psutil.Process(proc.pid).children(recursive=True)

    assert len(module_procs) > 2
    proc.terminate()
    proc.join(5)
    if proc.is_alive():
        raise Exception(
            "launcher process with pid {} may not be killed success!")

    time.sleep(Config().get_config("monitor.schedule_interval") * 2)
    for child in module_procs:
        try:
            child.wait(5)
        except psutil.TimeoutExpired:
            assert False

    Communicator.reset()
