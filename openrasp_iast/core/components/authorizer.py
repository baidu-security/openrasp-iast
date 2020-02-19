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

from core.components.config import Config


class Authorizer(object):

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(Authorizer, cls).__new__(cls)
            cls.instance._init_plugin()
        return cls.instance

    def _init_plugin(self):
        pass

    def get_auth(self):
        pass
