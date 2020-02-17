#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import setuptools

packages = [
    "openrasp_iast",
    "openrasp_iast.core",
    "openrasp_iast.core.components",
    "openrasp_iast.core.components.plugin",
    "openrasp_iast.core.components.audit_tools",
    "openrasp_iast.core.model",
    "openrasp_iast.core.modules",
    "openrasp_iast.plugin",
    "openrasp_iast.plugin.authorizer",
    "openrasp_iast.plugin.deduplicate",
    "openrasp_iast.plugin.scanner"
]

try:
    with open("openrasp_iast/requirements.txt") as f:
        req_str = f.read()
    install_requires = req_str.split("\n")
except Exception:
    install_requires = []

entry_points = {
    "console_scripts": [
        "openrasp-iast=openrasp_iast.main:run"
    ]
}


setuptools.setup(
    name='openrasp-iast',
    version='v1.2',
    description='An IAST scanner base on OpenRASP',
    long_description="An IAST scanner base on OpenRASP",
    author='OpenRASP',
    author_email='ext_yunfenxi@baidu.com',
    url='https://rasp.baidu.com/',
    packages=packages,
    install_requires=install_requires,
    package_dir={"openrasp_iast": "openrasp_iast"},
    include_package_data=True,
    entry_points=entry_points,
    platforms=["linux"],
    python_requires='>=3.6',
    license="Apache-2.0"
)
