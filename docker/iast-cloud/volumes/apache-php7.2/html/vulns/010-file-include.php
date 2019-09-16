<?php
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?file=';
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

	<p>正常调用:</p>
	<pre>curl '<a href="<?php echo $normal; ?>" target="_blank"><?php echo $normal; ?></a>'</pre>
	<br>
	
	<p>不正常调用:</p>
	<pre>curl '<a href="<?php echo $linux1; ?>" target="_blank"><?php echo $linux1; ?></a>'</pre>

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
