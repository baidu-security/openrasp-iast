<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);

	$baseurl  = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ;
	$windows  = $baseurl . '?file=C:\Windows\System32\drivers\etc\hosts';
	$windows2 = $baseurl . '?file=file://C:\Windows\System32\drivers\etc\hosts';
	$linux1   = $baseurl . '?file=/etc/hosts';
	$linux2   = $baseurl . '?file=file:///etc/hosts';
	$linux_json_curl = 'curl -d \'{"file":"/etc/hosts"}\' -H "Content-Type: application/json" ' . $baseurl;
?>

<html>
<head>	
	<meta charset="UTF-8"/>
	<title>002 任意文件读取</title>
</head>
<body>
<script>
function GetUrlRelativePath(){
    var url = document.location.toString();
    var arrUrl = url.split("//");
    var start = arrUrl[1].indexOf("/");
    var relUrl = arrUrl[1].substring(start);
    if(relUrl.indexOf("?") != -1){
        relUrl = relUrl.split("?")[0];
    }
    return relUrl;
}

function getXMLHttpRequest(){
    var xmlhttp;
    if (window.XMLHttpRequest){
        xmlhttp=new XMLHttpRequest();
    }
    else{
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    return xmlhttp;
}

function send_json(){
    data = '{"file":"/etc/hosts"}';
    var xmlhttp=getXMLHttpRequest();
    xmlhttp.onreadystatechange=function(){
        if (xmlhttp.readyState==4 && xmlhttp.status==200){
            document.body.innerHTML = "";
            document.write(xmlhttp.responseText);
        }
    }
    url = GetUrlRelativePath()
    xmlhttp.open("POST", url, true);
    xmlhttp.setRequestHeader("Content-type","application/json;charset=UTF-8");
    xmlhttp.send(data);
}
</script>

	<h1>002 - 任意文件读取 - file_get_contents</h1>

    <div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
        若测试用例无法执行，请检查 open_basedir 配置，以及文件是否有读取权限。
    </div>

<p>Linux 不正常调用</p>
<p>curl -g '<a href="<?php echo $linux1 ?>" target="_blank"><?php echo $linux1 ?></a>'</p>

<br>
<p>Linux 不正常调用 - file:// 协议</p>
<p>curl -g '<a href="<?php echo $linux2 ?>" target="_blank"><?php echo $linux2 ?></a>'</p>

<!-- <br>
<p>Linux 不正常调用（json方式）: </p>
<p><a href=# onclick=send_json() ><?=$linux_json_curl?></a></p> -->

<br>
<p>windows 不正常调用</p>
<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<br>
<p>windows 不正常调用 - file:// 协议</p>
<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows2 ?></a>'</p>

<br>
<p>文件内容</p>
<?php 
    if(isset($_GET['file'])) {	
        echo htmlentities(file_get_contents($_GET['file']));
    }
    else if(strpos(isset($_SERVER["CONTENT_TYPE"]) && $_SERVER["CONTENT_TYPE"], "application/json") !== false){
        $input = file_get_contents("php://input");
        $input = json_decode($input, true);
        if(isset($input['file'])){
            echo htmlentities(file_get_contents($input['file']));
        }
    }
?>
</body>
</html>