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
import asyncio
import peewee_async

from core.model import base_model
from core.components import common
from core.components import exceptions
from core.components import rasp_result
from core.components.logger import Logger
from core.components.config import Config


class ReportModel(base_model.BaseModel):

    def __init__(self, *args, **kwargs):
        """
        初始化
        """
        super(ReportModel, self).__init__(*args, **kwargs)

    def _create_model(self, db, table_prefix):
        """
        创建数据model
        """
        meta_dict = {
            "database": db,
            "table_name": table_prefix + "_" + "Report"
        }
        meta = type("Meta", (object, ), meta_dict)
        model_dict = {
            "id": peewee.AutoField(),
            "plugin_name": peewee.CharField(max_length=63),
            "description": peewee.TextField(),
            "rasp_result_list": self.LongTextField(),
            "payload_seq": peewee.CharField(unique=True, max_length=63),
            "message": peewee.TextField(),
            "time": peewee.IntegerField(default=common.get_timestamp),
            "upload": peewee.IntegerField(default=0),
            "Meta": meta
        }
        self.Report = type("Report", (peewee.Model, ), model_dict)
        return self.Report

    async def put(self, request_data_list, plugin_name, description, message):
        """
        插入一条RaspResult数据

        Parameters:
            rasp_result_instance - RaspResult实例,待插入的数据
            plugin_name - str, 插件名
            message - str, 漏洞描述

        Returns:
            插入成功返回True, 重复返回False

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            rasp_result_json_list = []
            for request_data in request_data_list:
                rasp_result_json_list.append(json.loads(
                    request_data.get_rasp_result().dump()))
            payload_seq = request_data_list[0].get_payload_info()["seq"]
            data = {
                "plugin_name": plugin_name,
                "description": description,
                "rasp_result_list": json.dumps(rasp_result_json_list),
                "payload_seq": payload_seq,
                "message": message
            }
            await peewee_async.create_object(self.Report, **data)
        except peewee.IntegrityError:
            return False
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            self._handle_exception("DB error in method put!", e)
        else:
            return True

    async def get(self, page=1, perpage=10):
        """
        获取数据

        Parameters:
            page - int, 获取的页码
            perpage - int, 每页的数据条数

        Returns:
            {"total":数据总条数, "data":[ RaspResult组成的list的json字符串, ...]}

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        if page <= 0:
            page = 1
        if perpage <= 0:
            perpage = 1
        result = {}

        try:
            query = self.Report.select().offset((page - 1) * perpage).limit(perpage)
            data = await peewee_async.execute(query)
            result["total"] = len(data)
            result["data"] = []
            for line in data:
                result["data"].append(line.rasp_result_list)
            return result

        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            Logger().critical("DB method get_new_scan Fail!", exc_info=e)
            raise exceptions.DatabaseError

    def get_upload_report(self, count=20):
        """
        获取报警数据

        Parameters:
            count - int, 获取的数量

        Returns:
            list, item为tuple, 格式
            (
                plugin_name, # str, 插件名
                description, # str, 插件描述
                rasp_result_list, # str, 包含rasp_result信息的dict组成的list json序列化后的字符串
                message # str, 漏洞描述信息
                time # int, 时间戳
            )

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        if count <= 0:
            count = 20
        result = []

        try:
            query = self.Report.select().where(self.Report.upload != 1).limit(count)
            data = query.execute()

            for line in data:
                result.append(
                    (
                        line.plugin_name,
                        line.description,
                        line.rasp_result_list,
                        line.message,
                        line.time
                    )
                )
            return result

        except Exception as e:
            self._handle_exception("DB error in method get_new_scan!", e)

    def mark_report(self, count=20):
        """
        标记已上传的报警数据

        Parameters:
            count - int, 标记的数量

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """

        if count <= 0:
            count = 20

        try:
            query = self.Report.update({self.Report.upload: 1}).where(
                self.Report.upload != 1).limit(count)
            query.execute()

        except Exception as e:
            self._handle_exception("DB error in method mark_report!", e)
