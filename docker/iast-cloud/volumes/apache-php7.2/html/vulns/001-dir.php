<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);

    $baseurl = 'http://' . $_SERVER['HTTP_HOST'] . parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $linux   = $baseurl . '?dir=/proc';
	$windows = $baseurl . '?dir=C:';
	$linux_json_curl = 'curl -d \'{"dir":"/proc"}\' -H "Content-Type: application/json" \'' . $baseurl . "'";
?>

<html>
<head>
    <meta charset="UTF-8"/>
    <title>001 - 列目录操作</title>
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
    data = '{"dir":"/proc"}';
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



    <h1>001 - 列目录操作 - scandir 方式</h1>

    <div style="display: inline-block; color: #721c24; background: #f8d7da; padding: 10px; ">
        若测试用例无法执行，请检查 open_basedir 配置，以及目录是否有读取权限。
    </div>

<p>Linux 不正常调用: </p>
<p>curl -g '<a href="<?php echo $linux ?>" target="_blank"><?php echo $linux ?></a>'</p>

<br>
<p>Linux 不正常调用（json方式）: </p>
<p><a href=# onclick=send_json() ><?=$linux_json_curl?></a></p>

<br>
<p>windows 不正常调用: </p>
<p>curl -g '<a href="<?php echo $windows ?>" target="_blank"><?php echo $windows ?></a>'</p>

<br>
<p>目录内容</p>
<?php 


    if(isset($_GET['dir'])) {	
        $content = scandir($_GET['dir']);
        foreach ($content as $item)
        {
            echo htmlentities("$item") . "<br/>\n";
        }
    }
    else if(isset($_SERVER["CONTENT_TYPE"]) && strpos($_SERVER["CONTENT_TYPE"], "application/json") !== false){
        $input = file_get_contents("php://input");
        $input = json_decode($input, true);
        if(isset($input['dir'])){
            $content = scandir($input['dir']);
            foreach ($content as $item)
            {
                echo htmlentities("$item") . "<br/>\n";
            }
        }
    }
?>
</body>
</html>