#!/usr/bin/env python3
"""
Deploy Rent Backend to Ubuntu server via SSH.

Usage:
    python deploy/deploy_backend.py                          # default LAN target
    python deploy/deploy_backend.py --host 192.168.1.50
    python deploy/deploy_backend.py --host 100.107.83.28 --port 22009
    python deploy/deploy_backend.py --clean                  # full rebuild
    python deploy/deploy_backend.py --dry-run                # show commands only
"""

import os
import sys
import argparse
import subprocess

try:
    import paramiko
except ImportError:
    paramiko = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_DIR = "/home/vega/rent/backend"

# Directories and files to upload (relative to repo root)
UPLOAD_DIRS = ["app", "backend"]
UPLOAD_FILES = ["requirements.txt"]


def parse_args():
    parser = argparse.ArgumentParser(description="Deploy Rent Backend")
    parser.add_argument("--host", default=os.getenv("DEPLOY_HOST", "192.168.1.50"))
    parser.add_argument("--port", type=int, default=int(os.getenv("DEPLOY_PORT", "22")))
    parser.add_argument("--user", default=os.getenv("DEPLOY_USER", "vega"))
    parser.add_argument("--key", default=os.getenv("DEPLOY_KEY", os.path.expanduser("~/.ssh/id_rsa")))
    parser.add_argument("--clean", action="store_true",
                        help="Full rebuild: docker compose down, rebuild --no-cache. Preserves storage.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show commands without executing")
    return parser.parse_args()


def run_local(cmd, dry_run=False):
    print(f"  >>> {cmd}")
    if dry_run:
        return True
    result = subprocess.run(cmd, shell=True, timeout=600)
    return result.returncode == 0


def run_remote(ssh, cmd, dry_run=False):
    print(f"  >>> {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    if dry_run:
        return True
    _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=600)
    while True:
        data = stdout.channel.recv(4096)
        if not data:
            break
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode(errors="replace").strip()
        print(f"\nERROR: Command failed (Exit Code {exit_status})")
        if err:
            print(f"  {err[:500]}")
        return False
    return True


def connect_ssh(host, port, user, key_path):
    if paramiko is None:
        print("ERROR: paramiko is not installed. Run: pip install paramiko")
        sys.exit(1)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = os.path.expanduser(key_path)
    if os.path.isfile(key_path):
        key = paramiko.Ed25519Key.from_private_key_file(key_path)
        print(f"Connecting to {user}@{host}:{port} (key: {key_path})...")
        ssh.connect(host, port=port, username=user, pkey=key, timeout=30)
    else:
        print(f"WARNING: Key file {key_path} not found. Trying agent/password fallback...")
        ssh.connect(host, port=port, username=user, timeout=30)
    print("Connected.")
    return ssh


def upload_files(ssh, files):
    """Upload specific files and directories to the remote server."""
    sftp = ssh.open_sftp()

    for rel_dir in UPLOAD_DIRS:
        local_dir = os.path.join(BASE_DIR, rel_dir)
        if not os.path.isdir(local_dir):
            print(f"  WARNING: {rel_dir} not found, skipping")
            continue
        _upload_dir(sftp, local_dir, rel_dir)

    for rel_file in UPLOAD_FILES:
        local_file = os.path.join(BASE_DIR, rel_file)
        if os.path.isfile(local_file):
            remote_file = f"{REMOTE_DIR}/{rel_file}"
            print(f"  Uploading {rel_file}")
            sftp.put(local_file, remote_file)

    sftp.close()


def _upload_dir(sftp, local_dir, rel_path):
    """Recursively upload a directory via SFTP."""
    for item in os.listdir(local_dir):
        if item in ("__pycache__", ".git", "node_modules", "venv", ".venv", "storage"):
            continue
        local_path = os.path.join(local_dir, item)
        remote_path = f"{REMOTE_DIR}/{rel_path}/{item}"
        if os.path.isfile(local_path):
            print(f"  Uploading {rel_path}/{item}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            try:
                sftp.mkdir(remote_path)
            except OSError:
                pass  # directory exists
            _upload_dir(sftp, local_path, f"{rel_path}/{item}")


def get_deploy_commands(args):
    if args.clean:
        return [
            f"cd {REMOTE_DIR} && docker compose down --remove-orphans || true",
            f"cd {REMOTE_DIR} && docker compose build --no-cache",
            f"cd {REMOTE_DIR} && docker compose up -d --force-recreate",
        ]
    else:
        return [
            f"cd {REMOTE_DIR} && docker compose build",
            f"cd {REMOTE_DIR} && docker compose up -d",
        ]


def main():
    args = parse_args()

    print("=" * 60)
    print(" RENT BACKEND DEPLOYMENT")
    print("=" * 60)
    print(f"  Target:  {args.user}@{args.host}:{args.port}")
    print(f"  Clean:   {'YES' if args.clean else 'no'}")
    print(f"  Dry run: {'YES' if args.dry_run else 'no'}")
    print("=" * 60)

    if not args.dry_run:
        ssh = connect_ssh(args.host, args.port, args.user, args.key)

        print("\n--- Uploading files ---")
        upload_files(ssh, UPLOAD_DIRS + UPLOAD_FILES)

        print("\n--- Deploying ---")
        commands = get_deploy_commands(args)
        for cmd in commands:
            if not run_remote(ssh, cmd, args.dry_run):
                ssh.close()
                print("\nDEPLOYMENT FAILED")
                sys.exit(1)

        ssh.close()
    else:
        print("\n--- Commands that would run ---")
        for cmd in get_deploy_commands(args):
            run_local(cmd, dry_run=True)

    print("\n" + "=" * 60)
    print(" Deployment completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
