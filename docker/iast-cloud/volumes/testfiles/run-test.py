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

from testtools import dvwa_scan
from testtools import webgoat_scan
from testtools import benchmark_scan
from testtools import mutillidae_scan

# test accessible
benchmark_scan.run()
dvwa_scan.run()
webgoat_scan.run()
mutillidae_scan.run()
