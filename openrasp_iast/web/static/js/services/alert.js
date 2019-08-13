/**
 * @file alert.js
 * Created by jason on 17/11/29.
 * PyCharm
 */
define(['app'], function (app) {
    app.factory('serviceAlert', function ($rootScope, $log) {
        var alertService = {};
        $rootScope.alerts = [];
        alertService.add = function (type, msg) {
            var levels = {
                'ok': 'success',
                'success': 'success',

                'debug': 'info',
                'msg': 'info',
                'log': 'info',
                'info': 'info',

                'warn': 'warning',
                'warning': 'warning',

                'err': 'danger',
                'error': 'danger',
                'fail': 'danger',
                'fatal': 'danger',
                'danger': 'danger'
            };
            var bFindLevel = false;
            for (var k in levels) {
                if (k === type.toLowerCase()) {
                    type = levels[k];
                    bFindLevel = true;
                }
            }
            if (!bFindLevel) {
                type = 'info';
            }

            $rootScope.alerts.push({'type': type, 'msg': msg});
        };
        alertService.closeAlert = function (index) {
            $log.info(index);
            $rootScope.alerts.splice(index, 1);
        };
        return alertService;
    });
});
