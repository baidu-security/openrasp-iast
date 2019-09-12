/**
 * @file Describe the file
 * Created by gmh on 2019/07/17.
 */
'use strict';

define([], function () {
    return function ($scope, $http) {
        var getAllUrl = '/api/model/get_all';
        var continueUrl = '/api/scanner/resume';
        var cancelUrl = '/api/scanner/cancel';
        var pauseUrl = '/api/scanner/pause';
        var stopUrl = '/api/scanner/kill';
        var cleanUrl = '/api/model/clean_target';
        var startTaskUrl = '/api/scanner/new';
        var autoStartUrl = '/api/scanner/auto_start';
        var autoStartStatusUrl = '/api/scanner/auto_start_status';
        var getConfigUrl = '/api/scanner/get_config';
        var setConfigUrl = '/api/scanner/config';
        $scope.data = [];
        $scope.scannerIds = [];
        $scope.eachTask = [];
        $scope.loadIcon = [];
        $scope.description = '';
        $scope.status = '';
        $scope.count = 0;
        $scope.taskId = '';
        $scope.refreshFreq = true;
        $scope.autoStartFlag = false;
        // 分页
        $scope.startRecordIdx = 0;
        $scope.endRecordIdx = 0;
        $scope.maxSize = 10;
        $scope.count = 0;
        $scope.currentPage = 1;
        $scope.perPageRecord = 20;

        //$scope.msg = "";
        $scope.modalDisplay = "modal";
        $scope.running = "运行中";
        $scope.cancel = "终止";
        $scope.pause = "暂停";
        $scope.unknown = "未知状态";
        $scope.unscanned = "未启动";

        var getAllTasks = function(){
            $http({
                method: 'post',
                url: getAllUrl,
                data: {},
                headers: {'Content-Type': 'application/json'}
            })
            .then(function (response) {
                //$scope.responseStatus = response.data['status'];
                $scope.data = [];
                if(status == 0){
                    $scope.count = Object.keys(response.data['data']).length
                    var tmp_data = response.data['data']
                    $scope.data = tmp_data;
                    $scope.displayRecord();
                }else{
                    alert(response.data['description'])
                }
            })
            .catch(function (result) {
                var err = result.data;
                if (err != undefined){
                    alert(err)
                }
            });
        }

        getAllTasks();
        // driver refresh
        $scope.refreshDriver = function(){
            getAllTasks();
            getRequest(autoStartStatusUrl, {})
            .then(function (response) {
                var status = response.data['status'];
                if(status != 0){
                   alert(response.data['description']);
                }else{
                    $scope.autoStartFlag = response.data['data']['status'];
                }
            })
            .catch(function (result) {
                var err = result.data;
                if (err != undefined){
                    alert(err)
                }
            });
        }

        $scope.$watch('urlWhiteRegex',function(newVal,oldVal){
            try {
                new RegExp($scope.urlWhiteRegex)
                $scope.regLegal = true
            } catch (error) {
                $scope.regLegal = false
            }
        })

        $scope.displayRecord = function(){
            $scope.eachTask = [];
            $scope.scannerIds = [];
            $scope.startRecordIdx = ($scope.currentPage - 1) * $scope.perPageRecord;
            $scope.endRecordIdx = $scope.startRecordIdx + $scope.perPageRecord;
            if($scope.endRecordIdx > $scope.count){
                $scope.endRecordIdx = $scope.count;
            }
            for(var i = $scope.startRecordIdx; i < $scope.endRecordIdx; i++){
                $scope.eachTask.push(i);
                $scope.loadIcon.push(false);
                $scope.getTaskStatus(i);
                $scope.scannerIds.push($scope.data[i].id);
            }
        }
        //auto refresh
        setInterval(function (){
            if ($scope.refreshFreq){
                $scope.refreshDriver();
            }
        }, 3000);

        var getRequest = function(url, data){
            return $http({
                method: 'post',
                url: url,
                data: data,
                headers: {'Content-Type': 'application/json'}
            })
        }

        var getConfig = function(taskId){
            var host = $scope.data[taskId].host
            var port = $scope.data[taskId].port
            getRequest(getConfigUrl, {"host": host, "port": port})
            .then(function (response) {
                var status = response.data['status'];
                if(status != 0){
                   alert(response.data['description']);
                }
                $scope.config = response.data["data"]
                $scope.plugins = $scope.config.scan_plugin_status
                var scan_rate = $scope.config.scan_rate
                $scope.concurrent = scan_rate.max_concurrent_request
                $scope.minInterval = scan_rate.min_request_interval
                $scope.maxInterval = scan_rate.max_request_interval
                $scope.urlWhiteRegex = $scope.config.white_url_reg
                $scope.scanProxy = $scope.config.scan_proxy
            })
            .catch(function (result) {
                var err = result.data;
                if (err != undefined){
                    alert(err)
                }
            });
        }

        $scope.setTaskId = function(taskId, task){
            $scope.taskId = taskId;
            getConfig(taskId);
            $scope.task = task;
        }

        $scope.setRefreshFreq = function(){
            $scope.refreshFreq = !$scope.refreshFreq;
        }

        <!--to display task status-->
        $scope.getTaskStatus = function (taskId) {
            var scannerId = $scope.data[taskId].id
            if (scannerId == undefined){
                $scope.status = $scope.unscanned;
            }else{
                $scope.status = $scope.running;
            }
            return $scope.status;
        }

        // stop specific task
        $scope.stopTask = function(taskId){
            // var reallyStop = confirm("真的要终止该任务?")
            // if(reallyStop == true){
                $scope.loadIcon[taskId] = true;
                var scannerId = $scope.data[taskId].id
                getRequest(stopUrl, {"scanner_id":  Number(scannerId)})
                .then(function (response) {
                    var status = response.data['status'];
                    getAllTasks();
                    if(status == 0){
                        // alert('终止成功!');
                    }else{
                        alert(response.data['description'])
                    }
                    $scope.loadIcon[taskId] = false;
                })
                .catch(function (result) {
                    var err = result.data;
                    if (err != undefined){
                        alert(err)
                    }
                });
            // }
        }

        // clean task
        $scope.cleanTask = function(taskId, urlOnly){
            if(urlOnly == false){
                var reallyClean = confirm("确认删除任务?")
                if(reallyClean == true){
                    var host = $scope.data[taskId].host
                    var port = $scope.data[taskId].port
                    getRequest(cleanUrl, {"host": host, "port": port, "url_only": false})
                    .then(function (response) {
                        var status = response.data['status'];
                        getAllTasks();
                        if(status == 0){
                            alert("清除成功!");
                        }else {
                            alert(response.data['description']);
                        }
                    })
                    .catch(function (result) {
                        var err = result.data;
                        if (err != undefined){
                            alert(err)
                        }
                    });
                }
            }else{
                var tmpUrlOnly = confirm("确认清空扫描队列?")
                if(tmpUrlOnly == true){
                    var host = $scope.data[taskId].host
                    var port = $scope.data[taskId].port
                    getRequest(cleanUrl, {"host": host, "port": port, "url_only": true})
                    .then(function (response) {
                        var status = response.data['status'];
                        getAllTasks();
                        if(status == 0){
                            alert("清除成功!");
                        }else {
                            alert(response.data['description']);
                        }
                    })
                    .catch(function (result) {
                        var err = result.data;
                        if (err != undefined){
                            alert(err)
                        }
                    });
                }
            }
        }

        // set plugin status
        $scope.setPluginStatus = function(pl){
            $scope.config.scan_plugin_status[pl].enable = !$scope.config.scan_plugin_status[pl].enable
        }

        $scope.reset = function(){
            $scope.concurrent = undefined;
            $scope.minInterval = undefined;
            $scope.maxInterval = undefined;
        }

        // set config task
        $scope.setConfigTask = function(taskId){
            var host = $scope.data[taskId].host
            var port = $scope.data[taskId].port
            //msg = $scope.msg;
            $scope.modalDisplay = "modal";
            $scope.concurrent = isNaN(Number($scope.concurrent))? undefined:Number($scope.concurrent);
            $scope.minInterval = isNaN(Number($scope.minInterval))? undefined:Number($scope.minInterval);
            $scope.maxInterval = isNaN(Number($scope.maxInterval))? undefined:Number($scope.maxInterval);
            $scope.urlWhiteRegex == undefined? "":$scope.urlWhiteRegex;
            $scope.scanProxy == undefined? "":$scope.scanProxy;

            if($scope.regLegal && $scope.concurrent > 0 && $scope.maxInterval > 0 && $scope.minInterval >= 0){
                if($scope.minInterval <= $scope.maxInterval){
                    getRequest(setConfigUrl, {
                        "host": host,
                        "port": port,
                        "config": {
                            "scan_plugin_status": $scope.config.scan_plugin_status,
                            "scan_rate": {
                                "max_concurrent_request": $scope.concurrent,
                                "max_request_interval": $scope.maxInterval,
                                "min_request_interval": $scope.minInterval
                            },
                            "white_url_reg": $scope.urlWhiteRegex,
                            "scan_proxy": $scope.scanProxy
                        }
                     })
                    .then(function (response) {
                        var status = response.data['status'];
                        if(status == 0){
                            alert("设置成功");
                            $scope.concurrent = undefined;
                            $scope.minInterval = undefined;
                            $scope.maxInterval = undefined;
                        }else{
                            alert(response.data['description']);
                        }
                    })
                    .catch(function (result) {
                        var err = result.data;
                        if (err != undefined){
                            alert(err)
                        }
                    });
                }else{
                    $scope.minInterval = undefined
                    alert("最小间隔不应超过最大间隔")
                    $scope.modalDisplay = false;
                    //$scope.msg = undefined
                }
            }else{
                $scope.modalDisplay = false;
            }
        }

        //start task
        $scope.startTask = function(taskId) {
            $scope.loadIcon[taskId] = true;
            var host = $scope.data[taskId].host
            var port = $scope.data[taskId].port
            getRequest(startTaskUrl,
            {"host": host, "port": port, "config": {}})
            .then(function (response) {
                var status = response.data['status'];
                getAllTasks();
                if(status == 0){
                    // alert("启动扫描任务成功！");
                }else {
                    alert(response.data['description']);
                }
                $scope.loadIcon[taskId] = false;
            })
            .catch(function (result) {
                var err = result.data;
                if (err != undefined){
                    alert(err)
                }
            });
        }

        // auto start
        $scope.autoStartTask = function() {
            $scope.autoStartFlag = !$scope.autoStartFlag
            getRequest(autoStartUrl, {"auto_start": $scope.autoStartFlag})
            .then(function (response) {
                var status = response.data['status'];
                if(status != 0){
                   alert(response.data['description']);
                }
            })
            .catch(function (result) {
                var err = result.data;
                if (err != undefined){
                    alert(err)
                }
            });
        }

    };
});
