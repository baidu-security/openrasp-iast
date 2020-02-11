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
import time
import json
import signal
import platform
import argparse
import traceback
import urllib.parse

main_path = os.path.abspath(__file__)
main_path = os.path.dirname(main_path)
sys.path.append(main_path)

from core.components.config import Config


def init_check():
    version = float(platform.python_version()[:3])
    if version < 3.6:
        print("[!] You must run this tool with Python 3.6 or newer version.")
        sys.exit(1)

    if sys.platform not in ("linux", "darwin"):
        print("[!] Not support to run on platform: {}, use linux.".format(sys.platform))
        sys.exit(1)

    try:
        import aiohttp, aiomysql, jsonschema, lru, peewee, peewee_async, psutil, pymysql, tornado, yaml, cloghandler, requests
    except ModuleNotFoundError as e:
        print(e, ", use command 'pip3 install -r requirements.txt' to install dependency packages.")
        sys.exit(1)

    try:
        conn = pymysql.connect(
            port=Config().config_dict["database.port"],
            host=Config().config_dict["database.host"],
            user=Config().config_dict["database.username"],
            passwd=Config().config_dict["database.password"]
        )
        sql = "select @@lower_case_table_names;"
        cursor = conn.cursor()
        cursor._defer_warnings = True
        cursor.execute(sql)
        result = cursor.fetchall()

        if len(result) > 0 and int(result[0][0]) == 1:
            print("[!] MySQL System Variable lower-case-table-names should be set to 0 or 2! ")
            sys.exit(1)

        sql = "select @@version"
        cursor.execute(sql)
        version = cursor.fetchone()
        try:
            if version is not None:
                version = version[0].split(".")
                if int(version[0]) > 5 or (int(version[0]) == 5 and int(version[1]) > 5):
                    print("[!] Warning: MySQL version not support, use mysql version >= 5.5.3".format(result[0][1]))
        except Exception:
            pass

        sql = "show variables like 'max_connections';"
        cursor.execute(sql)
        result = cursor.fetchall()
        if len(result) > 0 and int(result[0][1]) < 1000:
            print("[!] Warning: MySQL max_connections is set to {}, this may limit maximum number of concurrent scan task, set max_connections at least to 1000 if you have large number of concurrent scan task.".format(result[0][1]))

        cursor.close()
        conn.close()
    except Exception as e:
        print("[!] MySQL connection fail, check database config! ", e)
        sys.exit(1)

    # 测试是否能正确连接云控
    if Config().config_dict["cloud_api.enable"]:
        cloud_config = {
            "backend_url": Config().config_dict["cloud_api.backend_url"],
            "app_secret": Config().config_dict["cloud_api.app_secret"],
            "app_id": Config().config_dict["cloud_api.app_id"]
        }

        for k, v in cloud_config.items():
            if v == "":
                print("[!] Config item cloud_api.{} is empty, refer to rasp cloud page to configure this option!".format(k))
                sys.exit(1)

        url = cloud_config["backend_url"] + "/v1/agent/rasp/auth"
        headers = {
            "X-OpenRASP-AppSecret": cloud_config["app_secret"],
            "X-OpenRASP-AppID": cloud_config["app_id"]
        }
        try:
            r = requests.post(url=url, headers=headers, json=[], timeout=3)
            if r.status_code == 200:
                response = json.loads(r.text)
                if response["status"] != 0:
                    print("[!] Test cloud server failed, got HTTP code: {} with response: {} from cloud server: {}, check option startswith 'cloud_api' in config file!".format(r.status_code, r.text, url))
                    sys.exit(1)
            else:
                print("[!] Test cloud server failed, got HTTP code: {} from cloud server: {}, check option startswith 'cloud_api' in config file!".format(r.status_code, url))
                sys.exit(1)
        except Exception:
            print("[!] Cloud server url:{} connect failed, check option startswith 'cloud_api' in config file!".format(url))
            sys.exit(1)


def check_start():
    """
    检测后台启动是否成功
    """
    import requests
    port = Config().get_config("preprocessor.http_port")
    path = Config().get_config("preprocessor.api_path")
    url = "http://127.0.0.1:{}{}".format(port, path)
    for i in range(15):
        try:
            r = requests.get(url=url, timeout=2)
            if r.status_code == 200:
                return True
            break
        except Exception:
            time.sleep(2)
    return False


def detach_run():
    """
    后台运行
    """
    pid = os.fork()
    if pid != 0:
        if pid < 0:
            print("[!] Openrasp IAST start error, fork failed!")
            os._exit(0)
        elif not check_start():
            print("[!] Openrasp IAST start error, check logs/error.log for more info!")
            os._exit(0)

        if hasattr(sys, "_MEIPASS"):
            # pyinstaller运行时，防止tmp目录被删除
            print("[-] OpenRASP-IAST start success, front process will be killed!")
            os.kill(os.getpid(), 9)
        else:
            print("[-] OpenRASP-IAST start success!")
            os._exit(0)

    print("[-] OpenRASP-IAST is Starting...")
    os.close(0)
    sys.stdin = open(os.devnull, "r")
    os.close(1)
    sys.stdout = open(os.devnull, 'w')
    os.close(2)
    sys.stderr = open(os.devnull, 'w')
    os.setsid()
    os.umask(0)


def start(args):
    """
    启动
    """
    Config().load_config(args.config_path)

    init_check()

    real_log_path = os.path.realpath(Config().get_config("log.path"))
    log_level = Config().get_config("log.level").upper()
    print("[-] Log file will generate to {}, log level: {}".format(real_log_path, log_level))

    pid, config_path = Config().get_running_info()
    if pid != 0:
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            print("[!] OpenRASP-IAST is already Running!")
            return

    from core.launcher import Launcher

    if not args.foreground:
        detach_run()

    Config().set_running_info()
    Launcher().launch()


def stop(args):
    """
    停止
    """
    pid, config_path = Config().get_running_info()
    if pid == 0:
        print("[!] OpenRASP-IAST is not Running!")
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        else:
            time.sleep(2)
        try:
            os.kill(pid, 0)
        except OSError:
            Config().reset_running_info()
            print("[-] OpenRASP-IAST stopped!")
        else:
            print("[!] Stop OpenRASP-IAST failed!")


def restart(args):
    """
    重启
    """
    # 先获取运行时的配置文件路径
    pid, config_path = Config().get_running_info()
    stop(args)
    args.foreground = False
    if config_path != "":
        args.config_path = config_path
    else:
        args.config_path = None
    start(args)


def set_config(args):
    """
    修改配置文件
    """
    Config().generate_config(args.output_path)
    Config().load_config(args.output_path)
    if args.data_port is not None:
        Config().config_dict["preprocessor.http_port"] = args.data_port
    if args.web_port is not None:
        Config().config_dict["monitor.console_port"] = args.web_port
    if args.cloud_enable is not None:
        if args.cloud_enable == "true":
            Config().config_dict["cloud_api.enable"] = True
        else:
            Config().config_dict["cloud_api.enable"] = False
    if args.backend_url is not None:
        Config().config_dict["cloud_api.backend_url"] = args.backend_url
    if args.app_secret is not None:
        Config().config_dict["cloud_api.app_secret"] = args.app_secret
    if args.app_id is not None:
        Config().config_dict["cloud_api.app_id"] = args.app_id
    if args.mysql_url is not None:
        try:
            urllib.parse.uses_netloc.append("mysql")
            url = urllib.parse.urlparse(args.mysql_url)
            Config().config_dict["database.host"] = url.hostname if url.hostname is not None else "127.0.0.1"
            Config().config_dict["database.port"] = int(url.port) if url.port is not None else 3306
            Config().config_dict["database.username"] = url.username if url.username is not None else "root"
            Config().config_dict["database.password"] = url.password if url.password is not None else ""
            Config().config_dict["database.db_name"] = url.path[1:]
        except Exception as e:
            print(e)
            print("[!] Can't resolve mysql connection url: {}".format(args.mysql_url))
            sys.exit(1)
    if args.log_level is not None:
        Config().config_dict["log.level"] = args.log_level
    Config().save_config()


def show_version(args):
    print("OpenRASP-IAST v1.2")


def run():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')

    subparsers = parser.add_subparsers(title="options")

    parser_start = subparsers.add_parser('start', help='start help')
    parser_start.set_defaults(func=start)
    parser_start.add_argument(
        "-f", "--foreground", help="Run in foreground", action="store_true")
    parser_start.add_argument(
        "-c", "--config-path", help="Assign config file path, like /path/to/config.yaml")

    parser_stop = subparsers.add_parser('stop', help='stop help')
    parser_stop.set_defaults(func=stop)

    parser_restart = subparsers.add_parser('restart', help='restart help')
    parser_restart.set_defaults(func=restart)

    # 显示版本
    parser_config = subparsers.add_parser('version', help='show version')
    parser_config.set_defaults(func=show_version)

    # 修改配置
    parser_config = subparsers.add_parser('config', help='config help')
    parser_config.set_defaults(func=set_config)

    # 输出路径
    parser_config.add_argument(
        "-o", "--output-path",
        help="Assign path config file path to generate, default is /home/username/openrasp-iast/config.yaml", 
        type=str, default=None, nargs='?')

    # Preprocessor 模块
    parser_config.add_argument(
        "-d", "--data-port", help="Assign data http server port", type=int)

    # Monitor 模块
    parser_config.add_argument(
        "-w", "--web-port", help="Assign web console http server port", type=int)
    parser_config.add_argument(
        "-e", "--cloud-enable", help="Enable upload report to cloud server", type=bool)
    parser_config.add_argument(
        "-c", "--backend-url", help="Assign cloud server url", type=str)
    parser_config.add_argument(
        "-b", "--app-secret", help="Assign cloud server secret key", type=str)
    parser_config.add_argument(
        "-a", "--app-id", help="Assign cloud server app_id", type=str)

    # DB
    parser_config.add_argument(
        "-m", "--mysql-url", help="Assign Mysql connection url", type=str)

    # log
    parser_config.add_argument(
        "-l", "--log-level", help="Assign log level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])

    args = parser.parse_args()

    if len(vars(args)) == 0:
        parser.print_help()
    else:
        args.func(args)


if __name__ == '__main__':
    run()
