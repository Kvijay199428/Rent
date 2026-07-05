import paramiko
import zipfile

ZIP_FILE = r"d:\VEGA\RENT\update.zip"

print("--- LOCAL ZIP CONTENTS (First 20 items in static/) ---")
with zipfile.ZipFile(ZIP_FILE, 'r') as z:
    static_files = [f for f in z.namelist() if f.startswith('static/')]
    print(static_files[:20])

print("\n--- SERVER DIAGNOSTICS ---")
HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"
REMOTE_DIR = "/home/vega/rent-receipt"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

commands = [
    "cat /home/vega/rent-receipt/.dockerignore",
    "docker exec rent_app_20081 ls -la /app",
    "docker exec rent_app_20081 ls -la /app/static",
    "ls -la /home/vega/rent-receipt",
    "ls -la /home/vega/rent-receipt/static",
]

for cmd in commands:
    print(f"\n> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("STDOUT:", stdout.read().decode('utf-8', errors='replace'))
    err = stderr.read().decode('utf-8', errors='replace')
    if err:
        print("STDERR:", err)

ssh.close()
