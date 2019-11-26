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
import time
import peewee
import pymysql
import peewee_async
import threading

from core.components import exceptions
from core.components.logger import Logger
from core.components.config import Config
from core.components.communicator import Communicator


class BaseModel(object):

    mul_lock = threading.Lock()

    class LongTextField(peewee.TextField):
        """
        支持mysql longtext字段
        """
        field_type = 'LONGTEXT'

    def __new__(cls, table_prefix=None, use_async=True, create_table=True, multiplexing_conn=False):
        """
        初始化数据库连接，构造peewee model实例

        Parameters:
            table_prefix - 表名前缀，由扫描目标的 host + "_" + str(port) 组成
            use_async - 是否开启数据库连接的异步查询功能，默认为True
            create_table - 数据表不存在时是否创建，默认为True
            multiplexing_conn - 是否复用连接，为True时，相同的Model的实例会使用同一个连接，默认为False

        Raises:
            create_table为Fasle且目标数据表不存在时，引发exceptions.TableNotExist
        """
        cls.connect_para = {
            "database": Config().get_config("database.db_name"),
            "host": Config().get_config("database.host"),
            "port": Config().get_config("database.port"),
            "user": Config().get_config("database.username"),
            "password": Config().get_config("database.password"),
            "charset": "utf8mb4"
        }

        if not hasattr(cls, "db_created"):
            conn = pymysql.connect(
                host=Config().get_config("database.host"),
                port=Config().get_config("database.port"),
                user=Config().get_config("database.username"),
                passwd=Config().get_config("database.password"),
                charset="utf8mb4"
            )

            cursor = conn.cursor()
            cursor._defer_warnings = True

            sql = "select @@version"
            cursor.execute(sql)
            version = cursor.fetchone()
            charset = "utf8"
            try:
                if version is not None:
                    version = version[0].split(".")
                    if int(version[0]) > 5 or (int(version[0]) == 5 and int(version[1]) > 5):
                        charset = "utf8mb4"
            except Exception:
                pass

            sql = "CREATE DATABASE IF NOT EXISTS {dbname} default charset {charset} COLLATE {charset}_general_ci;".format(
                dbname=Config().get_config("database.db_name"),
                charset=charset
            )

            cursor.execute(sql)
            cursor.close()
            conn.commit()
            conn.close()
            cls.db_created = True

        if multiplexing_conn is True:
            with BaseModel.mul_lock:
                if not hasattr(BaseModel, "mul_database"):
                    BaseModel.mul_database = peewee_async.MySQLDatabase(
                        **cls.connect_para)
                    BaseModel.mul_database.connect()
                    BaseModel.mul_database_timeout = time.time() + 60
                elif time.time() > BaseModel.mul_database_timeout:
                    BaseModel.mul_database.close()
                    BaseModel.mul_database = peewee_async.MySQLDatabase(
                        **cls.connect_para)
                    BaseModel.mul_database.connect()
                    BaseModel.mul_database_timeout = time.time() + 60
        elif isinstance(multiplexing_conn, int):
            with BaseModel.mul_lock:
                if not hasattr(BaseModel, "mul_database"):
                    BaseModel.mul_database = peewee_async.PooledMySQLDatabase(
                        **cls.connect_para,
                        max_connections=multiplexing_conn
                    )

        instance = super(BaseModel, cls).__new__(cls)
        return instance

    def __init__(self, table_prefix=None, use_async=True, create_table=True, multiplexing_conn=False):
        """
        初始化

        Parameters:
            table_prefix - 表名前缀，由扫描目标的 host + "_" + str(port) 组成
            use_async - 是否开启数据库连接的异步查询功能，默认为True
            create_table - 数据表不存在时是否创建，默认为True
            multiplexing_conn - 是否复用连接，为True时，相同的Model的实例会使用同一个连接, 为int时使用该int大小的连接池, 默认为False

        Raises:
            create_table为Fasle且目标数据表不存在时，引发exceptions.TableNotExist
        """
        self.use_async = use_async
        try:
            if multiplexing_conn:
                database = BaseModel.mul_database
            else:
                if self.use_async:
                    database = peewee_async.MySQLDatabase(**self.connect_para)
                else:
                    database = peewee.MySQLDatabase(**self.connect_para)
                database.connect()

            # table_prefix 为None则不建立数据表实例，仅用于调用基类方法
            if table_prefix is not None:
                self._model = self._create_model(database, table_prefix)
                if not self._model.table_exists():
                    if create_table:
                        try:
                            database.create_tables([self._model])
                            Logger().debug("Create table {}_{}".format(table_prefix, self.__class__.__name__))
                            if self.__class__.__name__ == "NewRequestModel":
                                Communicator().update_target_list_status()
                        except peewee.InternalError:
                            pass
                    else:
                        raise exceptions.TableNotExist

            self.database = database
        except exceptions.TableNotExist as e:
            raise e
        except Exception as e:
            Logger().critical("Mysql Connection Fail!", exc_info=e)
            raise exceptions.DatabaseError

    def _create_model(self, db, table_prefix):
        """
        子类实现此方法，构建对应数据表的peewee.Model类
        """
        raise NotImplementedError

    def drop_table(self):
        """
        删除当前实例对应的数据库表

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        try:
            schema_manager = peewee.SchemaManager(self._model)
            schema_manager.drop_table()
        except AttributeError:
            Logger().error("Can not call drop table in base model!")
            raise exceptions.DatabaseError
        except Exception as e:
            Logger().error("Error in method drop table!", exc_info=e)
            raise exceptions.DatabaseError

    def truncate_table(self):
        """
        清空当前实例对应的数据库表

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        try:
            schema_manager = peewee.SchemaManager(self._model)
            schema_manager.truncate_table()
        except AttributeError:
            Logger().error("Can not call truncate table in base model!")
            raise exceptions.DatabaseError
        except Exception as e:
            Logger().error("Error in method truncate table!", exc_info=e)
            raise exceptions.DatabaseError

    def get_tables(self):
        """
        获取当前实例对应的所有数据库表

        Returns:
            list , item为table_name

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        try:
            result = self.database.get_tables()
        except Exception as e:
            Logger().error("Error in method get_tables!", exc_info=e)
            raise exceptions.DatabaseError
        return result

    @staticmethod
    def _creat_conn():
        """
        创建mysql连接
        """
        if not hasattr(BaseModel, "pymysql_conn") or \
           time.time() > BaseModel.pymysql_conn_timeout or \
           not BaseModel.pymysql_conn.open:
            if hasattr(BaseModel, "pymysql_conn"):
                try:
                    BaseModel.pymysql_conn.close()
                except Exception:
                    pass
            BaseModel.pymysql_conn = pymysql.connect(
                port=Config().config_dict["database.port"],
                host=Config().config_dict["database.host"],
                user=Config().config_dict["database.username"],
                passwd=Config().config_dict["database.password"],
                database=Config().config_dict["database.db_name"]
            )
            BaseModel.pymysql_conn_timeout = time.time() + 60

    @staticmethod
    def get_scan_count(target_list):
        """
        获取扫描进度信息

        Parameters:
            target_list - list, item为要获取的主机的host_port

        Returns:
            dict, item形式如下
            {
                "targethost.com_8080":{
                    "total": 10,
                    "scanned": 3,
                    "failed": 5,
                    "last_time": 1571217144
                },
                ...
            }

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        try:
            BaseModel._creat_conn()
            conn = BaseModel.pymysql_conn
            if len(target_list) == 0:
                return {}

            result = {}
            sql = ""
            for target in target_list:
                result[target] = {
                    "total": 0,
                    "scanned": 0,
                    "failed": 0
                }
                sql += "union all ( SELECT '{target}', scan_status, count(*) FROM `{target}_ResultList` group by scan_status) ".format(target=target)
            sql = sql[10:]
            cursor = conn.cursor()
            cursor._defer_warnings = True
            cursor.execute(sql)
            re = cursor.fetchall()
            conn.commit()

            for item in re:
                result[item[0]]["total"] += item[2]
                if item[1] == 1:
                    result[item[0]]["scanned"] = item[2]
                elif item[1] == 3:
                    result[item[0]]["failed"] = item[2]

            return result
        except Exception as e:
            raise exceptions.DatabaseError

    @staticmethod
    def get_last_time(target_list):
        """
        获取扫描目标最近一条记录的时间戳, 无记录时返回0

        Parameters:
            target_list - list, item为要获取的主机的host_port

        Returns:
            dict, item形式如下
            {
                "targethost.com_8080":{
                    "last_time": 1571217144
                },
                ...
            }

        Raises:
            exceptions.DatabaseError - 数据库出错时引发此异常
        """
        try:
            BaseModel._creat_conn()
            conn = BaseModel.pymysql_conn
            if len(target_list) == 0:
                return {}

            sql = ""
            result = {}
            for target in target_list:
                result[target] = {
                    "last_time": 0
                }
                sql += "union all ( SELECT '{target}', time FROM `{target}_ResultList` order by id limit 1) ".format(target=target)
            sql = sql[10:]
            cursor = conn.cursor()
            cursor._defer_warnings = True
            cursor.execute(sql)
            re = cursor.fetchall()
            conn.commit()

            for item in re:
                result[item[0]]["last_time"] = item[1]

            return result
        except Exception as e:
            raise exceptions.DatabaseError
