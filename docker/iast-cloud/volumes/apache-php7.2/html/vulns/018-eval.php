<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);
    
	$baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) . '?val=';
	$good    = $baseurl . '%24%61%3D%31%3B%20%65%63%68%6F%20%24%61%3B';
	$bad     = $baseurl . '%65%63%68%6F%20%62%61%73%65%36%34%5F%64%65%63%6F%64%65%28%22%4D%54%49%7A%43%67%3D%3D%22%29%3B';
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>018 - eval 代码执行测试</title>
</head>
<body>
	<h1>018 - eval 代码执行测试</h1>

	<div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
		目前我们仅提供一个基于正则的算法模板，如有绕过请自行修改 eval_regex 算法的正则
	</div>

<p>正常调用: </p>
<p>curl -g '<a href="<?php echo $good ?>" target="_blank"><?php echo $good ?></a>'</p>
<br>
<p>不正常调用: </p>
<p>curl -g '<a href="<?php echo $bad ?>" target="_blank"><?php echo $bad ?></a>'</p>

<br>
<p>执行结果</p>

<?php
	if (isset($_GET['val'])) 
	{
		$code = $_GET['val'];
		echo "Executing ", htmlentities($code), "<br/>\n";
		eval($code);
	}
?>

</body>
</html>
