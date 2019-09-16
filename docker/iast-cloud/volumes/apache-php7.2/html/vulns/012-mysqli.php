<?php
   $server = isset($_GET["server"]) ? $_GET['server']: 'mysql5.6';
   $user   = isset($_GET["user"])   ? $_GET['user']  : 'test';
   $pass   = isset($_GET["pass"])   ? $_GET['pass']  : 'test';
   $db     = isset($_GET["db"])     ? $_GET['db']    : 'test';
   $id     = isset($_GET['id'])     ? $_GET['id']    : '0';

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
    <link rel="stylesheet" href="css/bootstrap.min.css">
</head>
<body>
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
				<p>第二步: 尝试发起SQL注入攻击</p>
				<form action="<?php echo $_SERVER['PHP_SELF'] ?>" method="get">
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
