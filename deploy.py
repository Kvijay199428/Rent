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
DEPLOY_DIR = os.path.join(BASE_DIR, "deploy")
if DEPLOY_DIR not in sys.path:
    sys.path.insert(0, DEPLOY_DIR)

import ports as deploy_ports  # noqa: E402  (single source of truth for canonical ports)
ZIP_FILE = os.path.join(BASE_DIR, "update.zip")
REMOTE_ZIP = "/home/vega/update.zip"
REMOTE_DIR_DEV = "/home/vega/propaura-dev"
REMOTE_DIR_PROD = "/home/vega/propaura-prod"

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
    ".opencode",
    ".env",
}

TARGETS = {
    "sshLocal": {
        "host": "192.168.1.50",
        "port": 22009,
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
           "  python deploy.py --dev --sshPublic --clean   # dev stack, full wipe+rebuild, via SSH to public IP\n"
           "  python deploy.py --dev --sshPublic           # dev stack via SSH to public IP\n"
           "  python deploy.py --prod --sshPublic          # single-slot production deploy\n"
           "  python deploy.py --release                   # release branch deploy (self-pull, runs here)\n"
           "  python deploy.py --main                      # main branch deploy (self-pull, runs here)\n"
           "  python deploy.py --dev --self-test           # check SSH connectivity to the target only\n"
           "\n"
           "Scopes (default --all):\n"
           "  --all         ship the entire repo (default)\n"
           "  --frontend    ship only frontend/\n"
           "  --backend     ship only backend/\n"
"  --storage     ship storage/ data (keys, backups; overwrites server data)\n"
            "  --database    ship database schema + migrations (backend/app/app/db)\n"
           "  e.g. python deploy.py --dev --sshPublic --backend   # only backend fixes\n"
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
env_group.add_argument("--prod", action="store_true", help="Deploy production environment (single backend slot via deploy/deploy-release.sh).")

gh_group = parser.add_mutually_exclusive_group()
gh_group.add_argument("--main", action="store_true", help="Deploy the main (development) branch. Defaults to running here (server self-pull); combine with --sshLocal/--sshPublic to push from a machine.")
gh_group.add_argument("--release", action="store_true", help="Deploy the release (production) branch. Defaults to running here (server self-pull); combine with --sshLocal/--sshPublic to push from a machine.")

scope_group = parser.add_mutually_exclusive_group()
scope_group.add_argument("--all", action="store_true", help="Ship the entire repo (default).")
scope_group.add_argument("--frontend", action="store_true", help="Ship only frontend/ (and root infra files).")
scope_group.add_argument("--backend", action="store_true", help="Ship only backend/ (and root infra files).")
scope_group.add_argument("--storage", action="store_true", help="Ship storage/ data (keys, backups) — overwrites server data with local data. PostgreSQL data lives in named volumes and is NOT shipped.")
scope_group.add_argument("--database", action="store_true", help="Ship database schema + migrations (backend/app/app/db, database/, core/db.py).")

parser.add_argument("--clean", action="store_true", help="Full rebuild: remove containers, images, volumes, and rebuild from scratch. NOT supported with --prod/--release or scoped flags (implies --all).")
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
    parser.error("--clean is not supported for --prod/--release: it would delete the server repo and wipe storage/release and the pgdata_prod PostgreSQL volume. Use the rollback path in deploy/deploy-release.sh instead.")

# Scope: which components are shipped. Default --all.
SCOPES = ("all", "frontend", "backend", "storage", "database")
scope = next((s for s in SCOPES[1:] if getattr(args, s)), "all")

if args.clean and scope != "all":
    parser.error(
        "--clean wipes the server repo and re-extracts the uploaded package, so it "
        "requires the full deploy. Use  --clean --all  (or just --clean), or drop "
        "--clean for a scoped deploy (--frontend/--backend/--storage/--database)."
    )

# Scope -> relative path roots to ship. The exact key order matters: more
# specific (deeper) paths must be tested before their parents.
SCOPE_PATHS = {
    "all": None,  # whole repo (create_zip walks everything, as before)
    "frontend": ["frontend"],
    "backend": ["backend"],
    "storage": ["storage"],
    "database": [
        "backend/app/app/db",
        "backend/app/app/database",
        "backend/app/app/core/db.py",
    ],
}

# Small root-level "infra" files always carried by scoped zips so the overlay on
# the server stays self-sufficient (compose, env, nginx/gateway/deploy).
SCOPE_INFRA_FILES = {
    "compose.dev.yml",
    "compose.prod.yml",
    "nginx",
    "gateway",
    "deploy",
    "infrastructure",
}
SCOPE_INFRA_ENV_PREFIXES = (".env",)

# Dev compose service targeted by each scope (backend restarts pick up schema
# init_db() and config reload). `all` keeps the existing full build+up.
SCOPE_SERVICES = {
    "frontend": "propaura_frontend_dev",
    "backend": "propaura_backend_dev",
    "storage": "propaura_backend_dev",
    "database": "propaura_backend_dev",
}

# Transport. --main/--release (branch self-pull) default to running locally on
# the server; explicit SSH flags push the code from this machine instead.
if github_mode:
    if not (args.local or args.sshLocal or args.sshPublic):
        args.local = True
elif not args.local and not args.sshLocal and not args.sshPublic:
    args.sshLocal = True  # backward compatibility

target_name = "local" if args.local else ("sshPublic" if args.sshPublic else "sshLocal")

build_enabled = (env == ENV_PROD) and not args.no_build and scope in ("all", "frontend")


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


def _load_barsep_env(path):
    """Read a dotenv file into a dict (VITE_* vars are what we care about)."""
    data = {}
    if not os.path.isfile(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def write_ports_env():
    """Regenerate deploy/ports.env from deploy/ports.py (canonical port
    registry) so bash scripts (deploy-release.sh, self-pull.sh) and the
    compose env files always agree with the single source of truth."""
    path = os.path.join(DEPLOY_DIR, "ports.env")
    with open(path, "w", encoding="utf-8") as f:
        f.write(deploy_ports.ports_env_lines())
    print(f"  Regenerated {path} from deploy/ports.py")


def provision_frontend_env(env_source):
    """Write the canonical frontend/.env used by the vite builds (all apps read
    it via `envDir: '../'`). VITE_GOOGLE_CLIENT_ID, VITE_APP_BASE_PATH and
    VITE_API_BASE_URL are drawn from the .env/ source of truth. For release this
    carries the public API origin (https://api.vijaykrsha.online) so the Pages
    bundle calls the backend instead of same-origin (which would 405 on Pages);
    for a dev-style source it stays empty for same-origin /rent/ proxying."""
    env_file = os.path.join(LOCAL_DIR, "frontend", ".env")
    client_id = ""
    app_base = "/rent"
    api_base = ""
    if os.path.isfile(env_source):
        env_map = _load_barsep_env(env_source)
        client_id = env_map.get("VITE_GOOGLE_CLIENT_ID", "")
        app_base = env_map.get("VITE_APP_BASE_PATH", "/rent")
        api_base = env_map.get("VITE_API_BASE_URL", "").strip()
    if not client_id:
        print(f"  WARNING: VITE_GOOGLE_CLIENT_ID not found in {env_source} — Google login will break")
    lines = [
        "VITE_APP_BASE_PATH=" + app_base,
        "VITE_API_BASE_URL=" + api_base,
        "VITE_GOOGLE_CLIENT_ID=" + client_id,
        "",
    ]
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Provisioned frontend/.env (Google client id set: {bool(client_id)}, API base: '{api_base or '(same-origin)'}')")


def build_frontends():
    if env == ENV_DEV:
        print("Skipping frontend builds (development env runs Vite live on the server).")
        return
    if args.no_build:
        print("Skipping frontend builds (--no-build).")
        return
    if scope not in ("all", "frontend"):
        print(f"Skipping frontend builds (scope: {scope}).")
        return
    check_node_version()
    print("Building frontend applications...")
    provision_frontend_env(os.path.join(LOCAL_DIR, ".env.release"))
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


def _zip_roots():
    """Walk roots for the current scope.

    Returns a list of (abs_path, arcname_root) pairs. arcname_root is the path
    prefix to keep inside the zip (relative to LOCAL_DIR); files use their own
    relative path. `--all` walks the whole repo exactly as before.
    """
    if scope == "all":
        return [(LOCAL_DIR, "")]
    roots = []
    for rel in SCOPE_PATHS[scope]:
        p = os.path.join(LOCAL_DIR, rel)
        if os.path.exists(p):
            roots.append((p, rel))
    for rel in sorted(SCOPE_INFRA_FILES):
        p = os.path.join(LOCAL_DIR, rel)
        if os.path.isfile(p):
            roots.append((p, rel))
        elif os.path.isdir(p):
            roots.append((p, rel))
    for fname in sorted(os.listdir(LOCAL_DIR)):
        if fname.startswith(SCOPE_INFRA_ENV_PREFIXES) and os.path.isfile(os.path.join(LOCAL_DIR, fname)):
            roots.append((os.path.join(LOCAL_DIR, fname), fname))
    return roots


def sync_env_files():
    """Copy the single-source-of-truth env credentials from .env/ into the
    root .env.development / .env.release files that deploy.py ships (and that
    compose loads via --env-file). If a source file is missing, the matching
    root file is left untouched (keeps existing server-side behavior intact)."""
    env_dir = os.path.join(LOCAL_DIR, ".env")
    pairs = {
        ".env.development": ".env.development",
        ".env.release": ".env.release",
    }
    if not os.path.isdir(env_dir):
        return
    for src_name, dst_name in pairs.items():
        src = os.path.join(env_dir, src_name)
        dst = os.path.join(LOCAL_DIR, dst_name)
        if os.path.isfile(src):
            with open(src, "r", encoding="utf-8") as f:
                content = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Synced env: .env/{src_name} -> {dst_name}")


def _is_excluded_rel(path, base_dir, exclude):
    """True if a path (relative to base_dir) should be excluded from the zip.

    Excludes a directory when *any* of its segments is in the exclude set, but
    never the docker/storage build context: that `storage` segment is a
    legitimate image build context, not the top-level storage/ data tree.
    """
    rel = os.path.relpath(path, base_dir).replace("\\", "/")
    if rel == ".":
        return False
    segs = rel.split("/")
    for i, seg in enumerate(segs):
        if seg in exclude and not (i > 0 and segs[i - 1] == "docker" and seg == "storage"):
            return True
    return False


def create_zip():
    sync_env_files()
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
    print(f"  Scope: {scope}" + ("" if scope == "all" else " (infra files always included)"))

    exclude = set(EXCLUDE_DIRS)
    if scope == "storage":
        exclude.discard("storage")  # --storage ships the DB/config/backup trees

    def write_file(zipf, abs_path, arcname):
        if os.path.basename(abs_path).endswith(".zip"):
            return
        zipf.write(abs_path, arcname=arcname.replace("\\", "/"))

    try:
        with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root_abs, arc_root in _zip_roots():
                if os.path.isfile(root_abs):
                    write_file(zipf, root_abs, arc_root)
                    continue
                for root, dirs, files in os.walk(root_abs):
                    if _is_excluded_rel(root, LOCAL_DIR, exclude):
                        dirs[:] = []
                        continue
                    dirs[:] = [d for d in dirs
                               if not _is_excluded_rel(os.path.join(root, d), LOCAL_DIR, exclude)]
                    for file in files:
                        local_path = os.path.join(root, file)
                        arcname = os.path.relpath(local_path, LOCAL_DIR)
                        write_file(zipf, local_path, arcname)
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
    base = f"docker compose --env-file {env_file} -f {compose}"
    svc = SCOPE_SERVICES.get(scope)

    if args.clean:
        cmds = [
            f"cd {REMOTE_DIR} && {base} down --rmi all -v --remove-orphans || true",
            f"echo '{get_password()}' | sudo -S rm -rf {REMOTE_DIR}",
            f"mkdir -p {REMOTE_DIR}",
            f"python3 -c \"import zipfile; zipfile.ZipFile('{REMOTE_ZIP}','r').extractall('{REMOTE_DIR}')\"",
            f"rm -f {REMOTE_ZIP}",
            f"cat > {REMOTE_DIR}/.dockerignore <<'DOCKEOF'\n{DOCKERIGNORE}DOCKEOF",
            "docker builder prune -af",
            f"cd {REMOTE_DIR} && {base} build --no-cache",
            f"cd {REMOTE_DIR} && {base} up -d --force-recreate",
        ]
    elif scope == "all" or svc is None:
        cmds = extract_zip_cmds()
        cmds.extend([
            f"cd {REMOTE_DIR} && {base} build",
            f"cd {REMOTE_DIR} && {base} up -d",
        ])
    elif scope == "frontend":
        # Dev frontend is a live bind-mounted Vite container (image-only, no
        # build context). Target the exact container with a docker restart so the
        # newly synced frontend/ tree is picked up; avoids `no such service`
        # that would come from passing a container_name to a compose command.
        cmds = extract_zip_cmds()
        cmds.append("docker restart propaura_frontend_dev")
    else:
        # Unified path for backend/storage/database dev scopes. The dev backend
        # is a bind-mounted image with uvicorn --reload, so code and config
        # changes are picked up live. Target the exact container with a docker
        # restart instead of `compose build/restart <container_name>`, which
        # would fail because compose subcommands expect the service name, not
        # the container_name (SCOPE_SERVICES holds container names). For storage
        # scope the restart also reloads the in-memory config cache from disk.
        cmds = extract_zip_cmds()
        cmds.append("docker restart propaura_backend_dev")
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
    print(f" MODE: {'PROD' if env == ENV_PROD else 'DEV'}   SCOPE: {scope.upper()}   REMOTE_DIR: {REMOTE_DIR}")
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
    print(f" SCOPE: {scope.upper()}")
    print(f" BUILD: {'skip' if not build_enabled else 'yes'}")
    print("=" * 50)

    write_ports_env()

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
            base = f"docker compose --env-file {env_file} -f {compose}"
            svc = SCOPE_SERVICES.get(scope)
            commands = []
            if args.clean:
                commands.extend([
                    f"cd {LOCAL_DIR} && {base} down --rmi all -v --remove-orphans || true",
                    f"cd {LOCAL_DIR} && {base} build --no-cache",
                    f"cd {LOCAL_DIR} && {base} up -d --force-recreate",
                ])
            elif scope == "all" or svc is None:
                commands.extend([
                    f"cd {LOCAL_DIR} && {base} build",
                    f"cd {LOCAL_DIR} && {base} up -d",
                ])
            elif scope == "frontend":
                commands.append("docker restart propaura_frontend_dev")
            else:
                # Unified path for backend/storage/database dev scopes. The dev
                # backend is a bind-mounted image with uvicorn --reload. Target
                # the exact container with a docker restart instead of
                # `compose build/restart <container_name>`, which would fail
                # because compose subcommands expect the service name, not the
                # container_name (SCOPE_SERVICES holds container names).
                commands.append("docker restart propaura_backend_dev")

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
