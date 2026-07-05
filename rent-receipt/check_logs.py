import paramiko
import sys

HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"

print(f"Connecting to {USER}@{HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(HOST, username=USER, password=PASSWORD)

    print("\n--- Live Docker logs (Ctrl+C to stop) ---")
    # get_pty=True merges stderr into stdout
    _, stdout, _ = ssh.exec_command("docker logs -f --tail 50 rent_app_20081", get_pty=True)
    
    try:
        for line in iter(stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nStopped live tracing.")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
    print("\nDone.")
