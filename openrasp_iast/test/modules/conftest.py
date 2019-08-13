#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Copyright 2017-2019 Baidu Inc.

Licensed under the Apache License, Version 2.0 (the "License"];
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import helper
from core.components.config import Config

# 指定测试时的config
for item in helper.db_config:
    Config().config_dict["database." + item] = helper.db_config[item]

Config().config_dict["cloud_api.enable"] = False
Config().config_dict["monitor.schedule_interval"] = 0.1
Config().config_dict["preprocessor.request_lru_size"] = 1
Config().config_dict["scanner.max_concurrent_request"] = 5
Config().config_dict["scanner.min_request_interval"] = 50
Config().config_dict["scanner.max_request_interval"] = 300
Config().config_dict["scanner.max_module_instance"] = 2
Config().config_dict["log.path"] = "log"
