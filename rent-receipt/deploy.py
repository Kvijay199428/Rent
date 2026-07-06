# File: deploy.py

import os
import sys
import zipfile
import argparse
import paramiko

# ============================================================
# Configuration
# ============================================================

HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"

LOCAL_DIR = r"d:\VEGA\RENT\rent-receipt"
ZIP_FILE = r"d:\VEGA\RENT\update.zip"

REMOTE_ZIP = "/home/vega/update.zip"
REMOTE_DIR = "/home/vega/rent-receipt"

# ============================================================
# Parse Arguments
# ============================================================

parser = argparse.ArgumentParser(description="Deploy Rent Receipt Application")
parser.add_argument(
    "--clean",
    action="store_true",
    help="Completely remove existing Docker containers/images and deploy fresh."
)

args = parser.parse_args()

# ============================================================
# Create ZIP
# ============================================================

print(f"Zipping {LOCAL_DIR} -> {ZIP_FILE}")

with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(LOCAL_DIR):

        # Skip unwanted folders
        if any(
            exclude in root
            for exclude in [
                "__pycache__",
                ".git",
                "storage",
                "venv",
                ".venv",
            ]
        ):
            continue

        for file in files:

            if file.endswith(".zip"):
                continue

            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, LOCAL_DIR)
            posix_path = relative_path.replace("\\", "/")

            # Normalize web asset paths for Linux
            if (
                posix_path.lower().startswith("app/static/")
                or posix_path.lower().startswith("app/templates/")
            ):
                parts = posix_path.split("/")

                if len(parts) > 1:
                    dirs_lower = [p.lower() for p in parts[:-1]]
                    filename = parts[-1]

                    if filename.lower().endswith(
                        (
                            ".css",
                            ".js",
                            ".html",
                        )
                    ):
                        filename = filename.lower()

                    posix_path = "/".join(dirs_lower + [filename])

            zipf.write(local_path, arcname=posix_path)

print("ZIP created successfully.")

# ============================================================
# SSH Connect
# ============================================================

print(f"Connecting to {USER}@{HOST}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect(
    HOST,
    username=USER,
    password=PASSWORD,
)

# ============================================================
# Upload ZIP
# ============================================================

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

# ============================================================
# Deployment Commands
# ============================================================

commands = [

    # Remove old misplaced folders
    f"cd {REMOTE_DIR} && rm -rf static templates Static Templates app",

    # Extract latest files
    f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",

    # Create dockerignore
    f"cd {REMOTE_DIR} && echo 'storage/' > .dockerignore",
    f"cd {REMOTE_DIR} && echo '__pycache__/' >> .dockerignore",
    f"cd {REMOTE_DIR} && echo '.git/' >> .dockerignore",
    f"cd {REMOTE_DIR} && echo 'venv/' >> .dockerignore",
]

# ============================================================
# Docker Deployment
# ============================================================

if args.clean:

    print("\n========================================")
    print(" CLEAN DEPLOYMENT ENABLED")
    print("========================================\n")

    commands.extend([

        # Stop containers
        f"cd {REMOTE_DIR} && docker compose down --remove-orphans",

        # Remove project images
        f"cd {REMOTE_DIR} && docker compose down --rmi all --remove-orphans",

        # Remove anonymous volumes
        f"cd {REMOTE_DIR} && docker compose down -v --remove-orphans",

        # Completely wipe all persistent data (database, configs, uploads) using sudo to avoid permission denied
        f"cd {REMOTE_DIR} && echo '{PASSWORD}' | sudo -S rm -rf storage/",

        # Remove dangling build cache
        "docker builder prune -af",

        # Remove dangling images
        "docker image prune -af",

        # Build from scratch
        f"cd {REMOTE_DIR} && docker compose build --no-cache",

        "docker rm -f rent_app_20081 || true",

        # Start containers
        f"cd {REMOTE_DIR} && docker compose up -d",

    ])

else:

    commands.extend([

        f"cd {REMOTE_DIR} && docker compose down",

        f"cd {REMOTE_DIR} && docker compose build --no-cache",

        "docker rm -f rent_app_20081 || true",

        f"cd {REMOTE_DIR} && docker compose up -d",

    ])

# ============================================================
# Execute Commands
# ============================================================

for cmd in commands:

    print(f"\nExecuting:\n{cmd}\n")

    # Use get_pty=True to merge stderr into stdout and preserve progress bar animations
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

    # Read output byte by byte / chunk by chunk as it arrives
    while True:
        try:
            data = stdout.channel.recv(4096)
            if not data:
                break
            # Write bytes directly to preserve terminal control characters (e.g. \r)
            sys.stdout.buffer.write(data)
            sys.stdout.flush()
        except Exception as e:
            print(f"\nError reading stream: {e}")
            break

    exit_status = stdout.channel.recv_exit_status()

    if exit_status != 0:
        print(f"\nERROR: Command failed (Exit Code {exit_status})")
        ssh.close()
        sys.exit(exit_status)

ssh.close()

print("\n========================================")
print("Deployment completed successfully.")
print("========================================")