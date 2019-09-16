<?php
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?file=';
	$windows = $baseurl . 'C:\Windows\System32\drivers\etc\hosts';
	$linux1  = $baseurl . '/etc/hosts';
	$linux2  = $baseurl . 'file:///etc/hosts';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>002 任意文件读取</title>
</head>
<body>
	<h1>002 - 任意文件读取 - file_get_contents</h1>

<p>Linux 不正常调用</p>
<p>curl '<a href="<?php echo $linux1 ?>" target="_blank"><?php echo $linux1 ?></a>'</p>

<p>Linux 不正常调用 - file:// 协议</p>
<p>curl '<a href="<?php echo $linux2 ?>" target="_blank"><?php echo $linux2 ?></a>'</p>


<br>
<p>windows 不正常调用</p>
<p>curl '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<br>
<p>文件内容</p>
<?php 
	if (isset ($_GET['file']))
	{
		echo file_get_contents($_GET['file']);
	}
?>
</body>
</html>