import asyncio
import os
import re
import threading
import time
from pathlib import Path

import pytest

from chorelib import errors, ruledef, utils
from chorelib.deprunner import run


def builder(target: str, depends: list[str], needs: list[str]) -> None:
    pass


def test_build(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt", depends="b.txt", needs="c.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        assert target == "a.txt"
        assert depends == ["b.txt"]
        assert needs == ["c.txt"]
        (tmp_path / "a.txt").write_text("a.txt")

    @rules.rule("b.txt")
    def make_b(target: str, depends: list[str], needs: list[str]) -> None:
        assert target == "b.txt"
        assert depends == []
        assert needs == []
        (tmp_path / "b.txt").write_text("b.txt")

    @rules.rule("c.txt")
    def make_c(target: str, depends: list[str], needs: list[str]) -> None:
        assert target == "c.txt"
        assert depends == []
        assert needs == []
        (tmp_path / "c.txt").write_text("c.txt")

    with utils.chdir(tmp_path):
        asyncio.run(run(rules, ["a.txt"]))
        assert sorted(os.listdir(tmp_path)) == ["a.txt", "b.txt", "c.txt"]

        ts = {filename: os.path.getmtime(filename) for filename in os.listdir(tmp_path)}

        (tmp_path / "a.txt").unlink()
        time.sleep(0.01)

        asyncio.run(run(rules, ["a.txt"]))
        assert sorted(os.listdir(tmp_path)) == ["a.txt", "b.txt", "c.txt"]

        ts2 = {filename: os.path.getmtime(filename) for filename in os.listdir(tmp_path)}
        assert ts["a.txt"] != ts2["a.txt"]
        assert ts["b.txt"] == ts2["b.txt"]
        assert ts["c.txt"] == ts2["c.txt"]

        (tmp_path / "b.txt").unlink()
        time.sleep(0.01)

        asyncio.run(run(rules, ["a.txt"]))
        assert sorted(os.listdir(tmp_path)) == ["a.txt", "b.txt", "c.txt"]

        ts3 = {filename: os.path.getmtime(filename) for filename in os.listdir(tmp_path)}
        assert ts["a.txt"] != ts3["a.txt"]
        assert ts["b.txt"] != ts3["b.txt"]
        assert ts["c.txt"] == ts3["c.txt"]

        (tmp_path / "c.txt").unlink()
        time.sleep(0.01)
        asyncio.run(run(rules, ["a.txt"]))
        assert sorted(os.listdir(tmp_path)) == ["a.txt", "b.txt", "c.txt"]

        ts4 = {filename: os.path.getmtime(filename) for filename in os.listdir(tmp_path)}
        assert ts3["a.txt"] == ts4["a.txt"]
        assert ts3["b.txt"] == ts4["b.txt"]
        assert ts3["c.txt"] != ts4["c.txt"]


def test_no_deps(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        Path("a.txt").write_text("update")

    with utils.chdir(tmp_path):
        a_txt = tmp_path / "a.txt"
        a_txt.write_text("a.txt")
        asyncio.run(run(rules, ["a.txt"]))
        assert a_txt.read_text() == "a.txt"


def test_mtime_file(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt", depends="b.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        Path("a.txt").write_text("updated")

    with utils.chdir(tmp_path):
        (tmp_path / "a.txt").write_text("a.txt")
        b_txt = tmp_path / "b.txt"
        b_txt.write_text("b.txt")
        mtime = os.path.getmtime(b_txt) + 0.1
        os.utime(
            b_txt,
            (mtime, mtime),
        )
        asyncio.run(run(rules, ["a.txt"]))

        assert (tmp_path / "a.txt").read_text() == "updated"


def test_mtime_func(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt", depends="b.txt", needs="c.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        print("><", target, depends, needs)
        assert target == "a.txt"
        assert depends == ["b.txt"]
        assert needs == ["c.txt"]
        Path("a.txt").write_text("updated")

    @rules.rule(re.compile(r"(.*)\.txt"))
    def make_txt(target: str, depends: list[str], needs: list[str]) -> None:
        assert 0  # should not be called

    @rules.mtime("a.txt")
    def mtime_a(filename: str) -> int:
        return 1000

    @rules.mtime(re.compile(r"(.*)\.txt"))
    def mtime_b(filename: str) -> int:
        return 2000

    with utils.chdir(tmp_path):
        (tmp_path / "a.txt").write_text("a.txt")

        asyncio.run(run(rules, ["a.txt"]))

        assert os.listdir(tmp_path) == ["a.txt"]
        assert (tmp_path / "a.txt").read_text() == "updated"


def test_no_builder(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt", depends="b.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        pass

    with utils.chdir(tmp_path):
        with pytest.raises(errors.RuleNotFoundError) as excinfo:
            asyncio.run(run(rules, ["a.txt"]))
        assert excinfo.value.args[0] == "b.txt"


def test_thread(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()

    @rules.rule("a.txt")
    def make_a(target: str, depends: list[str], needs: list[str]) -> None:
        print("make a")
        ev.wait()
        Path(target).write_text("a.txt")

    @rules.rule("b.txt")
    def make_b(target: str, depends: list[str], needs: list[str]) -> None:
        print("make b")
        ev.set()
        Path(target).write_text("b.txt")

    ev = threading.Event()
    with utils.chdir(tmp_path):
        asyncio.run(run(rules, ["a.txt", "b.txt"], num_workers=2))


def test_add_build_targets(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()
    from chorelib.deprunner import schedule

    @rules.task
    def task1() -> None:
        schedule(["task2"])

    @rules.task
    def task2() -> None:
        open("task2.txt", "w").write("task2")

    with utils.chdir(tmp_path):
        asyncio.run(run(rules, ["task1"]))
        assert (tmp_path / "task2.txt").read_text() == "task2"


def test_add_build_targets_thread(tmp_path: Path) -> None:
    rules = ruledef.RuleSet()
    from chorelib.deprunner import schedule

    @rules.task
    def task1() -> None:
        schedule(["task2"])

    @rules.task
    def task2() -> None:
        open("task2.txt", "w").write("task2")

    with utils.chdir(tmp_path):
        asyncio.run(run(rules, ["task1"], num_workers=2))
        assert (tmp_path / "task2.txt").read_text() == "task2"
