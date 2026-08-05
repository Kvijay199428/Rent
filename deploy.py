import os
import sys
import zipfile
import argparse
import subprocess

try:
    import paramiko
except ImportError:
    paramiko = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR = BASE_DIR
ZIP_FILE = os.path.join(BASE_DIR, "update.zip")
REMOTE_ZIP = "/home/vega/update.zip"
REMOTE_DIR_DEV = "/home/vega/rent-app-20081"
REMOTE_DIR_PROD = "/home/vega/rent-app"

FRONTEND_DIRS = [
    "frontend/admin-app",
    "frontend/tenant-app",
    "frontend/landlord-app",
    "frontend/landing-app",
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

TARGETS = {
    "sshLocal": {"host": "192.168.1.50", "port": 22, "user": "vega", "password": "1010"},
    "sshPublic": {"host": "100.107.83.28", "port": 22009, "user": "vega", "password": "1010"},
}

DOCKERIGNORE = """\
storage/
__pycache__/
.git/
venv/
.venv/
node_modules/
frontend/admin-app/node_modules/
frontend/tenant-app/node_modules/
frontend/landlord-app/node_modules/
"""


# ── Args ─────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Deploy Rent Receipt Application (development or production).",
    epilog="Examples:\n"
           "  python deploy.py --dev --sshPublic        # dev stack via SSH to public IP\n"
           "  python deploy.py --prod --sshPublic       # blue-green production deploy\n"
           "  python deploy.py --release                # GitHub: production deploy\n"
           "  python deploy.py --main                   # GitHub: dev deploy",
)
group = parser.add_mutually_exclusive_group()
group.add_argument("--local", action="store_true", help="Deploy locally (restart Docker on this machine).")
group.add_argument("--sshLocal", action="store_true", help="Deploy via SSH to LAN (192.168.1.50).")
group.add_argument("--sshPublic", action="store_true", help="Deploy via SSH to public IP (100.107.83.28:22009).")

env_group = parser.add_mutually_exclusive_group()
env_group.add_argument("--dev", action="store_true", help="Deploy development environment (compose.dev.yml + .env.development, ngrok). Default when no env flag is given.")
env_group.add_argument("--prod", action="store_true", help="Deploy production environment (blue-green zero-downtime via deploy/deploy-release.sh).")

gh_group = parser.add_mutually_exclusive_group()
gh_group.add_argument("--main", action="store_true", help="GitHub: deploy development environment to the server (same as --dev, targets sshPublic).")
gh_group.add_argument("--release", action="store_true", help="GitHub: deploy production environment to the server (same as --prod, targets sshPublic).")

parser.add_argument("--clean", action="store_true", help="Full rebuild: remove containers, images, volumes, and rebuild from scratch. NOT supported with --prod/--release.")
parser.add_argument("--no-build", action="store_true", help="Skip frontend npm builds (useful for backend-only changes).")
args = parser.parse_args()

# Environment: --prod or --release wins, otherwise development (safe default).
ENV_PROD = "prod"
ENV_DEV = "dev"
env = ENV_PROD if (args.prod or args.release) else ENV_DEV
github_mode = args.main or args.release
REMOTE_DIR = REMOTE_DIR_PROD if env == ENV_PROD else REMOTE_DIR_DEV

if env == ENV_PROD and args.clean:
    parser.error("--clean is not supported for --prod/--release: it would delete the server repo and wipe storage/release (SQLite). Use the rollback path in deploy/deploy-release.sh instead.")

if github_mode and (args.local or args.sshLocal or args.sshPublic):
    parser.error("--main/--release (GitHub modes) cannot be combined with --local/--sshLocal/--sshPublic.")

# Default to sshLocal for backward compatibility
if not args.local and not args.sshLocal and not args.sshPublic:
    args.sshLocal = True

target_name = "local" if args.local else ("sshPublic" if args.sshPublic else "sshLocal")
if github_mode:
    target_name = "sshPublic"

build_enabled = (env == ENV_PROD) and not args.no_build


def get_password():
    return os.environ.get("DEPLOY_PASSWORD") or TARGETS[target_name]["password"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_node_version():
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip().lstrip("v")
        parts = version.split(".")
        major = int(parts[0])
        if major < 22:
            print(f"WARNING: Node v{version} detected. Node >= 22.22.0 recommended.")
            print("  Run: nvm use")
    except Exception:
        print("WARNING: Could not detect Node version.")


def build_frontends():
    if env == ENV_DEV:
        print("Skipping frontend builds (development env runs Vite live on the server).")
        return
    if args.no_build:
        print("Skipping frontend builds (--no-build).")
        return
    check_node_version()
    print("Building frontend applications...")
    for rel_dir in FRONTEND_DIRS:
        app_dir = os.path.join(LOCAL_DIR, *rel_dir.split("/"))
        if os.path.exists(app_dir):
            print(f"  Building {rel_dir}...")
            result = subprocess.run("npm install && npm run build", cwd=app_dir, shell=True)
            if result.returncode != 0:
                print(f"\nERROR: Build failed for {rel_dir}")
                sys.exit(1)
        else:
            print(f"  Skipping {rel_dir} (not found)")


def create_zip():
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
                arcname = os.path.relpath(local_path, LOCAL_DIR).replace("\\", "/")
                zipf.write(local_path, arcname=arcname)
    size = os.path.getsize(ZIP_FILE)
    print(f"ZIP created: {size:,} bytes")


def extract_zip_cmds():
    return [
        f"mkdir -p {REMOTE_DIR}",
        f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",
        f"rm -f {REMOTE_ZIP}",
        f"cat > {REMOTE_DIR}/.dockerignore <<'DOCKEOF'\n{DOCKERIGNORE}DOCKEOF",
    ]


def get_deploy_commands():
    if env == ENV_PROD:
        cmds = extract_zip_cmds()
        deploy_args = " --no-build" if args.no_build else ""
        cmds.append(f"cd {REMOTE_DIR} && bash deploy/deploy-release.sh{deploy_args}")
        return cmds

    compose = "compose.dev.yml"
    env_file = ".env.development"
    if args.clean:
        cmds = [
            f"cd {REMOTE_DIR} && docker compose --env-file {env_file} -f {compose} down --rmi all -v --remove-orphans || true",
            f"echo '{get_password()}' | sudo -S rm -rf {REMOTE_DIR}",
            f"mkdir -p {REMOTE_DIR}",
            f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",
            f"rm -f {REMOTE_ZIP}",
            f"cat > {REMOTE_DIR}/.dockerignore <<'DOCKEOF'\n{DOCKERIGNORE}DOCKEOF",
            "docker builder prune -af",
            f"cd {REMOTE_DIR} && docker compose --env-file {env_file} -f {compose} build --no-cache",
            f"cd {REMOTE_DIR} && docker compose --env-file {env_file} -f {compose} up -d --force-recreate",
        ]
    else:
        cmds = extract_zip_cmds()
        cmds.extend([
            f"cd {REMOTE_DIR} && docker compose --env-file {env_file} -f {compose} build",
            f"cd {REMOTE_DIR} && docker compose --env-file {env_file} -f {compose} up -d",
        ])
    return cmds


def run_remote(ssh, cmd):
    print(f"\n  >>> {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
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


def run_local(cmd):
    print(f"\n  >>> {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
    result = subprocess.run(cmd, shell=True, timeout=600)
    if result.returncode != 0:
        print(f"\nERROR: Command failed (Exit Code {result.returncode})")
        return False
    return True


def connect_ssh(host, port, user, password):
    if paramiko is None:
        print("ERROR: paramiko is not installed. Run: pip install paramiko")
        sys.exit(1)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {user}@{host}:{port}...")
    ssh.connect(host, port=port, username=user, password=password, timeout=30)
    print("Connected.")
    return ssh


def upload_zip(ssh):
    print("Uploading update package...")
    sftp = ssh.open_sftp()

    def progress(transferred, total):
        if total > 0:
            pct = transferred * 100 // total
            sys.stdout.write(f"\r  Uploading: {pct}% ({transferred:,}/{total:,} bytes)")
            sys.stdout.flush()

    sftp.put(ZIP_FILE, REMOTE_ZIP, callback=progress)
    sftp.close()
    print("\nUpload completed.")


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * 50)
print(f" MODE: {'PROD' if env == ENV_PROD else 'DEV'}")
print(f" TARGET: {target_name.upper()}{' (GitHub)' if github_mode else ''}")
print(f" CLEAN: {'YES' if args.clean else 'no'}")
print(f" BUILD: {'skip' if not build_enabled else 'yes'}")
print("=" * 50)

build_frontends()
create_zip()

# ── LOCAL deploy ──────────────────────────────────────────────────────────────
if args.local:
    print("\n========================================")
    print(f" LOCAL DEPLOYMENT ({'PROD' if env == ENV_PROD else 'DEV'})")
    print("========================================")

    if env == ENV_PROD:
        deploy_args = " --no-build" if args.no_build else ""
        commands = [f"cd {LOCAL_DIR} && bash deploy/deploy-release.sh{deploy_args}"]
    else:
        compose = "compose.dev.yml"
        env_file = ".env.development"
        commands = []
        if args.clean:
            commands.extend([
                f"cd {LOCAL_DIR} && docker compose --env-file {env_file} -f {compose} down --rmi all -v --remove-orphans || true",
                f"cd {LOCAL_DIR} && docker compose --env-file {env_file} -f {compose} build --no-cache",
                f"cd {LOCAL_DIR} && docker compose --env-file {env_file} -f {compose} up -d --force-recreate",
            ])
        else:
            commands.extend([
                f"cd {LOCAL_DIR} && docker compose --env-file {env_file} -f {compose} build",
                f"cd {LOCAL_DIR} && docker compose --env-file {env_file} -f {compose} up -d",
            ])

    for cmd in commands:
        if not run_local(cmd):
            sys.exit(1)

    print("\n========================================")
    print("Deployment completed successfully.")
    print("========================================")
    sys.exit(0)

# ── SSH deploy ────────────────────────────────────────────────────────────────
cfg = TARGETS[target_name]
ssh = connect_ssh(cfg["host"], cfg["port"], cfg["user"], get_password())

upload_zip(ssh)

commands = get_deploy_commands()

for cmd in commands:
    if not run_remote(ssh, cmd):
        ssh.close()
        sys.exit(1)

ssh.close()

print("\n========================================")
print("Deployment completed successfully.")
print("========================================")
