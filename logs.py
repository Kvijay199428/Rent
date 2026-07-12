import paramiko
import sys
import re
import time

HOST = "192.168.1.50"
USER = "vega"
PASSWORD = "1010"
REMOTE_DIR = "/home/vega/rent-app-20081"
LOG_FILE = "rent.log"

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

print(f"Connecting to {USER}@{HOST}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

channel = None

try:
    ssh.connect(HOST, username=USER, password=PASSWORD)
    transport = ssh.get_transport()
    transport.set_keepalive(10)

    print(f"\n--- Live Docker logs for {REMOTE_DIR} ---")
    print(f"--- Saving logs to {LOG_FILE} ---")
    print("--- Press CTRL + C to stop ---\n")

    cmd = (
        f"cd {REMOTE_DIR} && "
        f"if command -v docker-compose >/dev/null 2>&1; "
        f"then docker-compose logs -f --tail 50 --no-color; "
        f"else docker compose logs -f --tail 50 --no-color; fi"
    )

    channel = ssh.get_transport().open_session()
    channel.get_pty()
    channel.exec_command(cmd)

    buffer = ""

    with open(LOG_FILE, "a", encoding="utf-8") as log_f:
        while True:
            if channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                if not data:
                    break

                buffer += data

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    raw_line = line + "\n"

                    log_f.write(raw_line)
                    log_f.flush()

                    sys.stdout.write(colorize_line(raw_line))
                    sys.stdout.flush()

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
                    log_f.write(buffer)
                    log_f.flush()
                    sys.stdout.write(colorize_line(buffer))
                    sys.stdout.flush()
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