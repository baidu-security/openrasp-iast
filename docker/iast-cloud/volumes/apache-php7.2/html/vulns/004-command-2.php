<?php
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?cmd=';
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

	<p>Linux 触发: </p>
	<p>curl '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>
	<br>

	<p>Windows 触发: </p>
	<p>curl '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

	<br><br>
	<p>命令执行结果</p>

<?php 
	if (isset ($_GET['cmd']))
	{
		echo system ($_GET['cmd']);
	}
?>
</body>
</html>