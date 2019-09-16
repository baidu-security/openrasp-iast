<?php
	file_put_contents('uploads/hello.txt', '<?php echo "It Works!"; ?>');
	file_put_contents('uploads/hello.jpg', '<?php echo "It Works!"; ?>');

	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'];
	$any1    = sprintf('%s?from=%s&to=%s', $baseurl, 'uploads/hello.txt', 'uploads/hello.php');
	$any2    = sprintf('%s?from=%s&to=%s', $baseurl, 'uploads/hello.jpg', 'uploads/hello.png');
?>
<html>
<head>
    <meta charset="UTF-8"/>
    <title>009 - 文件重命名 - rename 方式</title>
</head>
<body>
	<h1>009 - 文件重命名 - rename 方式</h1>

	<p>不正常调用 - hello.txt 改名为 hello.php</p>
	<pre>curl '<a href="<?php echo $any1 ?>" target="_blank"><?php echo $any1 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<p>不正常调用 - hello.jpg 改名为 hello.png</p>
	<pre>curl '<a href="<?php echo $any2 ?>" target="_blank"><?php echo $any2 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<br>
	<p>响应内容</p>
<?php 
	$from = @$_GET['from'];
	$to   = @$_GET['to'];

	if (isset ($from) && isset ($to))
	{
		rename ($from, $to);
	}
?>
</body>
</html>