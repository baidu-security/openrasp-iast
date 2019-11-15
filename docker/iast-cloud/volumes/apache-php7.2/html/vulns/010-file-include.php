<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
    
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) . '?file=';
	$normal  = $baseurl . 'header.php';

	$linux1  = $baseurl . '../../../../../../../../../../../../../var/log/wtmp';
?>

<html>
<head>
	<meta charset="UTF-8"/>
	<title>010 - 任意文件包含 - include 拼接方式</title>

</head>

<body>
	<h1>010 - 任意文件包含 - include 拼接方式</h1>
    <div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
        若测试用例无法执行，请检查 open_basedir 配置，以及文件是否有读取权限。
    </div>
    
	<p>正常调用:</p>
	<pre>curl -g '<a href="<?php echo $normal; ?>" target="_blank"><?php echo $normal; ?></a>'</pre>
	<br>
	
	<p>不正常调用:</p>
	<pre>curl -g '<a href="<?php echo $linux1; ?>" target="_blank"><?php echo $linux1; ?></a>'</pre>

	<br>
	<p>包含内容</p>
<?php
	if (isset ($_GET['file']))
	{
		include (__DIR__ . '/classes/' . $_GET['file']);
	}
?>
</body>
</html>
