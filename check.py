#!/usr/bin/env -S uv run --script

from pathlib import Path

from chorelib import Main, schedule, shell, task


class CheckMain(Main):
    def add_arguments(self, parser):
        parser.add_argument(
            "--ci",
            dest="ci",
            action="store_true",
            default=False,
            help="Run in Github action",
        )


main = CheckMain()
SRCDIRS = ["src", "tests"]
SAMPLEDIRS = [d for d in Path("samples").glob("*") if d.is_dir()]
CHECKFILES = ("./check.py",)


@task
def check():
    schedule("lint", "test")


@task
def lint():
    """Run ruff and mypy"""

    shell(
        "ruff check",
        "--output-format=github" if main.args.ci else "--fix",
        CHECKFILES,
        SRCDIRS,
        SAMPLEDIRS,
    )
    shell("ruff format --check", CHECKFILES, SRCDIRS, SAMPLEDIRS)
    shell("mypy --strict src tests")


@task
def test():
    """Run pytest"""
    shell("pytest tests")


if __name__ == "__main__":
    main.run()
