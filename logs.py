import sys
import re
import time
import shlex
import argparse
import subprocess

try:
    import paramiko
except ImportError:
    paramiko = None

ENVIRONMENTS = {
    "dev": {
        "name": "dev",
        "label": "rent-dev",
        "remote_dir": "/home/vega/rent-app",
        "compose_file": "compose.dev.yml",
        "env_file": ".env.development",
        "log_file": "rent-dev.log",
    },
    "prod": {
        "name": "prod",
        "label": "rent-prod",
        "remote_dir": "/home/vega/rent-app-release",
        "compose_file": "compose.prod.yml",
        "env_file": ".env.release",
        "log_file": "rent-prod.log",
    },
}

TARGETS = {
    "sshLocal": {"host": "192.168.1.50", "port": 22, "user": "vega", "password": "1010"},
    "sshPublic": {"host": "100.107.83.28", "port": 22009, "user": "vega", "password": "1010"},
}

COLORS = [
    '\033[96m',
    '\033[92m',
    '\033[93m',
    '\033[94m',
    '\033[95m',
]
RESET = '\033[0m'

container_colors = {}


def get_color(container_name):
    if container_name not in container_colors:
        color = COLORS[len(container_colors) % len(COLORS)]
        container_colors[container_name] = color
    return container_colors[container_name]


def colorize_line(line):
    match = re.match(r'^([^|]+?)\s*\|\s?(.*)$', line.rstrip('\r\n'))
    if match:
        container_name = match.group(1).strip()
        log_content = match.group(2)
        color = get_color(container_name)
        return f"{color}{container_name} |{RESET} {log_content}\n"
    return line


def write_and_print(line, log_f):
    log_f.write(line)
    log_f.flush()
    sys.stdout.write(colorize_line(line))
    sys.stdout.flush()


def build_cmd(ctx, tail, services):
    cmd = (
        f"cd {ctx['remote_dir']} && "
        f"docker compose --env-file {ctx['env_file']} -f {ctx['compose_file']} "
        f"logs -f --tail {tail} --no-color"
    )
    if services:
        cmd += " " + " ".join(shlex.quote(s) for s in services)
    return cmd


# ── Args ─────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Stream live Docker logs from the Rent dev/prod stacks")
group = parser.add_mutually_exclusive_group()
group.add_argument("--local", action="store_true", help="Stream logs locally (no SSH).")
group.add_argument("--sshLocal", action="store_true", help="Stream logs via SSH to LAN (192.168.1.50).")
group.add_argument("--sshPublic", action="store_true", help="Stream logs via SSH to public IP (100.107.83.28:22009).")
env_group = parser.add_mutually_exclusive_group()
env_group.add_argument("--dev", action="store_true", help="Stream the dev stack (compose.dev.yml). Default when no env flag is given.")
env_group.add_argument("--prod", action="store_true", help="Stream the production stack (compose.prod.yml).")
parser.add_argument("--tail", type=int, default=50, help="Number of recent log lines to show (default: 50).")
parser.add_argument("--service", action="append", dest="services", default=[], help="Limit to specific services/containers (repeatable).")
parser.add_argument("--out", default=None, help="Log file path (default: rent-dev.log / rent-prod.log).")
args = parser.parse_args()

if not args.local and not args.sshLocal and not args.sshPublic:
    args.sshLocal = True

target_name = "local" if args.local else ("sshPublic" if args.sshPublic else "sshLocal")
env_name = "prod" if args.prod else "dev"
ctx = ENVIRONMENTS[env_name]
log_file = args.out or ctx["log_file"]


# ── LOCAL mode ───────────────────────────────────────────────────────────────

if args.local:
    print(f"\n--- Live Docker logs ({ctx['label']}) local ---")
    print(f"--- Saving logs to {log_file} ---")
    print("--- Press CTRL + C to stop ---\n")

    cmd = build_cmd(ctx, args.tail, args.services)

    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with open(log_file, "a", encoding="utf-8") as log_f:
            for raw_line in iter(proc.stdout.readline, b""):
                line = raw_line.decode("utf-8", errors="replace")
                if not line:
                    break
                write_and_print(line, log_f)
    except KeyboardInterrupt:
        print("\nStopping log stream...")
        proc.terminate()
    finally:
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("Done.")


# ── SSH modes ────────────────────────────────────────────────────────────────

else:
    cfg = TARGETS[target_name]

    if paramiko is None:
        print("ERROR: paramiko is not installed. Run: pip install paramiko")
        sys.exit(1)

    print(f"Connecting to {cfg['user']}@{cfg['host']}:{cfg['port']}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    channel = None

    try:
        ssh.connect(cfg["host"], port=cfg["port"], username=cfg["user"], password=cfg["password"], timeout=30)
        transport = ssh.get_transport()
        transport.set_keepalive(10)

        print(f"\n--- Live Docker logs ({ctx['label']} @ {ctx['remote_dir']}) ---")
        print(f"--- Saving logs to {log_file} ---")
        print("--- Press CTRL + C to stop ---\n")

        cmd = build_cmd(ctx, args.tail, args.services)

        channel = ssh.get_transport().open_session()
        channel.get_pty()
        channel.exec_command(cmd)

        buffer = ""

        with open(log_file, "a", encoding="utf-8") as log_f:
            while True:
                if channel.recv_ready():
                    data = channel.recv(4096).decode("utf-8", errors="replace")
                    if not data:
                        break

                    buffer += data

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        raw_line = line + "\n"
                        write_and_print(raw_line, log_f)

                elif channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    if data:
                        for line in data.splitlines(True):
                            log_f.write(line)
                            log_f.flush()
                            sys.stdout.write(line)
                            sys.stdout.flush()

                elif channel.exit_status_ready():
                    if buffer:
                        write_and_print(buffer, log_f)
                        buffer = ""
                    break
                else:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping log stream...")
        try:
            if channel is not None:
                channel.send("\x03")
                time.sleep(0.5)
                channel.close()
        except Exception:
            pass

    except Exception as e:
        print(f"Error: {e}")

    finally:
        try:
            ssh.close()
        except Exception:
            pass
        print("Done.")
