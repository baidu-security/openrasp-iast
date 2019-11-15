#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

s = "" 
s = s.replace("+", ' ')
s = s.replace("=", '": "')
s = s.replace("&", '",\n"')
s = '"' + s + '"'
print(s)
##
