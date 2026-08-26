"""Only one copy of BabelChat runs at a time, and the old one steps aside.

Split out of the entry point, which had grown past the line limit and was
carrying two unrelated jobs: wiring the application together, and deciding
whether another copy of it is already running. This is the second one, and it
is the half with the sharp edge — it terminates a process — so it is easier to
find and to read on its own.

The sharp edge, in one paragraph: the lock file used to hold a bare PID, and
startup opened that PID with PROCESS_TERMINATE and killed it. Windows hands
PIDs back out, so the number written yesterday may belong to the user's editor
today. The file records the start stamp beside the PID now; a process that
took over the number necessarily started later, so the pair identifies the
copy we meant and nothing else.
"""

from __future__ import annotations

import ctypes
import logging
import os
import signal
import sys

logger = logging.getLogger(__name__)


def _get_lock_file() -> str:
    if getattr(__import__("sys"), "frozen", False):
        lock_dir = os.path.join(os.path.expanduser("~"), ".config", "BabelChat")
        os.makedirs(lock_dir, exist_ok=True)
        return os.path.join(lock_dir, "babelchat.lock")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "babelchat.lock")


_LOCK_FILE = _get_lock_file()


def _linux_start_time(stat_line: str) -> str:
    """`starttime` out of a line of /proc/<pid>/stat.

    Separate from the reading so it can be tested where /proc does not exist,
    which is where this project is developed. The parsing is not obvious: field
    two is the executable name in parentheses, and it may itself contain spaces
    and parentheses — `(my prog) (v2)` is a legal name — so splitting the line
    on whitespace from the left puts every later field at an offset that
    depends on what the process is called. Counting from the last ')' is the
    documented way round it. starttime is field 22, and the last ')' ends field
    two, so it is index 19 in what follows.
    """
    return stat_line.rpartition(")")[2].split()[19]


def _start_stamp(pid: int) -> str | None:
    """When the process at `pid` started, as the operating system recorded it.

    A PID on its own does not identify a process for longer than that process
    lives: Windows hands the numbers back out, and Linux wraps them. The lock
    file outlives the copy that wrote it, so by the time it is read the number
    in it may belong to something the user very much wants to keep running.

    Paired with the PID, the start time is unique — a process that took over the
    number necessarily started later. Returns None when the answer is unknown,
    which the caller must treat as "do not touch it".
    """
    try:
        if sys.platform == "win32":
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return None
            try:
                created = ctypes.c_ulonglong()
                exited = ctypes.c_ulonglong()
                kernel_time = ctypes.c_ulonglong()
                user_time = ctypes.c_ulonglong()
                ok = kernel32.GetProcessTimes(
                    handle,
                    ctypes.byref(created),
                    ctypes.byref(exited),
                    ctypes.byref(kernel_time),
                    ctypes.byref(user_time),
                )
                return str(created.value) if ok else None
            finally:
                kernel32.CloseHandle(handle)

        if sys.platform.startswith("linux"):
            with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
                return _linux_start_time(f.read())
    except (OSError, ValueError, IndexError):
        return None

    return None


def _terminate(pid: int) -> None:
    """Stop the previous copy. Only ever called for a verified match."""
    if sys.platform == "win32":
        PROCESS_TERMINATE = 0x0001
        SYNCHRONIZE = 0x00100000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE, False, pid)
        if not handle:
            logger.info("Old PID %d is already gone", pid)
            return
        kernel32.TerminateProcess(handle, 0)
        kernel32.WaitForSingleObject(handle, 2000)
        kernel32.CloseHandle(handle)
    else:
        import time as _time

        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            logger.info("Old PID %d is already gone", pid)
            return
        _time.sleep(0.5)
    logger.info("Stopped the previous instance, PID %d", pid)


def _ensure_single_instance() -> None:
    """Stop the previous copy of BabelChat, and nothing else.

    The lock file carries the PID and the start stamp of the process that wrote
    it. Both must match a live process before anything is terminated; a lock
    with only a PID — written by a version before this check existed — matches
    nothing, so an upgrade leaves the running copy for the user to close rather
    than gambling on the number.
    """
    lock_path = os.path.abspath(_LOCK_FILE)
    if os.path.exists(lock_path):
        try:
            with open(lock_path, encoding="utf-8") as f:
                recorded = f.read().splitlines()
            old_pid = int(recorded[0].strip())
            was = recorded[1].strip() if len(recorded) > 1 else ""
            now = _start_stamp(old_pid)

            # One condition, deliberately. An earlier version spelled the three
            # ways this can fail as three branches, and each of them turned out
            # to be unreachable — the comparison below already rejects a missing
            # stamp, an unknown one and a mismatched one. Branches that cannot
            # change the outcome cannot be tested either, and they read as if
            # they were load-bearing.
            if now and now == was:
                _terminate(old_pid)
            else:
                logger.info(
                    "Leaving PID %d alone: the lock says it started at %s, the live process says %s",
                    old_pid,
                    was or "(nothing)",
                    now or "(nothing there)",
                )
        except (OSError, ValueError, IndexError) as e:
            logger.warning("Could not read the lock file: %s", e)

    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(f"{os.getpid()}\n{_start_stamp(os.getpid()) or ''}\n")
