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
import json
import time
import pymysql

from testtools import iast_api


def run():
    benchmark_host = _scan()
    # benchmark_host = "192.168.96.6"
    _get_result(benchmark_host)


def _query(sql):
    conn = pymysql.connect(
        host="mysql5.6",
        port=3306,
        user="rasp",
        passwd="rasp123"
    )
    cursor = conn.cursor()
    cursor._defer_warnings = True
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.commit()
    conn.close()
    return result


def _get_result(benchmark_host):
    sql = "select rasp_result_list from openrasp.`{}_8443_Report`".format(benchmark_host)
    result = _query(sql)
    vul_num_list = []
    for item in result:
        item_data = json.loads(item[0])[0]
        url = item_data["context"]["url"]
        task_num = re.findall(r'/(BenchmarkTest\d+)', url, re.I)
        if not len(task_num) == 0:
            vul_num_list.append(task_num[0])

    assert os.path.isfile("benchmark-expected.csv")
    with open("benchmark-expected.csv", "r") as f:
        data = f.readlines()

    data = data[1:]

    # with open("key-para.csv", "r") as f:
    #     key_para_dict = dict.fromkeys(f.read().split("\n"), None)

    test_case_list = {}
    for data_item in data:
        item = data_item.split(",")
        vul_type = item[1]
        is_true = "true" if item[2] == "true" else "false"
        test_case_list[item[0]] = [item[1], is_true, "漏报" if is_true == "true" else "OK"]

    for vul_num in vul_num_list:
        if test_case_list[vul_num][1] == "true":
            test_case_list[vul_num][2] = "OK"
        else:
            test_case_list[vul_num][2] = "误报"

    result = ["测试用例,测试类型,用例是否包含漏洞,检测结果"]
    # result = ["测试用例,测试类型,用例是否包含漏洞,检测结果,使用key做参数"]
    statistics = {}
    for vul_num in test_case_list:
        case_type = test_case_list[vul_num][0]
        is_vuln = True if test_case_list[vul_num][1] == "true" else False
        is_checkout = True if test_case_list[vul_num][2] == "OK" else False

        if case_type not in statistics:
            statistics[case_type] = {
                "total": 0,                 # 总样本
                "checkout": 0,              # 总正确样本
                "vuln_checkout": 0,         # 检出
                "vuln_case": 0,             # 漏洞样本
                "non_vuln_checkout": 0,     # 误报
                "non_vuln_case": 0,         # 无漏洞样本
            }

        statistics[case_type]["total"] += 1
        if is_vuln:
            statistics[case_type]["vuln_case"] += 1
        else:
            statistics[case_type]["non_vuln_case"] += 1

        if is_checkout:
            statistics[case_type]["checkout"] += 1
            if is_vuln:
                statistics[case_type]["vuln_checkout"] += 1
        elif not is_vuln:
            statistics[case_type]["non_vuln_checkout"] += 1

        # key_para = "true" if vul_num in key_para_dict else "false"
        result.append(",".join([vul_num, ] + list(test_case_list[vul_num])))
        # result.append(",".join([vul_num, ] + list(test_case_list[vul_num]) + [key_para, ]))

    if not os.path.isdir("./result"):
        os.makedirs("result")

    with open("./result/benchmark_result.csv", "w") as f:
        f.write("\n".join(result))

    with open("./result/benchmark_statistics.csv", "w") as f:
        f.write("用例类型,漏洞检出,漏洞样本,检出率,漏洞误报,无漏洞样本,误报率,总计正确检测,总计样本,正确率\n")
        for vul_type in statistics:
            f.write("{},{},{},{},{},{},{},{},{},{}\n".format(
                vul_type,
                statistics[vul_type]["vuln_checkout"],
                statistics[vul_type]["vuln_case"],
                "{:.2f}%".format(statistics[vul_type]["vuln_checkout"] / statistics[vul_type]["vuln_case"] * 100),
                statistics[vul_type]["non_vuln_checkout"],
                statistics[vul_type]["non_vuln_case"],
                "{:.2f}%".format(statistics[vul_type]["non_vuln_checkout"] / statistics[vul_type]["non_vuln_case"] * 100),
                statistics[vul_type]["checkout"],
                statistics[vul_type]["total"],
                "{:.2f}%".format(statistics[vul_type]["checkout"] / statistics[vul_type]["total"] * 100)
            ))


def _scan():
    crawled = 0
    benchmark_host = ""
    print("Check if Benchmark has been crawled.")
    while True:
        time.sleep(5)
        hosts = iast_api.get_all()
        for host in hosts:
            if int(host["port"]) == 8443:
                crawled = host["total"]
                break

        print("Benchmark has been crawled {} urls.".format(crawled))
        if crawled > 100:
            benchmark_host = host["host"]
            break

    print("Start scan Benchmark.")
    iast_api.new_scan(benchmark_host, 8443)

    while True:
        time.sleep(5)
        hosts = iast_api.get_all()
        for host in hosts:
            if int(host["port"]) == 8443:
                sid = host["id"]
                total = host["total"]
                scanned = host["scanned"] + host["failed"]
                break

        print("Benchmark scanning {}/{}".format(scanned, total))
        if total == scanned:
            break

    print("Benchmark scan complete.")
    iast_api.kill_scan(sid)
    return benchmark_host
