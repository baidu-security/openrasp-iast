/**
 * @file utils.js
 * Created by jason on 17/11/30.
 * PyCharm
 */

define(['app'], function (app) {
    app.factory('serviceUtils', function ($rootScope, $log) {
        var utilsService = {};

        utilsService.saveChartImg = function (chart, fileName) {
            // $log.info(chart);
            var image = chart.getDataURL();
            $log.info(image.length);

            var aTag = document.createElement('a');
            aTag.href = image;
            aTag.download = fileName;
            document.body.appendChild(aTag);
            aTag.click();
            document.body.removeChild(aTag);
            return;
        };

        return utilsService;
    });
});