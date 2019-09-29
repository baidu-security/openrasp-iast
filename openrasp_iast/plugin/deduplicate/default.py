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

from core.components.plugin import dedup_plugin_base


class DedupPlugin(dedup_plugin_base.DedupPluginBase):

    plugin_info = {
        "name": "default",
        "description": "默认去重插件"
    }

    def get_hash(self, rasp_result_ins):
        """
        返回None则该请求会被丢弃，可用于实现白名单
        """
        # if rasp_result_ins.get_url.find("logout") != -1:
        #     return None
        return self.get_hash_default(rasp_result_ins)
