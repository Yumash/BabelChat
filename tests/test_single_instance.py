"""Starting a second copy stops the first one. It must stop nothing else.

The lock file held a bare PID, and startup opened that PID with
PROCESS_TERMINATE and killed it. Windows hands PIDs back out: after a reboot,
or on a machine that has been up long enough to wrap the number space, the PID
written yesterday belongs to something else today — a browser, a game, the
user's own editor — and BabelChat would terminate it without a word.

The fix is to record what the process *was*, not only which number it had. The
operating system stamps every process with the moment it started; the pair
(pid, start stamp) is unique for as long as the process lives, and a reused PID
carries a different stamp by construction.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app import single_instance


@pytest.fixture
def lock(tmp_path, monkeypatch):
    """Point the module at a lock file of our own and count the kills."""
    path = tmp_path / "babelchat.lock"
    monkeypatch.setattr(single_instance, "_LOCK_FILE", str(path))

    killed: list[int] = []
    monkeypatch.setattr(single_instance, "_terminate", lambda pid: killed.append(pid))

    return SimpleNamespace(path=path, killed=killed)


def test_a_reused_pid_is_not_killed(lock, monkeypatch):
    """The whole point. Same number, different process — leave it alone."""
    lock.path.write_text("4242\nstarted-yesterday\n", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: "started-today")

    single_instance._ensure_single_instance()

    assert lock.killed == [], "terminated a process that only shares the number"


def test_the_previous_copy_is_killed(lock, monkeypatch):
    """And the feature still works: same number, same process."""
    lock.path.write_text("4242\nstarted-yesterday\n", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: "started-yesterday")

    single_instance._ensure_single_instance()

    assert lock.killed == [4242]


def test_an_unknown_stamp_kills_nothing(lock, monkeypatch):
    """`_start_stamp` returns None when the process is gone — and also when the
    query failed for some other reason. Both are 'I do not know', and killing on
    'I do not know' is what this test exists to prevent."""
    lock.path.write_text("4242\nstarted-yesterday\n", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: None)

    single_instance._ensure_single_instance()

    assert lock.killed == []


def test_a_lock_from_an_older_version_kills_nothing(lock, monkeypatch):
    """One line, no stamp — written by the version this test was added to fix.
    There is nothing to compare against, so the old copy is left running and the
    user closes it by hand. Nobody's unrelated process dies for the upgrade."""
    lock.path.write_text("4242", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: "started-today")

    single_instance._ensure_single_instance()

    assert lock.killed == []


def test_an_empty_stamp_never_matches_an_old_lock(lock, monkeypatch):
    """Belt and braces. A lock written before stamps existed carries an empty
    one, so a platform whose stamp came back empty would match it and kill on a
    bare PID again — the exact bug, reintroduced by a plausible edit somewhere
    else entirely."""
    lock.path.write_text("4242\n\n", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: "")

    single_instance._ensure_single_instance()

    assert lock.killed == []


def test_a_damaged_lock_does_not_stop_the_app(lock, monkeypatch):
    lock.path.write_text("not a pid at all", encoding="utf-8")
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: "started-today")

    single_instance._ensure_single_instance()

    assert lock.killed == []
    assert lock.path.read_text(encoding="utf-8").splitlines()[0] == str(single_instance.os.getpid())


def test_the_lock_records_this_process(lock, monkeypatch):
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: f"stamp-of-{pid}")

    single_instance._ensure_single_instance()

    pid, stamp = lock.path.read_text(encoding="utf-8").splitlines()[:2]
    assert pid == str(single_instance.os.getpid())
    assert stamp == f"stamp-of-{single_instance.os.getpid()}"


def test_the_lock_is_written_even_with_no_stamp_available(lock, monkeypatch):
    """A platform we cannot query still gets single-instance behaviour on the
    next run — it just never kills anything. Writing no lock at all would leave
    stale files around and change nothing for the better."""
    monkeypatch.setattr(single_instance, "_start_stamp", lambda pid: None)

    single_instance._ensure_single_instance()

    assert lock.path.read_text(encoding="utf-8").splitlines()[0] == str(single_instance.os.getpid())


# ── the stamp itself, against the real operating system ──────────────────────


def test_this_process_has_a_stamp():
    """A test double is only worth something if the real thing behaves the same
    way. Windows and Linux are both covered by the implementation; anywhere else
    the function is allowed to say it does not know."""
    stamp = single_instance._start_stamp(single_instance.os.getpid())

    if sys.platform in ("win32", "linux"):
        assert stamp, f"no start stamp for our own process on {sys.platform}"
    elif stamp is None:
        pytest.skip(f"no stamp implementation for {sys.platform}")


def test_a_pid_that_cannot_exist_has_no_stamp():
    """PIDs are bounded; this one is past the end on both platforms."""
    assert single_instance._start_stamp(0x7FFFFFFF) is None


# ── /proc parsing, testable where there is no /proc ──────────────────────────

#: A real line, from `cat /proc/self/stat`, with the fields after the command
#: name in their documented order. starttime — field 22 — is 8654321.
STAT = (
    "1234 (BabelChat) S 1200 1234 1234 0 -1 4194304 1523 0 0 0 12 3 0 0 "
    "20 0 4 0 8654321 145678336 3421 18446744073709551615 4194304 5242880 "
    "140725430044160 0 0 0 0 4096 0 0 0 0 17 2 0 0 0 0 0\n"
)


def test_the_start_time_is_read_from_the_documented_field():
    assert single_instance._linux_start_time(STAT) == "8654321"


def test_a_command_name_full_of_spaces_and_brackets_does_not_shift_the_field():
    """Linux lets a process call itself almost anything, and the name is not
    quoted or escaped in this file. Counting fields from the left of the line
    would read a different number for a process named like this one — which is
    also how a process could choose a name that makes it look like ours."""
    hostile = STAT.replace("(BabelChat)", "(evil ) prog (x) )")

    assert single_instance._linux_start_time(hostile) == "8654321"


def test_the_stamp_is_stable_across_calls():
    """It is compared between two runs of the program, so a stamp that changed
    between calls would make every previous copy look like a stranger and the
    single-instance behaviour would quietly stop working."""
    pid = single_instance.os.getpid()

    assert single_instance._start_stamp(pid) == single_instance._start_stamp(pid)
