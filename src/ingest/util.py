# src/ingest/util.py

import subprocess
import socket
import getpass


def get_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def get_host_name():
    return socket.gethostname()


def get_user_name():
    return getpass.getuser()
