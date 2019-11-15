<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);

	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) . '?cmd=';
	$linux   = $baseurl . 'cp+/etc/passwd+/tmp/';
	$windows = $baseurl . 'cmd+/c+calc';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>004 - 命令执行 - exec 方式，无回显</title>
</head>
<body>
	<h1>004 - 命令执行 - exec 方式，无回显</h1>
	<div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
		若测试用例无法执行，请检查 disable_function 配置，看下 exec 函数是否被禁用。
	</div>

	<p>Linux 触发: </p>
	<p>curl -g '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>
	<p>然后检查 /tmp 是否存在 passwd 这个文件</p>
	<br>

	<p>Windows 触发 - 运行计算器: </p>
	<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<?php 
	if (isset ($_GET['cmd']))
	{
		exec ($_GET['cmd']);
	}
?>
</body>
</html>