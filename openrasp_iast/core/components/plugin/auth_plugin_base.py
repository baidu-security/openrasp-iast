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

import json
import time

from core.components.logger import Logger


class AuthPluginBase(object):

    plugin_info = {
        "name": "No_name_plugin",  # 使用数字字母下划线命名, 应与文件名（不含扩展名）相同
        "description": "No description"
    }

    def __init__(self):
        """
        初始化
        """
        self.last_auth = []

    def get_auth_info(self):
        try:
            if self.last_auth[1] < time.time():
                self.last_auth = self.get_auth()
            return self.last_auth[0]
        except Exception as e:
            Logger().error("Authorizer plugin error!", exc_info=e)
            return {}

    def get_auth(self):
        """
        返回一个元组：（包含认证头key：value的dict, 超时时间time）
        """
        raise NotImplementedError
