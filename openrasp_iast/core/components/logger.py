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
import tornado
import logging
import peewee
import multiprocessing
import cloghandler

from core.components.config import Config
from core.components.communicator import Communicator


class Logger(object):
    """
    日志记录模块
    """
    def __new__(cls):
        """
        单例模式初始化
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Logger, cls).__new__(cls)
            cls.instance._init_logger()
        return cls.instance

    def _init_error_log(self):
        """
        配置统一的error.log
        """
        error_logger = logging.getLogger("openrasp_iast.error")

        # 前台输出
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.ERROR)
        fmt = logging.Formatter('[!] %(message)s')
        stream_handler.setFormatter(fmt)
        
        # 文件输出
        file_handler = cloghandler.ConcurrentRotatingFileHandler(
            self.log_path + "/error.log",
            mode='a',
            maxBytes=Config().get_config("log.rotate_size")*1024*1024,
            backupCount=Config().get_config("log.rotate_num")
        )
        date_fmt = '%Y-%m-%d %H:%M:%S'
        log_fmt = '[%(asctime)s - %(levelname)s][%(processName)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
        fmt = logging.Formatter(fmt=log_fmt, datefmt=date_fmt)
        file_handler.setFormatter(fmt)

        error_logger.propagate = False
        error_logger.handlers = []
        error_logger.addHandler(file_handler)
        error_logger.addHandler(stream_handler)
        error_logger.setLevel(logging.ERROR)

        self.error_logger = error_logger
        
        self.critical = self.error_logger.critical
        self.error = self.error_logger.error

    def _set_handler(self, logger, suffix, log_fmt, concurrent=True):
        """
        为logger配置Handler
        """
        if concurrent is True:
            Handler = cloghandler.ConcurrentRotatingFileHandler
        else:
            Handler = logging.handlers.RotatingFileHandler

        handler = Handler(
            self.log_path + "/" + suffix,
            mode='a',
            maxBytes=Config().get_config("log.rotate_size")*1024*1024,
            backupCount=Config().get_config("log.rotate_num")
        )
        date_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter(fmt=log_fmt, datefmt=date_fmt)
        handler.setFormatter(fmt)

        logger.propagate = False
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(self._log_level)

    def init_module_logger(self):
        """
        初始化模块日志配置, 应当在每个模块初始化时调用
        """
        module_name = Communicator().get_module_name()
        root_logger = logging.getLogger()
        if module_name == "Preprocessor":
            access_logger = logging.getLogger("tornado.access")
            access_logger.handlers = []
            access_logger.propagate = False
            access_logger.setLevel(logging.CRITICAL)
            access_logger.parent = root_logger
            log_fmt = '[%(asctime)s - %(levelname)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
            log_suffix = "Preprocessor.log"
            self._set_handler(root_logger, log_suffix, log_fmt, concurrent=True)

        elif module_name == "Monitor":
            access_logger = logging.getLogger("tornado.access")
            access_logger.propagate = False
            access_logger.setLevel(logging.CRITICAL)
            access_logger.handlers = []
            log_fmt = '[%(asctime)s - %(levelname)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
            log_suffix = "Monitor.log"
            self._set_handler(root_logger, log_suffix, log_fmt, concurrent=False)

        elif module_name.startswith("Scanner"):
            self.module_log_path = self.log_path + "/" + module_name
            if not os.path.exists(self.module_log_path):
                os.makedirs(self.module_log_path)
            log_fmt = '[%(asctime)s - %(levelname)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
            log_suffix = module_name + "/Scanner.log"
            self._set_handler(root_logger, log_suffix, log_fmt, concurrent=False)
        
        else:
            log_fmt = '[%(asctime)s - %(levelname)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
            log_suffix = module_name + ".log"
            self._set_handler(root_logger, log_suffix, log_fmt, concurrent=False)

        iast_logger = logging.getLogger("openrasp_iast." + module_name)
        self.warning = iast_logger.warning
        self.info = iast_logger.info
        self.debug = iast_logger.debug

    def get_scan_plugin_logger(self, plugin_name):
        """
        配置扫描插件logger

        Parameters:
            plugin_name - str, 扫描插件名

        Returns:
            Logger , 生成的logger
        """
        log_path = self.module_log_path
        handler = logging.handlers.RotatingFileHandler(
            log_path + "/plugin_" + plugin_name + ".log",
            mode='a',
            maxBytes=Config().get_config("log.rotate_size")*1024*1024,
            backupCount=Config().get_config("log.rotate_num")
        )
        module_name = Communicator().get_module_name()
        logger = logging.getLogger("openrasp_iast.module_name_" + plugin_name)
        log_fmt = '[%(asctime)s - %(levelname)s] %(message)s [file: %(pathname)s , line %(lineno)d]'
        date_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter(fmt=log_fmt, datefmt=date_fmt)
        handler.setFormatter(fmt)
        logger.parent = None
        logger.propagate = False
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(self._log_level)
        return logger

    def _init_logger(self):
        """
        初始化
        """
        self._log_level = Config().get_config("log.level").upper()
        if self._log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self._log_level = "INFO"
        self.log_path = Config().get_config("log.path")
        self.module_log_path = self.log_path

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        self._init_error_log()
        self.init_module_logger()
        