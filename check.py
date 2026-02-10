#!/usr/bin/env -S uv run --script

from pathlib import Path

from chorelib import Main, schedule, shell, task

main = Main()
SRCDIRS = ["src", "tests"]
SAMPLEDIRS = [d for d in Path("samples").glob("*") if d.is_dir()]


@task
def check():
    schedule("lint", "test")


@task
def lint():
    """Run ruff and mypy"""

    shell("ruff check --fix", SRCDIRS, SAMPLEDIRS)
    shell("ruff format", SRCDIRS, SAMPLEDIRS)
    shell("mypy --strict src tests")


@task
def test():
    """Run pytest"""
    shell("pytest tests")


if __name__ == "__main__":
    main.run()
