#!/usr/bin/env -S uv run --script

from pathlib import Path
from chorelib import Main, task, shell

SRCDIRS = ["src", "tests"]
SAMPLEDIRS = [d for d in Path("samples").glob("*") if d.is_dir()]

@task
def lint():
    """Run ruff and mypy"""

    shell("ruff check --fix", SRCDIRS, SAMPLEDIRS)
    shell("ruff format", SRCDIRS, SAMPLEDIRS)
    shell("mypy --strict src tests")

    for sample in SAMPLEDIRS:
        shell("mypy --strict --ignore-missing-imports --install-types", sample)

if __name__ == '__main__':
    Main().run()
