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
import pytest
import signal
import psutil
import multiprocessing

import helper
from core import modules
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


@pytest.fixture(scope="module")
def preprocessor_fixture():
    helper.reset_db()
    Communicator()
    Logger()
    module_proc = modules.Process(modules.Preprocessor)
    module_proc.start()

    yield module_proc

    root_proc = psutil.Process(module_proc.pid)
    procs = root_proc.children(recursive=True)
    try:
        root_proc.terminate()
        root_proc.wait(10)
        module_proc.join(5)
        for p in procs:
            p.terminate()
            p.wait(10)
    except psutil.TimeoutExpired:
        raise Exception("Module process may not be killed success!")

    helper.reset_db()
    Communicator.reset()
