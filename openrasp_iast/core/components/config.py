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
import sys
import yaml
import tempfile
import traceback
import dictdiffer

from core.components import exceptions


class Config(object):

    def __new__(cls):
        """
        单例模式初始化
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Config, cls).__new__(cls)
            cls.instance._init()
        return cls.instance

    def _init(self):
        """
        初始化
        """
        self._config_path_candidate = [
            os.path.expanduser("~") + "/openrasp-iast/config.yaml",
            "/etc/openrasp-iast/config.yaml",
            "./config.yaml"
        ]
        self._default_log_path = os.path.expanduser("~") + "/openrasp-iast/log"

        self._config_path = None
        self.config_dict = None

        file_path = os.path.abspath(__file__)
        main_path = os.path.dirname(file_path) + "/../../"
        self._main_path = os.path.realpath(main_path)

        sys_tmp = tempfile.gettempdir()
        try:
            if not os.path.exists(sys_tmp + "/openrasp-iast"):
                os.makedirs(sys_tmp + "/openrasp-iast")
            else:
                with open(sys_tmp + "/openrasp-iast/file", "w"):
                    pass
                os.remove(sys_tmp + "/openrasp-iast/file")
            self._tmp_path = sys_tmp + "/openrasp-iast"

        except Exception as e:
            print(
                "[!]OpenRASP-IAST init error! Please check if {} is writable".format(sys_tmp))
            traceback.print_exc()
            sys.exit(1)

    def get_main_path(self):
        """
        获取当前iast主目录

        Returns:
            str - 目录字符串
        """
        return self._main_path

    def get_config_path(self):
        """
        获取当前配置文件路径, 不存在返回空字符串

        Returns
            str
        """
        if self._config_path is None:
            return ""
        else:
            return self._config_path

    def save_config(self):
        """
        保存当前配置
        """
        with open(self._config_path, "w") as f:
            content = yaml.dump(self.config_dict)
            f.write(self._set_comment(content))

    def generate_config(self, path=None):
        """
        生成配置模板
        """
        if path is None:
            self._config_path = self._config_path_candidate[0]
            print("[!] No path assigned, generate config file to default path!")
        else:
            self._config_path = path

        self._config_path = os.path.realpath(
            os.path.abspath(self._config_path))

        try:
            with open(self._main_path + "/config.default.yaml", "rb") as f:
                content = f.read()
        except Exception:
            print("[!] Fail to generate config!")
            traceback.print_exc()
            sys.exit(1)

        if os.path.isdir(self._config_path):
            print("[!] Detect config path '{}' is a directory!".format(
                self._config_path))
            print(
                "[!] Config path should be a file path, like /path/to/config.yaml, not directory!")
            sys.exit(1)

        try:
            config_dir = os.path.dirname(self._config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            with open(self._config_path, "wb") as f:
                f.write(content)
        except Exception as e:
            print("[!] Fail to generate config, check if {} is writable!".format(
                self._config_path))
            traceback.print_exc()
            sys.exit(1)

        print("[-] Config file generated to: {}".format(self._config_path))

    def _set_comment(self, config_content):
        """
        为生成的配置文件添加注释
        """
        with open(self._main_path + "/config.default.yaml", "r") as f:
            origin_config = f.read()

        comments = {}
        for line in origin_config.split("\n"):
            if line.find(":") != -1:
                key = line[:line.find(":")]
                comment = line[line.find("#"):]
                comments[key] = comment

        new_content = []
        lines = config_content.split("\n")
        maxlen = 0
        for line in lines:
            if len(line) > maxlen:
                maxlen = len(line)
        maxlen += 1

        for line in lines:
            if line.find(":") != -1:
                key = line[:line.find(":")]
                if key in comments:
                    new_content.append(
                        line + (maxlen - len(line)) * " " + comments[key])
                    continue
            new_content.append(line)

        return "\n".join(new_content)

    def _check_format(self):
        """
        检查配置格式, 使用默认配置代替丢失/错误配置
        """
        with open(self._main_path + "/config.default.yaml", "r") as f:
            origin_config = yaml.load(f, Loader=yaml.FullLoader)

        keys = []
        diff = dictdiffer.diff(origin_config, self.config_dict)
        for item in diff:
            if item[0] == "remove":
                for diff_item in item[2]:
                    key = diff_item[0]
                    keys.append(key)
                    print("[!] Missing config item: {}, use default.".format(key))
            elif item[0] == "change" and not isinstance(item[2][0], type(item[2][1])):
                # 配置只有一层，只取[0]即可
                key = item[1][0]
                keys.append(key)
                print("[!] Config item {} type error, expect {}, found {}, use default value.".format(
                    item[1], type(item[2][0]), type(item[2][1])))
            elif item[0] == "add":
                for diff_item in item[2]:
                    key = diff_item[0]
                    print("[!] Unknow config item {}, ignore.".format(key))
                continue
            else:
                continue
        for key in keys:
            self.config_dict[key] = origin_config[key]

    def get_running_info(self):
        """
        获取运行的主进程pid和配置文件路径

        Returns:
           pid, running_config_path - int, str pid获取失败返回0, config_path获取失败返回空
        """
        try:
            with open(self._tmp_path + "/iast.pid", "r") as f:
                pid = int(f.read())
        except FileNotFoundError:
            pid = 0

        try:
            with open(self._tmp_path + "/iast.config", "r") as f:
                running_config_path = f.read()
        except FileNotFoundError:
            running_config_path = ""

        return pid, running_config_path

    def set_running_info(self):
        """
        保存当前运行的进程pid, 配置文件路径
        """
        with open(self._tmp_path + "/iast.pid", "w") as f:
            f.write(str(os.getpid()))

        with open(self._tmp_path + "/iast.config", "w") as f:
            f.write(self._config_path)

    def reset_running_info(self):
        """
        重置当前运行的进程pid, 配置文件路径
        """
        with open(self._tmp_path + "/iast.pid", "w") as f:
            f.write("0")

        with open(self._tmp_path + "/iast.config", "w") as f:
            f.write("")

    def load_config(self, path=None):
        """
        读取配置文件, 若已经读取不再重复读取

        Parameters:
            path - 读取的目标文件路径, 为None时读取默认文件
        """
        if self.config_dict is not None:
            return
        if path is None:
            for cp in self._config_path_candidate:
                if os.path.isfile(cp):
                    self._config_path = cp
                    break
        else:
            self._config_path = path
        if self._config_path is None or not os.path.isfile(self._config_path):
            # cmd = "'" + sys.argv[0] + " config'"
            # print("[!] OpenRASP-IAST init error, no config file found, use {} to generate a config file!".format(cmd))
            print('[!] No config file found, please refer to https://rasp.baidu.com/doc/install/iast.html#config for initial setup')
            sys.exit(1)

        self._config_path = os.path.realpath(
            os.path.abspath(self._config_path))

        try:
            with open(self._config_path, "r") as f:
                self.config_dict = yaml.load(f, Loader=yaml.FullLoader)

            print("[-] Using config file: {}".format(self._config_path))
            self._check_format()

            try:
                if self.config_dict["log.path"] == "":
                    self.config_dict["log.path"] = self._default_log_path

                if not os.path.exists(self.config_dict["log.path"]):
                    os.makedirs(self.config_dict["log.path"])
                else:
                    with open(self.config_dict["log.path"] + "/log.file", "w") as f:
                        pass
                    os.remove(self.config_dict["log.path"] + "/log.file")
            except Exception as e:
                print("[!] OpenRASP-IAST init error, log path: {} is not writable!".format(
                    os.path.abspath(self.config_dict["log.path"])))
                sys.exit(1)

        except Exception as e:
            print(
                "[!] OpenRASP-IAST load config error! Please check config file: {}! \n".format(self._config_path))
            traceback.print_exc()
            sys.exit(1)

    def get_config(self, name):
        """
        获取配置

        Parameters:
            name - str, 获取的配置名称

        Returns:
            获取到的值
        """
        return self.config_dict[name]
