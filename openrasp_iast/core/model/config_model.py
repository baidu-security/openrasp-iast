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
import json
import peewee
import hashlib
import peewee_async

from core.model import base_model
from core.components import exceptions
from core.components import rasp_result
from core.components.logger import Logger


class ConfigModel(base_model.BaseModel):

    def __init__(self, *args, **kwargs):
        """
        初始化
        """
        super(ConfigModel, self).__init__(*args, **kwargs)

    def _create_model(self, db, table_prefix):
        """
        创建数据model
        """
        meta_dict = {
            "database": db,
            "table_name": "Config"
        }
        meta = type("Meta", (object, ), meta_dict)
        model_dict = {
            "host_port_hash": peewee.CharField(primary_key=True, max_length=63),
            "host_port": peewee.TextField(),
            "config_json": peewee.TextField(),
            "Meta": meta
        }
        self.Config = type("Config", (peewee.Model, ), model_dict)
        return self.Config

    def update(self, host_port, config_json):
        """
        插入或更新一条config数据

        Parameters:
            host_port - str, 配置对应的机器
            config_json - str, 配置内容的json

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        host_port_hash = hashlib.md5(host_port.encode("utf-8")).hexdigest()
        try:
            self.Config.insert(
                host_port_hash=host_port_hash,
                host_port=host_port,
                config_json=config_json
            ).execute()
        except peewee.IntegrityError:
            self.Config.update(
                {
                    self.Config.config_json: config_json
                }
            ).where(
                self.Config.host_port_hash == host_port_hash
            ).execute()
        except Exception as e:
            Logger().critical("Database error in update method!", exc_info=e)
            raise exceptions.DatabaseError

    def get(self, host_port):
        """
        获取指定主机的配置数据

        Parameters:
            host_port - str, 目标主机

        Returns:
            str - json字符串, 不存在时返回None
        
        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            data = self.Config.select().where(
                self.Config.host_port == host_port
            ).execute()
            if len(data) > 0:
                return data[0].config_json
            else:
                return None
        except Exception as e:
            Logger().critical("DB method get Fail!", exc_info=e)
            raise exceptions.DatabaseError

    def delete(self, host_port):
        """
        删除一条配置

        Parameters:
            host_port - str, 删除的目标主机, 为 "all" 则删除所有配置 

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            if host_port != "all":
                self.Config.delete().where(
                    self.Config.host_port == host_port
                ).execute()
            else:
                self.Config.delete().execute()
        except Exception as e:
            Logger().critical("DB method delete Fail!", exc_info=e)
            raise exceptions.DatabaseError