<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
    
	file_put_contents('uploads/hello.txt', '<?php echo "It Works!"; ?>');
	file_put_contents('uploads/hello.jpg', '<?php echo "It Works!"; ?>');

	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
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

    <div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
        若测试用例无法执行，请检查 open_basedir 配置，以及文件是否有读写权限。
    </div>

	<p>不正常调用 - hello.txt 改名为 hello.php</p>
	<pre>curl -g '<a href="<?php echo $any1 ?>" target="_blank"><?php echo $any1 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<p>正常调用 - hello.jpg 改名为 hello.png</p>
	<pre>curl -g '<a href="<?php echo $any2 ?>" target="_blank"><?php echo $any2 ?></a>'</pre>
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