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

from pytest_cov.embed import cleanup_on_sigterm

from core.components.config import Config

Config().generate_config("./config.yaml")
Config().load_config("./config.yaml")
# 用于支持多进程覆盖率统计
cleanup_on_sigterm()


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: this mark slow test.")
    config.addinivalue_line(
        "markers", "test: mark test to run specified only.")


sys.path.append(os.path.dirname(__file__) + "/test")
