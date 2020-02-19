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
import time
import peewee
import asyncio
import peewee_async

from core.model import base_model
from core.components import common
from core.components import exceptions
from core.components import rasp_result
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class NewRequestModel(base_model.BaseModel):

    def __init__(self, *args, **kwargs):
        """
        初始化
        """
        super(NewRequestModel, self).__init__(*args, **kwargs)
        self._init_start_id()

    def _create_model(self, db, table_prefix):
        """
        创建数据model
        """
        meta_dict = {
            "database": db,
            "table_name": table_prefix + "_" + "ResultList"
        }

        meta = type("Meta", (object, ), meta_dict)
        model_dict = {
            "id": peewee.AutoField(),
            "data": self.LongTextField(),
            # utf8mb4 编码下 1 char = 4 bytes，会导致peewee创建过长的列导致MariaDB产生 1071, Specified key was too long; 错误, max_length不使用255
            "data_hash": peewee.CharField(unique=True, max_length=63),
            # scan_status含义： 未扫描：0, 已扫描：1, 正在扫描：2, 扫描中出现错误: 3
            "scan_status": peewee.IntegerField(default=0),
            "time": peewee.IntegerField(default=common.get_timestamp),
            "Meta": meta
        }
        self.ResultList = type("ResultList", (peewee.Model, ), model_dict)
        return self.ResultList

    def _init_start_id(self):
        """
        初始化start_id为未扫描的最小id，未扫描时，值为0

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        query = self.ResultList.select(peewee.fn.MIN(self.ResultList.id)).where(
            self.ResultList.scan_status != 1
        )
        try:
            result = query.scalar()
        except Exception as e:
            Logger().critical("DB error in method _init_start_id!", exc_info=e)
        if result is None:
            self.start_id = 0
        else:
            self.start_id = result - 1

    def reset_unscanned_item(self):
        """
        重置未扫描的item的status为初始状态码(0)

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            self.ResultList.update(scan_status=0).where(
                self.ResultList.scan_status > 1).execute()
        except Exception as e:
            Logger().critical("DB error in method reset_unscanned_item!", exc_info=e)

    def get_start_id(self):
        """
        获取当前start_id

        Returns:
            start_id, int类型
        """
        return self.start_id

    async def put(self, rasp_result_ins):
        """
        将rasp_result_ins序列化并插入数据表

        Returns:
            插入成功返回True, 重复返回False

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            data = {
                "data": rasp_result_ins.dump(),
                "data_hash": rasp_result_ins.get_hash()
            }
            await peewee_async.create_object(self.ResultList, **data)
        except peewee.IntegrityError as e:
            return False
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            Logger().critical("DB error in method put!", exc_info=e)
        else:
            return True

    async def get_new_scan(self, count=1):
        """
        获取多条未扫描的请求数据

        Parameters:
            count - 最大获取条数，默认为1

        Returns:
            获取的数据组成的list,每个item为一个dict, [{id:数据id, data:请求数据的json字符串} ... ]

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        result = []
        try:
            # 获取未扫描的最小id
            query = self.ResultList.select(peewee.fn.MIN(self.ResultList.id)).where((
                self.ResultList.id > self.start_id) & (
                self.ResultList.scan_status == 0)
            )
            fetch_star_id = await peewee_async.scalar(query)
            if fetch_star_id is None:
                return []

            # 将要获取的记录标记为扫描中
            query = self.ResultList.update(
                {self.ResultList.scan_status: 2}
            ).where((
                self.ResultList.scan_status == 0) & (
                self.ResultList.id > self.start_id)
            ).order_by(
                self.ResultList.id
            ).limit(count)

            row_count = await peewee_async.execute(query)
            if (row_count == 0):
                return result

            # 获取标记的记录
            query = self.ResultList.select().where((
                self.ResultList.id >= fetch_star_id) & (
                self.ResultList.scan_status == 2)
            ).order_by(
                self.ResultList.id
            ).limit(row_count)

            data = await peewee_async.execute(query)

            for line in data:
                result.append({
                    "id": line.id,
                    "data": rasp_result.RaspResult(line.data)
                })
            return result

        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            self._handle_exception("DB error in method get_new_scan!", e)

    async def mark_result(self, last_id, failed_list):
        """
        将id 小于等于 last_id的result标记为已扫描，更新star_id, 将failed_list中的id标记为失败

        Parameters:
            last_id - 已扫描的最大id
            failed_list - 扫描中出现连接失败的url

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        if last_id > self.start_id:
            try:

                # 标记失败的扫描记录
                query = self.ResultList.update({self.ResultList.scan_status: 3}).where((
                    self.ResultList.id <= last_id) & (
                    self.ResultList.id > self.start_id) & (
                    self.ResultList.id << failed_list)
                )
                await peewee_async.execute(query)

                # 标记已扫描的记录
                query = self.ResultList.update({self.ResultList.scan_status: 1}).where((
                    self.ResultList.id <= last_id) & (
                    self.ResultList.id > self.start_id) & (
                    self.ResultList.scan_status == 2)
                )
                await peewee_async.execute(query)

                # 更新start_id
                query = self.ResultList.select(peewee.fn.MAX(self.ResultList.id)).where((
                    self.ResultList.id > self.start_id) & (
                    self.ResultList.scan_status == 1)
                )

                result = await peewee_async.scalar(query)
            except asyncio.CancelledError as e:
                raise e
            except Exception as e:
                self._handle_exception("DB error in method mark_result!", e)

            if result is not None:
                self.start_id = result

    async def get_scan_count(self):
        """
        获取扫描进度

        Returns:
            total, count 均为int类型，total为数据总数，count为已扫描条数

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        try:
            query = self.ResultList.select(
                peewee.fn.COUNT(self.ResultList.id)).where(
                self.ResultList.scan_status == 1)

            result = await peewee_async.scalar(query)
            if result is None:
                scanned = 0
            else:
                scanned = result

            query = self.ResultList.select(
                peewee.fn.COUNT(self.ResultList.id)).where(
                self.ResultList.scan_status == 3)

            result = await peewee_async.scalar(query)
            if result is None:
                failed = 0
            else:
                failed = result

            query = self.ResultList.select(
                peewee.fn.COUNT(self.ResultList.id))

            result = await peewee_async.scalar(query)
            if result is None:
                total = 0
            else:
                total = result
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            self._handle_exception("DB error in method get_scan_count!", e)

        return total, scanned, failed

    async def get_last_time(self):
        """
        获取最近一条记录的时间戳, 无记录时返回0

        Returns:
            int, 时间戳

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        query = self.ResultList.select().order_by(self.ResultList.time.desc()).limit(1)

        try:
            result = await peewee_async.execute(query)
            data = await peewee_async.execute(query)
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            self._handle_exception("DB error in method get_last_time!", e)

        if len(data) == 0:
            return 0
        else:
            return data[0].time

    async def get_urls(self, page=1, status=0):
        """
        获取指定状态的的url列表

        Parameters:
            page - int, 获取的页数，每页10条
            status - int, url的状态 未扫描：0, 已扫描：1, 正在扫描：2, 扫描中出现错误: 3

        Returns:
            total, urls - total为数据总数, int类型，urls为已扫描的url, list类型, item形式为tuple (url对应id, url字符串)

        Raises:
            exceptions.DatabaseError - 数据库错误引发此异常
        """
        if page <= 0:
            page = 1
        try:
            query = self.ResultList.select(
                peewee.fn.COUNT(self.ResultList.id)).where(
                self.ResultList.scan_status == status)

            result = await peewee_async.scalar(query)
            if result is None:
                total = 0
            else:
                total = result

            query = self.ResultList.select().where(
                self.ResultList.scan_status == status
            ).order_by(
                self.ResultList.id
            ).offset((page - 1) * 10).limit(10)

            data = await peewee_async.execute(query)
            urls = []

            for line in data:
                url_id = line.id
                rasp_result_ins = rasp_result.RaspResult(line.data)
                url = rasp_result_ins.get_url()
                urls.append((url_id, url))
            return total, urls

        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            self._handle_exception("DB error in method get_urls!", e)

    def drop_table(self):
        """
        删除表时更新表状态
        """
        super().drop_table()
        Communicator().update_target_list_status()
