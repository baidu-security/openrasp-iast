<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>005 - 任意文件写入 - file_put_contents 方式</title>
</head>
<body>
<h1>005 - 任意文件写入 - file_put_contents 方式</h1>

	<div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
		若测试用例无法执行，请检查 open_basedir 配置，以及目录是否有写入权限。
	</div>

<p>正常调用：</p>
<pre>curl -g <?php echo 'http://'.$_SERVER['HTTP_HOST'].parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH).' -d "name=user.txt&data=123"'?></pre>
<br>

<p>(注:write script 默认 block action 为 log)不正常调用：</p>
<pre>curl -g <?php echo 'http://'.$_SERVER['HTTP_HOST'].parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH).' -d "name=../uploads/1.php&data=&lt;?php phpinfo(); ?>"'?></pre>

<?php 
	if (isset ($_POST['name']) && isset ($_POST['data']))
	{
		$dest   = __DIR__ . '/uploads/' . $_POST['name'];
		$status = file_put_contents($dest, $_POST['data']);
		if ($status)
		{
			echo "文件上传成功: " . htmlentities($dest) . "\n<br/>";
		}
		else
		{
			echo "上传失败，可能是 uploads 目录没有写权限？\n<br/>";
		}
	}
?>
</body>
</html>
