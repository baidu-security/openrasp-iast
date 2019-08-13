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


class OriException(Exception):
    pass


# normal exception 此类为调用时的预期异常，应当被正确捕获并处理
class OriExpectedException(OriException):
    pass


# Fatal error 此类异常表示无法正常运行当前逻辑，应交由模块外层循环处理并记录日志，通常意味着错误的使用了某些方法或产生了未知错误
class OriFatalError(OriException):
    pass


# PreprocessorException
class PreprocessorException(OriException):
    pass


class ContentTypeInvalid(PreprocessorException, OriExpectedException):
    def __init__(self):
        message = "Http request content-type is not json"
        super().__init__(message)


# RaspResultException
class RaspResultException(OriException):
    pass


class ResultInvalid(RaspResultException, OriExpectedException):
    def __init__(self):
        message = "Rasp result format is invalid"
        super().__init__(message)


class ResultJsonError(RaspResultException, OriExpectedException):
    def __init__(self):
        message = "Rasp result json decode error"
        super().__init__(message)


class ResultHostError(RaspResultException, OriExpectedException):
    def __init__(self):
        message = "Rasp result get host error"
        super().__init__(message)


class GetQueueIdError(RaspResultException, OriFatalError):
    def __init__(self):
        message = "Try to call get_result_queue_id in Non-scan rasp_result"
        super().__init__(message)


# CommunicatorException
class CommunicatorException(OriException):
    pass


class InternalSharedKeyError(CommunicatorException, OriExpectedException):
    def __init__(self):
        message = "Try to get internal shared key that does not exist!"
        super().__init__(message)


class QueueEmpty(CommunicatorException, OriExpectedException):
    def __init__(self):
        message = "OriQueue which get in communicator is empty"
        super().__init__(message)


class QueueValueError(CommunicatorException, OriExpectedException):
    def __init__(self):
        message = "OriQueue send data too large"
        super().__init__(message)


class QueueNotExist(CommunicatorException, OriFatalError):
    def __init__(self):
        message = "OriQueue which put in communicator is not exist"
        super().__init__(message)


class SharedSettingError(CommunicatorException, OriFatalError):
    def __init__(self):
        message = "Try to get Shared Settings before it set"
        super().__init__(message)


# ScannerException
class ScannerException(OriException):
    pass


class MaximumScannerExceede(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Scanner maximum number exceeded"
        super().__init__(message)


class InvalidScannerId(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Scanner id is not exist or out of range"
        super().__init__(message)


class TargetIsScanning(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Target is scanning by other scanner"
        super().__init__(message)


class TargetNotExist(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Target host_port is not exist"
        super().__init__(message)


class ScanRequestFailed(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Scan request failed!"
        super().__init__(message)


class GetRaspResultFailed(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Get RaspResult failed!"
        super().__init__(message)


class UnsupportedHttpData(ScannerException, OriExpectedException):
    def __init__(self):
        message = "Try make an unsupported http request data!"
        super().__init__(message)


class ForkModuleError(ScannerException, OriFatalError):
    def __init__(self):
        message = "Fork new module process failed"
        super().__init__(message)

class DataParamError(ScannerException, OriFatalError):
    def __init__(self):
        message = "Use invalid param in set/get data method!"
        super().__init__(message)

class CheckTypeNotExist(ScannerException, OriFatalError):
    def __init__(self):
        message = "Try to use an unsupported checl type!"
        super().__init__(message)


class NoPluginError(ScannerException, OriFatalError):
    def __init__(self):
        message = "Scanner not detect any plugin!"
        super().__init__(message)


class UnsupportedPayloadType(ScannerException, OriFatalError):
    def __init__(self):
        message = "Mutant get an unknow payload type!"
        super().__init__(message)


class GetRuntimeConfigFail(ScannerException, OriFatalError):
    def __init__(self):
        message = "Get runtime config from database failed!"
        super().__init__(message)


# DatabaseException


class DatabaseException(OriException):
    pass


class DatabaseError(DatabaseException, OriFatalError):
    def __init__(self):
        message = "Database error when doing connect or query"
        super().__init__(message)


class TableNotExist(DatabaseException, OriExpectedException):
    def __init__(self):
        message = "Try to query with a not exist table"
        super().__init__(message)
