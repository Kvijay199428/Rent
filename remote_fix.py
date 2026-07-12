import paramiko
import sys

HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

cmd = """docker exec rent-app-20081 python -c "
import sqlite3, uuid
DB = '/code/storage/database/rent.db'
conn = sqlite3.connect(DB)
cols = [r[1] for r in conn.execute('PRAGMA table_info(tenants)')]
if 'view_token' not in cols:
    conn.execute('ALTER TABLE tenants ADD COLUMN view_token TEXT')
    for tid, name in conn.execute('SELECT id, name FROM tenants'):
        conn.execute('UPDATE tenants SET view_token=? WHERE id=?', (str(uuid.uuid4()), tid))
    conn.execute(\\"INSERT OR REPLACE INTO app_metadata VALUES ('tenant_schema_version','2')\\")
    conn.commit()
    print('Fixed!')
else:
    print('Already OK')
conn.close()
"
docker restart rent-app-20081
"""

print("Executing Option A fix on remote server...")
stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

while True:
    data = stdout.channel.recv(4096)
    if not data:
        break
    sys.stdout.buffer.write(data)
    sys.stdout.flush()

exit_status = stdout.channel.recv_exit_status()
ssh.close()
print(f"\\nExit status: {exit_status}")
