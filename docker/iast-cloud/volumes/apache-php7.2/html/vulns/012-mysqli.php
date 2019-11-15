<?php
    error_reporting(E_ALL);
    ini_set("display_errors", 1);

    $server = isset($_GET["server"]) ? $_GET['server']: '127.0.0.1';
    $user   = isset($_GET["user"])   ? $_GET['user']  : 'test';
    $pass   = isset($_GET["pass"])   ? $_GET['pass']  : 'test';
    $db     = isset($_GET["db"])     ? $_GET['db']    : 'test';
    $id     = isset($_GET['id'])     ? $_GET['id']    : '0';

    if(isset($_SERVER["CONTENT_TYPE"]) && strpos($_SERVER["CONTENT_TYPE"], "application/json") !== false){
        $input = file_get_contents("php://input");
        $input = json_decode($input, true);
        if(isset($input['id'])){
            $id = $input['id'];
        }
    }

    function query($id)
    {
        global $server, $user, $pass, $db;

        $data = array();
        $conn = new mysqli($server, $user, $pass, $db);
            if ($conn->connect_error) {
            echo "MySQL: connection failed: " . $conn->connect_error;
            return;
            }

            $sql    = "SELECT id, name FROM vuln WHERE id = " . $id;
            $result = $conn->query($sql);

            if (! $result) {
            echo 'MySQL: query error: ' . $conn->error;
            return;
            }

            if ($result->num_rows > 0) {
            while($row = $result->fetch_assoc()) {
                $data[] = array("id" => $row["id"], "name" => $row["name"]);
            }
        } else {
            echo "0 results";
        }
        $conn->close();

        return $data;
    }
?>

<html>
<head>
    <meta charset="UTF-8"/>
    <title>012 - SQL 注入测试- MySQLi 方式</title>
    <link rel="stylesheet" href="https://cdn.bootcss.com/bootstrap/3.3.7/css/bootstrap.min.css">
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
    var data = document.getElementById("jsoninput").value;
    var xmlhttp=getXMLHttpRequest();
    xmlhttp.onreadystatechange=function(){
        if (xmlhttp.readyState==4 && xmlhttp.status==200){
            document.body.innerHTML = ""
            document.write(xmlhttp.responseText);
        }
    }
    url = GetUrlRelativePath()
    xmlhttp.open("POST", url, true);
    xmlhttp.setRequestHeader("Content-type","application/json;charset=UTF-8");
    xmlhttp.send(data);
}
</script>
    <div class="container-fluid" style="margin-top: 50px;">
        <div class="row">
            <div class="col-xs-8 col-xs-offset-2">
            <h4>SQL注入 - mysqli 方式</h4>
            <p>第一步: 请以mysql root账号执行下面的语句创建表</p>
            <pre>DROP DATABASE IF EXISTS test;
CREATE DATABASE test;					
grant all privileges on test.* to 'test'@'%' identified by 'test';
grant all privileges on test.* to 'test'@'localhost' identified by 'test';
CREATE TABLE test.vuln (id INT, name text);
INSERT INTO test.vuln values (0, "openrasp");
INSERT INTO test.vuln values (1, "rocks");
</pre>
            </div>
        </div>

        <div class="row">
            <div class="col-xs-8 col-xs-offset-2">
                <p>第二步: 尝试发起SQL注入攻击 - 为了保证性能，默认只会检测长度超过8的语句</p>
                <form action="<?php echo parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?>" method="get">
                    <div class="form-group">
                        <label>服务器地址</label>
                        <input class="form-control" name="server" value="<?php echo $server ?>">
                    </div>
                    <div class="form-group">
                        <label>查询条件</label>
                        <input class="form-control" name="id" value="<?php echo $id ?>" autofocus>
                    </div>

                    <button type="submit" class="btn btn-primary">提交查询</button>                    
                </form>
            </div>
        </div>

        <div class="row">
            <div class="col-xs-8 col-xs-offset-2">
                <form>
                    <div class="form-group">
                        <label>JSON 方式查询</label>
                        <input id="jsoninput" class="form-control" name="id" value='{"id":"<?php echo htmlspecialchars($id, ENT_QUOTES) ?>"}' >
                    </div>
                    <button type="button" onclick="send_json()" class="btn btn-primary">JSON 方式提交查询</button>
                </form>                
            </div>
        </div>

        <div class="row">
            <div class="col-xs-8 col-xs-offset-2">
            <p>第三步: 检查注入结果</p>
            <?php $result = query($id);	?>
            <table class="table">
                <tbody>
                    <?php if (isset ($result)) foreach ($result as $row) {?>
                    <tr>
                        <td><?php echo $row["id"] ?></td>
                        <td><?php echo $row["name"] ?></td>
                    </tr>
                    <?php } ?>
                </tbody>
            </table>
            </div>
        </div>
    </div>


</body>
