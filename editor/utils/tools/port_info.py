"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared socket-to-PID discovery helpers used by the terminal Ports tab
and the system monitor. Prefers ``psutil.net_connections`` and degrades
gracefully to parsing ``ss`` output when the system call is denied.
"""

import re
import socket
import subprocess

import psutil

_SS_TIMEOUT_SECONDS = 5


def service_name(port: int, protocol: str) -> str:
    """Resolve the IANA service name for a port number.

    Args:
        port: Numeric port as reported by the socket table.
        protocol: Either ``"tcp"`` or ``"udp"``.

    Returns:
        The well-known service name, or ``"-"`` when unresolved.
    """
    try:
        return socket.getservbyport(int(port), protocol) or "-"
    except (OSError, OverflowError, ValueError):
        return "-"


def _parse_ss_output(listen_only: bool = False) -> dict:
    """Parse ``ss`` output into a ``pid -> {(port, proto)}`` mapping.

    Used as a fallback when ``psutil.net_connections`` raises
    ``AccessDenied``, which happens whenever the IDE is not running as
    root. PIDs owned by other users are invisible to both tools, so
    this is strictly best-effort.

    Args:
        listen_only: Restrict parsing to listening sockets.

    Returns:
        Dictionary mapping each PID to a set of ``(port, proto)``
        tuples. Empty when ``ss`` is unavailable or silent.
    """
    result: dict = {}
    flags = ["-tulpnH"] + (["-l"] if listen_only else [])
    try:
        proc = subprocess.run(
            ["ss", *flags],
            capture_output=True,
            text=True,
            timeout=_SS_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return result

    for line in proc.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0] == "Netid":
            continue
        proto = fields[0].lower()
        local_addr = fields[4]
        try:
            port = int(local_addr.rsplit(":", 1)[1])
        except (ValueError, IndexError):
            continue
        for pid in re.findall(r"pid=(\d+)", line):
            result.setdefault(int(pid), set()).add((str(port), proto))
    return result


def fetch_pid_to_ports(listen_only: bool = True) -> dict:
    """Build a ``pid -> {(port, proto)}`` map of open sockets.

    Args:
        listen_only: When True only listening (server) sockets are
            reported, matching what tools like ``ss -tlnp`` display.
            When False established and outbound sockets are included,
            which mostly yields ephemeral ports.

    Returns:
        Dictionary mapping each PID to a set of ``(port, proto)``
        tuples. Falls back to ``ss`` parsing when socket enumeration
        is denied instead of returning a silently empty map.
    """
    result: dict = {}
    try:
        for conn in psutil.net_connections(kind="inet"):
            if not conn.pid or not conn.laddr:
                continue
            if listen_only and conn.status != psutil.CONN_LISTEN:
                continue
            proto = "tcp" if conn.type == socket.SOCK_STREAM else "udp"
            result.setdefault(conn.pid, set()).add((str(conn.laddr.port), proto))
        return result
    except (psutil.AccessDenied, PermissionError, OSError):
        pass
    return _parse_ss_output(listen_only)
