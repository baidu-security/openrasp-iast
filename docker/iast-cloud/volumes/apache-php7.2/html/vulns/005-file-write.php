<html>
<head>	
	<meta charset="UTF-8"/>
	<title>005 - 任意文件写入 - file_put_contents 方式</title>
</head>
<body>
<h1>005 - 任意文件写入 - file_put_contents 方式</h1>

<p>正常调用：</p>
<pre>curl <?php echo 'http://'.$_SERVER['HTTP_HOST'].$_SERVER['PHP_SELF'].' -d "name=user.txt&data=123"'?></pre>
<br>

<p>不正常调用：</p>
<pre>curl <?php echo 'http://'.$_SERVER['HTTP_HOST'].$_SERVER['PHP_SELF'].' -d "name=1.php&data=&lt;?php phpinfo(); ?>"'?></pre>

<?php 
	if (isset ($_POST['name']) && isset ($_POST['data']))
	{
		$dest   = __DIR__ . '/uploads/' . $_POST['name'];
		$status = file_put_contents($dest, $_POST['data']);
		if ($status)
		{
			echo "文件上传成功: $dest\n<br/>";
		}
		else
		{
			echo "上传失败，可能是 uploads 目录没有写权限？\n<br/>";
		}
	}
?>
</body>
</html>
