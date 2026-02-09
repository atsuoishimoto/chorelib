"""Utility functions for shell execution, logging, and data manipulation."""

import datetime
import logging
import os
import shlex
import subprocess
import sys
from collections.abc import Iterable, Iterator
from typing import Any

import chorelib

logger = logging.getLogger(__name__)


def flatten(seq: Any, ignore_none: bool = True) -> Iterator[Any]:
    """Recursively flatten nested iterables into a single sequence.

    Strings are treated as atomic values and are not iterated over.

    Args:
        seq: A value or nested iterable to flatten.
        ignore_none: If True, None values are skipped.

    Yields:
        Individual non-iterable elements from the input.
    """
    if isinstance(seq, str) or (not isinstance(seq, Iterable)):
        yield seq
        return

    for item in seq:
        if isinstance(item, str) or (not isinstance(item, Iterable)):
            if ignore_none and (item is None):
                continue
            yield item
        else:
            yield from flatten(item)


def unique_list(lst: Iterable[Any]) -> list[Any]:
    """Return a list with duplicates removed, preserving insertion order.

    Args:
        lst: An iterable of hashable elements.

    Returns:
        A list containing only the first occurrence of each element.
    """
    return list({e: None for e in lst}.keys())


def to_timestamp(ts: Any) -> Any:
    """Convert a value to a numeric timestamp.

    Args:
        ts: A datetime object or numeric timestamp. If a naive datetime
            (without tzinfo) is given, it is treated as UTC.

    Returns:
        A float timestamp, or the original value if not a datetime.
    """
    match ts:
        case datetime.datetime():
            if not ts.tzinfo:
                return ts.replace(tzinfo=datetime.timezone.utc).timestamp()
            return ts.timestamp()
        case _:
            return ts


def shell(
    *cmd: Any,
    cwd: str | None = None,
    text: bool = True,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    echo: bool = True,
) -> str | None:
    """Execute a command string via the system shell.

    Multiple arguments are joined with spaces into a single shell command line.

    Args:
        *cmd: Command string(s) or objects to execute. Nested sequences
            are recursively flattened and each element is converted to
            a string, then joined with spaces into a single command line.
        cwd: Working directory for the command.
        text: If True, decode stdout/stderr as text.
        check: If True, raise CalledProcessError on non-zero exit.
        capture: If True, capture and return stdout.
        env: Environment variables for the subprocess.
        echo: If True, print the command to stderr.

    Returns:
        The captured stdout string if capture=True, otherwise None.
    """
    cmdstr: str
    match cmd:
        case Iterable():
            cmdstr = " ".join(str(c) for c in flatten(cmd))
        case _:
            cmdstr = str(cmd)

    stdout: int | None = None
    if capture:
        stdout = subprocess.PIPE
    if echo:
        message(cmdstr, 0)

    ret = subprocess.run(
        cmdstr, cwd=cwd, shell=True, stdout=stdout, text=text, check=check, env=env
    )
    if stdout:
        return ret.stdout  # type: ignore[no-any-return]
    return None


def command(
    *cmd: Any,
    cwd: str | None = None,
    text: bool = True,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    echo: bool = True,
) -> str | None:
    """Execute a command directly without a shell (no shell interpretation).

    Each argument is passed as a separate element in the argument list,
    avoiding shell injection risks.

    Args:
        *cmd: Command and arguments to execute. Nested sequences are
            recursively flattened and each element is converted to a
            string before being passed to the subprocess.
        cwd: Working directory for the command.
        text: If True, decode stdout/stderr as text.
        check: If True, raise CalledProcessError on non-zero exit.
        capture: If True, capture and return stdout.
        env: Environment variables for the subprocess.
        echo: If True, print the command to stderr.

    Returns:
        The captured stdout string if capture=True, otherwise None.
    """
    stdout: int | None = None
    if capture:
        stdout = subprocess.PIPE

    cmdlist: list[str] = [str(c) for c in flatten(cmd)]
    if echo:
        message(shlex.join(cmdlist))

    ret = subprocess.run(
        cmdlist, cwd=cwd, shell=False, stdout=stdout, text=text, check=check, env=env
    )
    if stdout:
        return ret.stdout  # type: ignore[no-any-return]
    return None


def message(msg: str, level: int = 0) -> None:
    """Print a message to stderr if the current verbosity level is sufficient.

    Args:
        msg: The message string to display.
        level: Minimum verbosity level required to show the message.
            The message is printed only when ``chorelib.verbose >= level``.
    """
    if level <= chorelib.verbose:
        print(msg, file=sys.stderr)


class chdir:
    """Non thread-safe context manager to change the current working directory."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = path
        self._old_cwd: list[str] = []

    def __enter__(self) -> None:
        self._old_cwd.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, *excinfo: object) -> None:
        os.chdir(self._old_cwd.pop())
