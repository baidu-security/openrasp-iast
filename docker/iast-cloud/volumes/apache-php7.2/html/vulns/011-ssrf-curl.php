<?php
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'] . '?url=';
	$any1    = $baseurl . 'http://192.168.154.200.xip.io';
	$any2    = $baseurl . 'http://10.10.10.10';
	$any3    = $baseurl . 'file:///etc/passwd';
?>
<html>
<head>
    <meta charset="UTF-8"/>
    <title>011 - SSRF - cURL 方式</title>
</head>
<body>
	<h1>011 - SSRF - cURL 方式</h1>

	<p>不正常调用 - dnslog:</p>
	<pre>curl '<a href="<?php echo $any1 ?>" target="_blank"><?php echo $any1 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<p>不正常调用 - IP形式:</p>
	<pre>curl '<a href="<?php echo $any2 ?>" target="_blank"><?php echo $any2 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<p>不正常调用 - 读取文件:</p>
	<pre>curl '<a href="<?php echo $any3 ?>" target="_blank"><?php echo $any3 ?></a>'</pre>
	<pre>说明: 参数 url 为请求的 url</pre>

	<br>
	<p>响应内容</p>
<?php 
	$url = @$_GET['url'];
	if(isset($url))
	{
		$ch = curl_init($url);
		curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
		curl_setopt($ch, CURLOPT_NOSIGNAL, 1);
		curl_setopt($ch, CURLOPT_NOBODY, FALSE); 
		curl_setopt($ch, CURLOPT_TIMEOUT_MS, 200);
		echo curl_exec($ch);		
	}
?>
</body>
</html>