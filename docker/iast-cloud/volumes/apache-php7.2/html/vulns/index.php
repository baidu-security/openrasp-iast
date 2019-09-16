<!DOCTYPE html>
<html>

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenRASP 官方测试用例集合</title>
  <link rel="stylesheet" href="https://cdn.bootcss.com/bootstrap/3.3.7/css/bootstrap.min.css" media="screen">
  <script src="https://cdn.bootcss.com/angular.js/1.6.3/angular.min.js" charset="utf-8"></script>
  <style media="screen">
	thead tr td {
		background-color: #f1f1f1
	}
  </style>
</head>

<body>
  <div ng-app="myapp" ng-controller="main">
	<div class="container" id="main">
		<div class="row">
			<div class="col-xs-12 col-sm-8 col-sm-offset-2">
				<h3 class="text-center">OpenRASP 官方测试用例集合</h3>
                <br/>
				<table class="table table-striped">
					<thead>
						<tr>
							<td>测试用例</td>
							<td>用例路径</td>
						</tr>
					</thead>
					<tbody>
						<tr ng-repeat="a in testcases">
							<td>{{a.name}}</td>
							<td><a target="_blank" ng-href="{{a.path}}">{{a.path}}</a></td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</div>
  </div>
  
  <script type="text/javascript">
    var app = angular.module('myapp', []);

    app.controller('main', ['$scope', '$http',
      function($scope, $http) {

        $scope.testcases = [
        	{"name": "001 - 列目录操作 - scandir 方式", "path": '001-dir.php'},
			{"name": "002 - 任意文件读取 - file_get_contents", "path": '002-file-read.php'},
			{"name": "004 - 命令执行 - exec 方式，无回显", "path": '004-command-1.php'},
			{"name": "004 - 命令执行 - system 方式", "path": '004-command-2.php'},
			{"name": "005 - 任意文件写入 - file_put_contents 方式", "path": '005-file-write.php'},
			{"name": "008 - 任意文件上传 - move_uploaded_file 方式", "path": "008-file-upload.php"},
			{"name": "009 - 文件重命名 - rename 方式", "path": "009-file-rename.php"},
			{"name": "010 - 任意文件包含 - include 方式", "path": "010-file-include.php"},
			{"name": "012 - SSRF - cURL 方式", "path": "011-ssrf-curl.php"},
			{"name": "012 - SQL 注入测试- MySQLi 方式", "path": "012-mysqli.php"},
			{"name": "013 - WebShell - 回调类型后门", "path": "013-webshell-array_walk.php"},
			{"name": "014 - WebShell - 中国菜刀", "path": "014-webshell-eval.php"},
			{"name": "015 - WebShell - 文件上传小马", "path": "015-webshell-dropper.php"},
			{"name": "016 - WebShell - 文件包含方式", "path": "016-webshell-include.php"},
        ]

      }
    ]);
  </script>

</body>
<!-- design, implemented by c0debreak -->
</html>

