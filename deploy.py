import os
import sys
import zipfile
import argparse
import subprocess
import paramiko


HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR = BASE_DIR
ZIP_FILE = os.path.join(BASE_DIR, "update.zip")

REMOTE_ZIP = "/home/vega/update.zip"
REMOTE_DIR = "/home/vega/rent-app-20081"

FRONTEND_DIRS = [
    "frontend/admin-app",
    "frontend/tenant-app",
]

EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "storage",
    "venv",
    ".venv",
    "node_modules",
    "dist-ssr",
}

parser = argparse.ArgumentParser(description="Deploy Rent Receipt Application")
parser.add_argument(
    "--clean",
    action="store_true",
    help="Completely remove existing Docker containers/images and deploy fresh."
)
args = parser.parse_args()


print("Building frontend applications...")

for rel_dir in FRONTEND_DIRS:
    app_dir = os.path.join(LOCAL_DIR, *rel_dir.split("/"))
    if os.path.exists(app_dir):
        print(f"Building {app_dir}...")
        result = subprocess.run("npm run build", cwd=app_dir, shell=True)
        if result.returncode != 0:
            print(f"\nERROR: Build failed for {app_dir}")
            sys.exit(1)

if os.path.exists(ZIP_FILE):
    os.remove(ZIP_FILE)

print(f"\nZipping {LOCAL_DIR} -> {ZIP_FILE}")

with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(LOCAL_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        if any(part in EXCLUDE_DIRS for part in root.replace("\\", "/").split("/")):
            continue

        for file in files:
            if file.endswith(".zip"):
                continue

            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, LOCAL_DIR)
            posix_path = relative_path.replace("\\", "/")
            zipf.write(local_path, arcname=posix_path)

print("ZIP created successfully.")

print(f"Connecting to {USER}@{HOST}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

print("Uploading update package...")

def print_progress(transferred, total):
    if total > 0:
        percent = (transferred / total) * 100
        sys.stdout.write(f"\rUploading: {percent:.1f}% ({transferred}/{total} bytes)")
        sys.stdout.flush()

sftp = ssh.open_sftp()
sftp.put(ZIP_FILE, REMOTE_ZIP, callback=print_progress)
sftp.close()

print("\nUpload completed.")

commands = []

# ----------------------------------------------------
# CLEAN DEPLOY
# ----------------------------------------------------
if args.clean:
    print("\n========================================")
    print(" CLEAN DEPLOYMENT ENABLED")
    print("========================================\n")

    commands.extend([
        # Stop everything and remove containers/images/volumes
        f"cd {REMOTE_DIR} && docker compose down --rmi all -v --remove-orphans || true",

        # Remove project completely
        f"echo '{PASSWORD}' | sudo -S rm -rf {REMOTE_DIR}",

        # Fresh directory
        f"mkdir -p {REMOTE_DIR}",

        # Extract project
        f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",

        # Remove uploaded archive
        f"rm -f {REMOTE_ZIP}",

        # Recreate .dockerignore
        f"""cd {REMOTE_DIR} && cat > .dockerignore <<'EOF'
storage/
__pycache__/
.git/
venv/
.venv/
node_modules/
frontend/admin-app/node_modules/
frontend/tenant-app/node_modules/
EOF""",

        # Remove Docker build cache
        "docker builder prune -af",

        # Build from scratch
        f"cd {REMOTE_DIR} && docker compose build --no-cache",

        # Start application
        f"cd {REMOTE_DIR} && docker compose up -d --force-recreate",
    ])

# ----------------------------------------------------
# NORMAL DEPLOY
# ----------------------------------------------------
else:
    print("\n========================================")
    print(" NORMAL DEPLOYMENT")
    print("========================================\n")

    commands.extend([
        # Ensure project directory exists
        f"mkdir -p {REMOTE_DIR}",

        # Overwrite only changed files
        f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",

        # Remove uploaded archive
        f"rm -f {REMOTE_ZIP}",

        # Refresh .dockerignore
        f"""cd {REMOTE_DIR} && cat > .dockerignore <<'EOF'
storage/
__pycache__/
.git/
venv/
.venv/
node_modules/
frontend/admin-app/node_modules/
frontend/tenant-app/node_modules/
EOF""",

        # Rebuild images with latest code
        f"cd {REMOTE_DIR} && docker compose build",

        # Recreate only changed containers
        f"cd {REMOTE_DIR} && docker compose up -d",
    ])

for cmd in commands:
    print(f"\nExecuting:\n{cmd}\n")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

    while True:
        data = stdout.channel.recv(4096)
        if not data:
            break
        sys.stdout.buffer.write(data)
        sys.stdout.flush()

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"\nERROR: Command failed (Exit Code {exit_status})")
        ssh.close()
        sys.exit(exit_status)

ssh.close()

print("\n========================================")
print("Deployment completed successfully.")
print("========================================")