"""Fake browser Worker scripts that speak the containment handshake.

They stand in for the real Worker so process containment can be tested without
Chromium. Each script announces itself, waits for the parent acknowledgement, and
only then spawns descendants. Spawning before the acknowledgement would be the
race the handshake exists to remove.
"""

from __future__ import annotations

HANDSHAKE_PREAMBLE = (
    "import json, os, subprocess, sys, time\n"
    "sys.stdout.write(json.dumps({'message_type': 'hello',"
    " 'protocol': 'browser.worker.v2', 'pid': os.getpid()}) + '\\n')\n"
    "sys.stdout.flush()\n"
    "ack = sys.stdin.readline()\n"
    "if not ack.strip():\n"
    "    sys.exit(2)\n"
)


def descendant_script(pid_path: str, *, sleep_seconds: int = 30) -> str:
    """Spawn one descendant after the acknowledgement and record its pid."""

    return HANDSHAKE_PREAMBLE + (
        f"path = {pid_path!r}\n"
        f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep({sleep_seconds})'])\n"
        "open(path, 'w', encoding='utf-8').write(str(child.pid))\n"
        f"time.sleep({sleep_seconds})\n"
    )


def memory_breach_script(*, allocate_mib: int = 512) -> str:
    """Allocate well past the cgroup memory ceiling inside the contained tree."""

    return HANDSHAKE_PREAMBLE + (
        "child = subprocess.Popen(\n"
        "    [sys.executable, '-c', 'blocks = []\\n"
        f"for _ in range({allocate_mib}):\\n"
        "    blocks.append(bytearray(1024 * 1024))\\n"
        "import time; time.sleep(30)'],\n"
        ")\n"
        "time.sleep(30)\n"
    )


def pids_breach_script(*, attempts: int = 64) -> str:
    """Fork past the cgroup pids ceiling and report how many children survived."""

    return HANDSHAKE_PREAMBLE + (
        "spawned = 0\n"
        f"for _ in range({attempts}):\n"
        "    try:\n"
        "        subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\n"
        "    except OSError:\n"
        "        break\n"
        "    spawned += 1\n"
        "sys.stderr.write('spawned=%d\\n' % spawned)\n"
        "sys.stderr.flush()\n"
        "time.sleep(30)\n"
    )
