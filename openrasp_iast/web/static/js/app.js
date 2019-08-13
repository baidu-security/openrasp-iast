/**
 * @file Describe the file
 * Created by gaomenghan on 19/07/17.
 */
'use strict';

require.config({
    baseUrl: './../static/js/',
    paths: {
        'angular': './lib/angular/angular.min',
        'angular-route': './lib/angular-route/angular-route.min',
        'angularAMD': './lib/angularAMD/angularAMD.min',
        'ui-bootstrap': 'lib/angular-bootstrap/ui-bootstrap-tpls.min',
    },
    shim: {
        'angular': {exports: 'angular'},
        'angularAMD': ['angular'],
        'angular-route': ['angular'],
        'ui-bootstrap': ['angular'],
    },
    deps: ['app']
});

define([
        'angular',
        'angularAMD',
        'angular-route',
        'ui-bootstrap'
    ],
    function (angular, angularAMD) {
        var registerRoutes = function ($routeProvider) {
            $routeProvider
                .when('/', angularAMD.route({
                    templateUrl: 'static/html/showTask.html',
                    controllerUrl: 'static/js/controllers/showTask.js'
                }))
                .otherwise({redirectTo: '/'});
        };


        var app = angular.module('iastapp', ['ngRoute', 'ui.bootstrap']);
        app.config(['$routeProvider', registerRoutes]);

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
        app.controller('Main', function ($scope, $rootScope, $log, $http, $q, serviceAlert) {
            $scope.controller = 'Main';
            $rootScope.closeAlert = serviceAlert.closeAlert;

        });

        return angularAMD.bootstrap(app);
    });





