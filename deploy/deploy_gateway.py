#!/usr/bin/env python3
"""
Deploy/update nginx gateway configuration.

Uploads changed route files and reloads Nginx without downtime.

Usage:
    python deploy/deploy_gateway.py
    python deploy/deploy_gateway.py --host 192.168.1.50
    python deploy/deploy_gateway.py --dry-run
"""

import os
import sys
import argparse

try:
    import paramiko
except ImportError:
    paramiko = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(BASE_DIR, "gateway")
REMOTE_DIR = "/home/vega/gateway"


def parse_args():
    parser = argparse.ArgumentParser(description="Deploy Rent Gateway")
    parser.add_argument("--host", default=os.getenv("DEPLOY_HOST", "192.168.1.50"))
    parser.add_argument("--port", type=int, default=int(os.getenv("DEPLOY_PORT", "22")))
    parser.add_argument("--user", default=os.getenv("DEPLOY_USER", "vega"))
    parser.add_argument("--key", default=os.getenv("DEPLOY_KEY", os.path.expanduser("~/.ssh/id_rsa")))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run_remote(ssh, cmd, dry_run=False):
    print(f"  >>> {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    if dry_run:
        return True
    _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=60)
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
        print(f"Connecting to {user}@{host}:{port}...")
        ssh.connect(host, port=port, username=user, pkey=key, timeout=30)
    else:
        print(f"WARNING: Key file {key_path} not found. Trying agent/password fallback...")
        ssh.connect(host, port=port, username=user, timeout=30)
    print("Connected.")
    return ssh


def upload_nginx_configs(ssh, dry_run=False):
    """Upload nginx config and route files."""
    sftp = ssh.open_sftp()

    files_to_upload = [
        ("nginx/nginx.conf", "nginx/nginx.conf"),
    ]

    # Upload all route files
    routes_dir = os.path.join(GATEWAY_DIR, "nginx", "routes")
    if os.path.isdir(routes_dir):
        for fname in os.listdir(routes_dir):
            if fname.endswith(".conf"):
                files_to_upload.append(
                    (f"nginx/routes/{fname}", f"nginx/routes/{fname}")
                )

    for local_rel, remote_rel in files_to_upload:
        local_path = os.path.join(GATEWAY_DIR, local_rel)
        remote_path = f"{REMOTE_DIR}/{remote_rel}"
        if os.path.isfile(local_path):
            if not dry_run:
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.mkdir(remote_dir)
                except OSError:
                    pass
                print(f"  Uploading {local_rel}")
                sftp.put(local_path, remote_path)
            else:
                print(f"  Would upload {local_rel}")

    sftp.close()


def main():
    args = parse_args()

    print("=" * 60)
    print(" GATEWAY DEPLOYMENT")
    print("=" * 60)
    print(f"  Target:  {args.user}@{args.host}:{args.port}")
    print(f"  Dry run: {'YES' if args.dry_run else 'no'}")
    print("=" * 60)

    if not args.dry_run:
        ssh = connect_ssh(args.host, args.port, args.user, args.key)

        print("\n--- Uploading nginx configs ---")
        upload_nginx_configs(ssh, args.dry_run)

        print("\n--- Testing nginx configuration ---")
        if not run_remote(ssh, "docker exec vega-nginx-gateway nginx -t"):
            print("\nERROR: Nginx config test failed. NOT reloading.")
            ssh.close()
            sys.exit(1)

        print("\n--- Reloading nginx ---")
        if not run_remote(ssh, "docker exec vega-nginx-gateway nginx -s reload"):
            print("\nERROR: Nginx reload failed.")
            ssh.close()
            sys.exit(1)

        ssh.close()
    else:
        print("\n--- Commands that would run ---")
        print("  Upload nginx configs")
        print("  docker exec vega-nginx-gateway nginx -t")
        print("  docker exec vega-nginx-gateway nginx -s reload")

    print("\n" + "=" * 60)
    print(" Gateway deployment completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
