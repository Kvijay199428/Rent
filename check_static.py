import paramiko

HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

cmds = [
    "docker exec rent_app_20081 python3 -c \"import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:20081/static/css/style.css'); print('HTTP', r.getcode())\"",
    "docker exec rent_app_20081 python3 -c \"import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:20081/static/js/main.js'); print('HTTP', r.getcode())\"",
    "docker logs rent_app_20081 --tail 15 2>&1",
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(f"==> {cmd[:60]}")
    print(out or err)

ssh.close()
print("Done.")
