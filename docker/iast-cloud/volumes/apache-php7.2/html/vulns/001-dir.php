<?php
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?dir=';
	$linux   = $baseurl . '/proc';
	$windows = $baseurl . 'C:';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>001 - 列目录操作</title>
</head>
<body>
	<h1>001 - 列目录操作 - scandir 方式</h1>

<p>Linux 不正常调用: </p>
<p>curl '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>

<br>
<p>windows 不正常调用: </p>
<p>curl '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<br>
<p>目录内容</p>
<?php 

	if (isset($_GET['dir'])) 
	{
		$content = scandir($_GET['dir']);
		foreach (scandir($_GET['dir']) as $item)
		{
			echo "$item<br/>\n";
		}
	}
    
?>
</body>
</html>