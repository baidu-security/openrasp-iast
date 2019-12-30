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

import re
import os
import sys
import json
import asyncio
import traceback
import jsonschema
import tornado.web
import urllib.parse
import tornado.ioloop
import tornado.httpserver

from core import modules
from core.components import exceptions
from core.components.logger import Logger
from core.components.config import Config
from core.components.scanner_manager import ScannerManager


class WebConsole(object):

    def __init__(self):
        """
        初始化
        """
        current_path = os.path.dirname(__file__)
        self.static_path = os.path.join(current_path, "../../web")
        self.port = Config().get_config("monitor.console_port")
        self._init_app()

    def _init_app(self):
        """
        注册处理请求的handler
        """
        handlers = []

        handlers.append(
            tornado.web.url(
                "/api/scanner/new",
                RunScannerHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/scanner/config",
                ScanConfigHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/scanner/get_config",
                GetConfigHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/scanner/kill",
                KillScannerHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/scanner/auto_start",
                AutoStartHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/scanner/auto_start_status",
                AutoStartStatusHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/model/get_all",
                GetAllTargetHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/model/get_url_info",
                GetUrlInfoHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/model/clean_target",
                CleanTargetHandler
            )
        )

        handlers.append(
            tornado.web.url(
                "/api/model/get_report",
                GetReportHandler
            )
        )

        handlers.append(
            (
                r'^/((?:index.html)?)$',
                NoCacheStaticFileHandler,
                {
                    "path": self.static_path,
                    "default_filename": "index.html"
                }
            )
        )
        settings = {
            "static_path": os.path.join(self.static_path, "static"),
            "static_url_prefix": "/static/",
            "static_handler_class": NoCacheStaticFileHandler
        }
        self.app = tornado.web.Application(handlers=handlers, **settings)

    def run(self):
        """
        单进程（协程）方式启动http server
        """
        asyncio.set_event_loop(asyncio.new_event_loop())
        server = tornado.httpserver.HTTPServer(self.app)
        try:
            server.listen(self.port)
        except OSError as e:
            Logger().critical("Monitor web_console bind port error!", exc_info=e)
            sys.exit(1)
        else:
            tornado.ioloop.IOLoop.current().start()


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    """
    静态文件不使用缓存
    """

    def set_extra_headers(self, path):
        self.set_header("Cache-control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", 0)

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Credentials", "true")


class ApiHandlerBase(tornado.web.RequestHandler):

    # config 类请求格式定义
    config_schema = {
        "type": "object",
        "properties": {
            "scan_plugin_status": {
                "type": "object",
                "patternProperties": {
                        ".*": {
                            "type": "object",
                            "required": ["enable", "show_name", "description"],
                            "properties": {
                                "enable": {
                                    "type": "boolean"
                                },
                                "show_name": {
                                    "type": "string"
                                }
                            }
                        }
                }
            },
            "scan_rate": {
                "type": "object",
                "properties": {
                    "max_concurrent_request": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "max_request_interval": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "min_request_interval": {
                        "type": "integer",
                        "minimum": 0
                    }
                }
            },
            "white_url_reg": {
                "type": "string"
            }
        }
    }

    def get(self):
        """
        处理get请求
        """
        self.send_error(405)

    async def post(self):
        """
        处理post请求
        """
        header = self.request.headers
        if "Content-Type" in header:
            if header["Content-Type"].startswith("application/json"):
                try:
                    try:
                        data = json.loads(self.request.body)
                    except json.decoder.JSONDecodeError:
                        Logger().warning(
                            "Invalid json send to server, data: {}.".format(self.request.body))
                        self.send_error(415)
                        return
                    else:
                        response = await self.handle_request(data)
                except Exception as e:
                    Logger().error(
                        "Error when process http request.", exc_info=e)
                    response = {
                        "exception_info": e.__repr__(),
                        "trace_back": traceback.format_exc()
                    }
                    self.write(json.dumps(response))
                    self.send_error(500)
                else:
                    self.set_header('Content-type', 'application/json')
                    self.write(json.dumps(response))
                return

        Logger().warning("Data with Content-Type: {} posted to http server, rejected!".format(
            header.get("Content-Type", "None")))
        # Unsupported media type
        self.send_error(415)

    def handle_request(self, data):
        """
        子类实现请求的具体处理方法
        """
        raise NotImplementedError


class RunScannerHandler(ApiHandlerBase):

    async def handle_request(self, data):
        """
        请求格式：
        {
            "host":"1.2.3.4",
            "port": 80
        }
        """
        try:
            module_params = {
                "host": data["host"],
                "port": data.get("port", 80)
            }

        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            try:
                ScannerManager().new_scanner(module_params)
            except exceptions.MaximumScannerExceede:
                ret = {
                    "status": 2,
                    "description": "并行扫描任务数量到达上限!"
                }
            except exceptions.TargetIsScanning:
                ret = {
                    "status": 3,
                    "description": "目标主机:{}:{}正在被扫描，请先停止!".format(
                        module_params["host"], module_params["port"])
                }
            else:
                ret = {
                    "status": 0,
                    "description": "ok"
                }
        return ret


class ScanConfigHandler(ApiHandlerBase):

    config_validtor = jsonschema.Draft7Validator(ApiHandlerBase.config_schema)

    async def handle_request(self, data):
        """
        请求格式：
        {
            "host":"1.2.3.4",
            "port": 80,
            "config": {
                "scan_plugin_status": {
                    "command_basic": {
                        "enable": true,
                        "show_name": "命令注入检测插件",
                        "description": "xxxx"
                    },
                    ...
                },
                "scan_rate": {
                    "max_concurrent_request": 20,
                    "max_request_interval": 1000,
                    "min_request_interval": 0
                },
                "white_url_reg": "^/logout",
                "scan_proxy": "http://127.0.0.1:8080"
            }
        }
        """
        try:
            module_params = {
                "host": data["host"],
                "port": data.get("port", 80),
                "config": data.get("config", {})
            }
            self.config_validtor.validate(module_params["config"])
            if "white_url_reg" in module_params["config"]:
                re.compile(module_params["config"]["white_url_reg"])

            if "scan_proxy" in module_params["config"]:
                proxy_url = module_params["config"]["scan_proxy"]
                if proxy_url != "":
                    scheme = urllib.parse.urlparse(proxy_url).scheme
                    if scheme not in ("http", "https"):
                        assert False

        except (KeyError, TypeError, jsonschema.exceptions.ValidationError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        except re.error:
            ret = {
                "status": 2,
                "description": "白名单正则不合法!"
            }
        except AssertionError:
            ret = {
                "status": 3,
                "description": "代理协议应为http或https!"
            }
        else:
            ScannerManager().mod_config(module_params)
            ret = {
                "status": 0,
                "description": "ok"
            }
        return ret


class GetConfigHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "host":"1.2.3.4",
            "port": 80,
        }

        返回的data结构, 获取目标不存在返回default配置：
        {
            "scan_plugin_status": {
                "command_basic": true,
                "directory_basic": false
            },
            "scan_rate": {
                "max_concurrent_request": 20,
                "max_request_interval": 1000,
                "min_request_interval": 0
            }
        }
        """
        try:
            module_params = {
                "host": data["host"],
                "port": data.get("port", 80)
            }
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            data = ScannerManager().get_config(module_params)
            ret = {
                "status": 0,
                "description": "ok",
                "data": data
            }
            return ret


class KillScannerHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "scanner_id":0
        }
        """
        try:
            scanner_id = data["scanner_id"]
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            try:
                success = ScannerManager().kill_scanner(scanner_id)
            except exceptions.InvalidScannerId:
                ret = {
                    "status": 2,
                    "description": "目标Scanner_id：{} 未在运行!".format(scanner_id)
                }
            else:
                if success:
                    ret = {
                        "status": 0,
                        "description": "ok"
                    }
                else:
                    ret = {
                        "status": 3,
                        "description": "结束scanner进程失败!"
                    }
        return ret


class AutoStartHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "auto_start": true
        }
        """
        try:
            auto_start = data["auto_start"]
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            ScannerManager().set_auto_start(auto_start)
            ret = {
                "status": 0,
                "description": "ok"
            }
            return ret


class AutoStartStatusHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {}
        """
        status = ScannerManager().get_auto_start()
        ret = {
            "status": 0,
            "description": "ok",
            "data": {
                "status": status
            }
        }
        return ret


class GetAllTargetHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "page":1
        }
        """
        page = data.get("page", 1)
        result, total = ScannerManager().get_all_target(page)
        ret = {
            "status": 0,
            "description": "ok",
            # data 格式参考get_all_target返回值
            "data": {
                "total": total,
                "result": result
            }
        }
        return ret


class GetUrlInfoHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "host":"1.2.3.4",
            "port": 80,
            "page": 1,
            "status": 0 // 未扫描：0, 已扫描：1, 正在扫描：2, 扫描中出现错误: 3
        }
        """

        try:
            host = data["host"]
            port = data.get("port", 80)
            page = data.get("page", 1)
            status = int(data["status"])
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            host_port = host + "_" + str(port)
            try:
                total, urls = await ScannerManager().get_urls(host_port, page, status)
            except exceptions.TableNotExist:
                ret = {
                    "status": 2,
                    "description": "target not exist",
                }
            else:
                ret = {
                    "status": 0,
                    "description": "ok",
                    "data": {
                        "total": total,
                        # urls: [(23, "http://127.0.0.1/testpage?a=1"), ...]
                        "urls": urls
                    }
                }
        return ret


class CleanTargetHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "host": "1.2.3.4",
            "port": 80,
            "url_only": false
        }
        """
        try:
            host = data["host"]
            port = data.get("port", 80)
            url_only = data.get("url_only", False)
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            try:
                ScannerManager().clean_target(host, port, url_only)
                ret = {
                    "status": 0,
                    "description": "ok"
                }
            except exceptions.TargetIsScanning:
                ret = {
                    "status": 2,
                    "description": "目标主机:{}:{}正在被扫描，请先停止!".format(host, port)
                }
        return ret


class GetReportHandler(ApiHandlerBase):
    async def handle_request(self, data):
        """
        请求格式：
        {
            "host":"1.2.3.4",
            "port": 80,
            "page": 1,
            "perpage": 10
        }
        """
        try:
            host = data["host"]
            port = data.get("port", 80)
            page = data["page"]
            perpage = data["perpage"]
        except (KeyError, TypeError):
            ret = {
                "status": 1,
                "description": "请求json格式非法!"
            }
        else:
            host_port = host + "_" + str(port)
            data = await ScannerManager().get_report(host_port, page, perpage)

            ret = {
                "status": 0,
                "description": "ok",
                # {"total":123, "data":["json_str_1", "json_str2" ...]}
                "data": data
            }
        return ret
