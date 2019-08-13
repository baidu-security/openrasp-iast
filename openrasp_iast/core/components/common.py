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

import uuid
import time
import random
import string
import socket
import struct

def generate_uuid():
    """
    随机生成uuid

    Returns:
        str, 型如: ce361bf9-48c9-483b-8122-fc9b867869cc
    """
    return str(uuid.uuid4())

def random_str(length=32):
    """
    随机生成包含数字和小写字母的字符串

    Parameters:
        length - int ,字符串长度， 默认32
    
    Returns:
        str, 生成的字符串
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_timestamp():
    """
    获取当前时间戳

    Returns:
        int, 当前时间戳
    """
    return int(time.time())

def bytes2human(num):
    """
    将bytes数值转换为常用单位字符串

    Parameters:
        num - int ,代转换数值

    Returns:
        str, 转换后的字符串
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if num >= prefix[s]:
            value = float(num) / prefix[s]
            return '%.2f %s' % (value, s)
    return '%.2f B' % (num, )

def print_logo():
    logo = ''' :',`                          `:##:`                          `.'; 
 `'@@@+`                  `;#@@@@@@@@@@@;`                  `+@@@+` 
  ,@@@@:    ,##;`    .'@@@@@@@@#'``;#@@@@@@@@'.    `;@@,    ;@@@#,  
  `'@@@@.   `'@@@@@@@@@@@@#;`          `:#@@@@@@@@@@@@'    .#@@@+`  
   .@@@@'`     ,#@@@@#:                      ,#@@@@#:      ;@@@@,   
    ;@@@@,                     ,#@@#:                     .#@@@+`   
    .#@@@+`               `'@@@@@@@@@@@@'.                '@@@#.    
     ;@@@@:          `:@@@@@@@@#,  ,+@@@@@@@#:           ,@@@@'     
     `;.         ,+@@@@@@@#:`          `;#@@@@#:`       `'@@@#.     
            `;@@@@@@@@+`         ::`                 ,@@@@@@@;      
        :#@@@@@@@#,          `:@@@@@@;`         .'@@@@@@@@'`        
       ;@@@@@:`         `                   :#@@@@@@@+.             
       `#@@@+`     ,#@@@@@@#:`         .+@@@@@@@#;`                 
        ;@@@@,        `;@@@@@@@@+,`;#@@@@@@@+.         :+@@:        
        `+@@@+`            .'@@@@@@@@@@#:`           `#@@@#`        
         :@@@@@@'.             `,+@'.             ,+@@@@@@,         
          `,+@@@@@@@#:`                      `;@@@@@@@@'.           
               `;#@@@@@@@+,              ,#@@@@@@@#,`               
                    .'@@@@@@@@'.    .'@@@@@@@#'`                    
                        `,+@@@@@@@@@@@@@@+,`                        
                             `:#@@@@#;`                             
                                                                    
               OpenRASP IAST scanner initializing...               
'''
    print("\n", logo)