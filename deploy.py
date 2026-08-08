import os
import sys
import errno
import socket
import traceback
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
    "sshLocal": {
        "host": "192.168.1.50",
        "port": 22,
        "user": "vega",
        "password": "1010",
        "label": "LAN (same Wi-Fi as the server)",
    },
    "sshPublic": {
        "host": "100.107.83.28",
        "port": 22009,
        "user": "vega",
        "password": "1010",
        "label": "Tailscale (public IP 100.107.83.28)",
    },
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


# ── Exit codes ────────────────────────────────────────────────────────────────

EXIT_BUILD = 1          # frontend build or update.zip creation failed
EXIT_CONNECTIVITY = 2   # server unreachable (timeout / no route / refused)
EXIT_AUTH = 3           # SSH login / handshake failed
EXIT_UPLOAD = 4         # SFTP upload failed mid-transfer
EXIT_REMOTE = 5         # a deploy command failed on the server (or locally)
EXIT_UNEXPECTED = 6     # anything unclassified


# ── Args ─────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Deploy Rent Receipt Application (development or production).",
    epilog="Examples:\n"
           "  python deploy.py --dev --sshPublic        # dev stack via SSH to public IP\n"
           "  python deploy.py --prod --sshPublic       # blue-green production deploy\n"
           "  python deploy.py --release                # release branch deploy (self-pull, runs here)\n"
           "  python deploy.py --main                   # main branch deploy (self-pull, runs here)\n"
           "  python deploy.py --dev --self-test        # check SSH connectivity to the target only\n"
           "\n"
           "Exit codes: 1 build/zip, 2 connectivity, 3 auth, 4 upload,\n"
           "            5 remote command failed, 6 unexpected error.",
)
group = parser.add_mutually_exclusive_group()
group.add_argument("--local", action="store_true", help="Deploy locally (restart Docker on this machine).")
group.add_argument("--sshLocal", action="store_true", help="Deploy via SSH to LAN (192.168.1.50).")
group.add_argument("--sshPublic", action="store_true", help="Deploy via SSH to public IP over Tailscale (100.107.83.28:22009).")

env_group = parser.add_mutually_exclusive_group()
env_group.add_argument("--dev", action="store_true", help="Deploy development environment (compose.dev.yml + .env.development, ngrok). Default when no env flag is given.")
env_group.add_argument("--prod", action="store_true", help="Deploy production environment (blue-green zero-downtime via deploy/deploy-release.sh).")

gh_group = parser.add_mutually_exclusive_group()
gh_group.add_argument("--main", action="store_true", help="Deploy the main (development) branch. Defaults to running here (server self-pull); combine with --sshLocal/--sshPublic to push from a machine.")
gh_group.add_argument("--release", action="store_true", help="Deploy the release (production) branch. Defaults to running here (server self-pull); combine with --sshLocal/--sshPublic to push from a machine.")

parser.add_argument("--clean", action="store_true", help="Full rebuild: remove containers, images, volumes, and rebuild from scratch. NOT supported with --prod/--release.")
parser.add_argument("--no-build", action="store_true", help="Skip frontend npm builds (useful for backend-only changes).")
parser.add_argument("--debug", action="store_true", help="Print full Python tracebacks when something fails.")
parser.add_argument("--self-test", action="store_true", help="Only check connectivity to the deploy target, then exit (no build, no zip, no deploy).")
args = parser.parse_args()

# Environment: --prod or --release wins, otherwise development (safe default).
ENV_PROD = "prod"
ENV_DEV = "dev"
env = ENV_PROD if (args.prod or args.release) else ENV_DEV
github_mode = args.main or args.release
REMOTE_DIR = REMOTE_DIR_PROD if env == ENV_PROD else REMOTE_DIR_DEV

if env == ENV_PROD and args.clean:
    parser.error("--clean is not supported for --prod/--release: it would delete the server repo and wipe storage/release (SQLite). Use the rollback path in deploy/deploy-release.sh instead.")

# Transport. --main/--release (branch self-pull) default to running locally on
# the server; explicit SSH flags push the code from this machine instead.
if github_mode:
    if not (args.local or args.sshLocal or args.sshPublic):
        args.local = True
elif not args.local and not args.sshLocal and not args.sshPublic:
    args.sshLocal = True  # backward compatibility

target_name = "local" if args.local else ("sshPublic" if args.sshPublic else "sshLocal")

build_enabled = (env == ENV_PROD) and not args.no_build


def get_password():
    return os.environ.get("DEPLOY_PASSWORD") or TARGETS[target_name]["password"]


# ── Friendly error helpers ────────────────────────────────────────────────────

def friendly_fail(summary, hints=None, exit_code=EXIT_UNEXPECTED):
    """Print a clear, actionable ERROR block and exit."""
    print()
    print("=" * 60)
    print("  ERROR")
    print("=" * 60)
    print(f"  {summary}")
    if hints:
        print()
        print("  How to fix:")
        for hint in hints:
            print(f"    - {hint}")
    print("=" * 60)
    sys.exit(exit_code)


def target_hints(target_name):
    """Return the 'how to fix' hints specific to a deploy target."""
    if target_name == "sshPublic":
        return [
            "Tailscale must be running AND logged in on BOTH this machine and the server.",
            "Check each machine with:  tailscale status",
            "If a node is down, bring it up with:  tailscale up   (or reopen the Tailscale app).",
            "Confirm the server's Tailscale IP is still 100.107.83.28 (it changes if re-keyed).",
        ]
    if target_name == "sshLocal":
        return [
            "This machine must be on the same Wi-Fi/LAN as the server (192.168.1.50).",
            "The server's LAN IP may have changed via DHCP — check your router's DHCP client list.",
            "If the IP changed, update TARGETS['sshLocal'] at the top of deploy.py.",
        ]
    return []


def tailscale_local_hint():
    """Best-effort: does this machine look like Tailscale is up? Returns a warning string or None."""
    try:
        out = subprocess.run(
            ["tailscale", "status"], capture_output=True, text=True, timeout=3
        )
        if out.returncode != 0:
            return "Tailscale is installed on this machine but is not running (tailscale status failed)."
        return None
    except FileNotFoundError:
        pass
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["ip", "link", "show", "tailscale0"], capture_output=True, text=True, timeout=3
        )
        if out.returncode == 0:
            return None
    except Exception:
        pass
    return "Tailscale does not appear to be installed or running on this machine (no 'tailscale0' interface / no 'tailscale' command)."


def classify_connect_error(host, port, exc, target_name, hints=None):
    """Map a connection/SSH exception to (summary, hints, exit_code)."""
    target = TARGETS.get(target_name, {})
    user = target.get("user", "?")
    label = target.get("label", target_name)
    base = hints if hints is not None else target_hints(target_name)

    pko = paramiko
    if pko is not None and isinstance(exc, pko.AuthenticationException):
        return (
            f"SSH login failed for {user}@{host}: wrong username or password.",
            [
                "Check the password for this target.",
                "Set it explicitly with:  DEPLOY_PASSWORD=... python deploy.py ...",
                f"Or update TARGETS['{target_name}'] at the top of deploy.py.",
            ],
            EXIT_AUTH,
        )
    if pko is not None and isinstance(exc, pko.SSHException):
        return (
            f"SSH handshake with {host}:{port} failed.",
            [
                "The server may not accept password login (key-only auth may be configured).",
                "The server's SSH host key may have changed — remove the stale entry from your SSH known_hosts.",
            ],
            EXIT_CONNECTIVITY,
        )
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return (
            f"Could not reach server {user}@{host}:{port} — the connection timed out.",
            [f"The target is: {label}."] + base,
            EXIT_CONNECTIVITY,
        )
    if isinstance(exc, ConnectionRefusedError):
        return (
            f"Server {host} is reachable, but nothing is listening on SSH port {port}.",
            [
                "The SSH service may be stopped, or the port is blocked by a firewall.",
                "On the server (or via another route) check:  systemctl status sshd  /  ss -ltn | grep :22009",
            ]
            + base,
            EXIT_CONNECTIVITY,
        )
    if isinstance(exc, socket.gaierror):
        return (
            f"Could not resolve the host '{host}'.",
            [f"Check the hostname/IP in TARGETS['{target_name}'] at the top of deploy.py."],
            EXIT_CONNECTIVITY,
        )
    if isinstance(exc, OSError) and exc.errno in (
        errno.EHOSTUNREACH, errno.ENETUNREACH, errno.ENETDOWN, errno.EADDRNOTAVAIL,
    ):
        return (
            f"No route to server {host} ({type(exc).__name__}).",
            [f"The target is: {label}, but this machine cannot reach it."] + base,
            EXIT_CONNECTIVITY,
        )
    return (
        f"Failed to connect to {host}:{port} ({type(exc).__name__}: {exc}).",
        base,
        EXIT_CONNECTIVITY,
    )


def preflight_tcp(host, port, target_name, timeout=5):
    """Quick TCP check so the user gets a clear answer in seconds, not 30."""
    print(f"Checking connectivity to {host}:{port}...")
    try:
        with socket.create_connection((host, port), timeout=timeout):
            print("  Connectivity OK.")
            return True
    except Exception as exc:
        hints = target_hints(target_name)
        if target_name == "sshPublic":
            local_hint = tailscale_local_hint()
            if local_hint:
                hints = [local_hint] + hints
        summary, hints, code = classify_connect_error(host, port, exc, target_name, hints)
        if args.debug:
            traceback.print_exc()
        friendly_fail(summary, hints, code)


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
                if args.debug:
                    traceback.print_exc()
                friendly_fail(
                    f"Frontend build failed for {rel_dir}.",
                    [
                        "Fix the build error shown above, then re-run.",
                        "For backend-only changes you can skip builds with:  --no-build",
                    ],
                    EXIT_BUILD,
                )
        else:
            print(f"  Skipping {rel_dir} (not found)")


def create_zip():
    if os.path.exists(ZIP_FILE):
        try:
            os.remove(ZIP_FILE)
        except OSError as exc:
            if args.debug:
                traceback.print_exc()
            friendly_fail(
                f"Could not remove the stale {ZIP_FILE}.",
                [f"Delete it manually and re-run. (underlying error: {exc})"],
                EXIT_BUILD,
            )
    print(f"\nZipping {LOCAL_DIR} -> {ZIP_FILE}")
    try:
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
    except OSError as exc:
        if args.debug:
            traceback.print_exc()
        friendly_fail(
            "Could not create the update package (update.zip).",
            [
                "Check there is enough free disk space.",
                "Check write permissions in this directory.",
                f"(underlying error: {exc})",
            ],
            EXIT_BUILD,
        )
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
        cmds.append(f"cd {REMOTE_DIR} && bash deploy/deploy-release.sh")
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
    try:
        _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=600)
        while True:
            data = stdout.channel.recv(4096)
            if not data:
                break
            sys.stdout.buffer.write(data)
            sys.stdout.flush()
        exit_status = stdout.channel.recv_exit_status()
    except Exception as exc:
        if args.debug:
            traceback.print_exc()
        friendly_fail(
            "The SSH connection was lost while running a deploy command on the server.",
            [
                "The server may have rebooted or restarted Docker during the deploy.",
                "Check the server state with:  docker ps   (and the deploy logs).",
                "Re-run the deploy — the steps are safe to repeat.",
                f"(underlying error: {exc})",
            ],
            EXIT_REMOTE,
        )
    if exit_status != 0:
        err = stderr.read().decode(errors="replace").strip()
        print(f"\nERROR: Command failed (Exit Code {exit_status})")
        if err:
            print(f"  {err[:500]}")
        return False
    return True


def run_local(cmd):
    print(f"\n  >>> {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
    try:
        result = subprocess.run(cmd, shell=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        if args.debug:
            traceback.print_exc()
        friendly_fail(
            f"A local command timed out after 600s: {cmd[:100]}",
            [
                "The command may be stuck (e.g., waiting on Docker).",
                "Check running containers with:  docker ps",
                f"(underlying error: {exc})",
            ],
            EXIT_REMOTE,
        )
    if result.returncode != 0:
        print(f"\nERROR: Command failed (Exit Code {result.returncode})")
        return False
    return True


def connect_ssh(host, port, user, password):
    if paramiko is None:
        friendly_fail(
            "paramiko (the SSH library) is not installed.",
            ["Install it with:  pip install paramiko"],
            EXIT_BUILD,
        )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {user}@{host}:{port}...")
    try:
        ssh.connect(host, port=port, username=user, password=password, timeout=30)
    except Exception as exc:
        if args.debug:
            traceback.print_exc()
        summary, hints, code = classify_connect_error(host, port, exc, target_name)
        friendly_fail(summary, hints, code)
    print("Connected.")
    return ssh


def upload_zip(ssh):
    print("Uploading update package...")
    try:
        sftp = ssh.open_sftp()

        def progress(transferred, total):
            if total > 0:
                pct = transferred * 100 // total
                sys.stdout.write(f"\r  Uploading: {pct}% ({transferred:,}/{total:,} bytes)")
                sys.stdout.flush()

        sftp.put(ZIP_FILE, REMOTE_ZIP, callback=progress)
        sftp.close()
        print("\nUpload completed.")
    except Exception as exc:
        if args.debug:
            traceback.print_exc()
        friendly_fail(
            "Uploading the update package to the server failed.",
            [
                "The SSH connection was dropped mid-upload — the server may be restarting.",
                "Check free disk space on the server:  df -h /home/vega",
                "Make sure this machine stays connected, then re-run the deploy.",
                f"(underlying error: {exc})",
            ],
            EXIT_UPLOAD,
        )


def run_self_test():
    cfg = TARGETS[target_name]
    print("=" * 60)
    print(f" SELF-TEST: {target_name.upper()} -> {cfg['user']}@{cfg['host']}:{cfg['port']}")
    print(f" MODE: {'PROD' if env == ENV_PROD else 'DEV'}   REMOTE_DIR: {REMOTE_DIR}")
    print("=" * 60)
    preflight_tcp(cfg["host"], cfg["port"], target_name)
    print()
    print("Connectivity OK — the target is reachable.")
    print("Next step: run the deploy, e.g.  python deploy.py --dev --sshPublic")
    sys.exit(0)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print(f" MODE: {'PROD' if env == ENV_PROD else 'DEV'}")
    print(f" TARGET: {target_name.upper()}{' (GitHub)' if github_mode else ''}")
    print(f" CLEAN: {'YES' if args.clean else 'no'}")
    print(f" BUILD: {'skip' if not build_enabled else 'yes'}")
    print("=" * 50)

    if args.self_test:
        run_self_test()

    # SSH deploys: verify the server is reachable before doing any real work,
    # so a network problem is reported in seconds instead of after builds/zip.
    if not args.local:
        cfg = TARGETS[target_name]
        preflight_tcp(cfg["host"], cfg["port"], target_name)

    build_frontends()

    # ── LOCAL deploy (self-pull on the server) ───────────────────────────────
    if args.local:
        print("\n========================================")
        print(f" LOCAL DEPLOYMENT ({'PROD' if env == ENV_PROD else 'DEV'})")
        print("========================================")

        if env == ENV_PROD:
            commands = [f"cd {LOCAL_DIR} && bash deploy/deploy-release.sh"]
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
                print("\nDeploy aborted because a command failed (see above).")
                sys.exit(EXIT_REMOTE)

        print("\n========================================")
        print("Deployment completed successfully.")
        print("========================================")
        sys.exit(0)

    # ── SSH deploy (push from this machine) ──────────────────────────────────
    create_zip()

    cfg = TARGETS[target_name]
    ssh = connect_ssh(cfg["host"], cfg["port"], cfg["user"], get_password())
    try:
        upload_zip(ssh)

        for cmd in get_deploy_commands():
            if not run_remote(ssh, cmd):
                print("\nDeploy aborted because a command failed on the server (see above).")
                sys.exit(EXIT_REMOTE)
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    print("\n========================================")
    print("Deployment completed successfully.")
    print("========================================")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(130)
    except Exception:
        if getattr(args, "debug", False) or os.environ.get("DEPLOY_DEBUG") == "1":
            raise
        friendly_fail(
            "Unexpected error while running the deploy.",
            [
                "Re-run with  --debug  to see the full error trace.",
                "If the problem persists, check deploy/README.md.",
            ],
            EXIT_UNEXPECTED,
        )
