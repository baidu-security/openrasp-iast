<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);

	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) . '?cmd=';
	$linux   = $baseurl . 'cat+/etc/resolv.conf';
	$windows = $baseurl . 'cmd+/c+whoami';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>004 - 命令执行 - system 方式，有回显</title>
</head>
<body>
	<h1>004 - 命令执行 - system 方式</h1>

	<div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
		若测试用例无法执行，请检查 disable_function 配置，看下 system 函数是否被禁用。
	</div>

	<p>Linux 触发: </p>
	<p>curl -g '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>
	<br>

	<p>Windows 触发: </p>
	<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

	<br><br>
	<p>命令执行结果</p>

<?php 
	if (isset ($_GET['cmd']))
	{
		echo htmlentities(system ($_GET['cmd']));
	}
?>
</body>
</html>