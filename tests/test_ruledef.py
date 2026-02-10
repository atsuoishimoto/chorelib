import re
from pathlib import Path
from typing import Any

import pytest

from chorelib import depgraph, errors, ruledef


def f(target: str, depends: list[str], needs: list[str]) -> None:
    pass


def test_ruledef() -> None:
    rule = ruledef.Rule(
        builder=None,
        targets="abc",
        depends=["xyz", ["def"]],
        needs=["123", ["456"]],
        doc="doc",
    )
    rule.set_builder(f)
    assert rule.targets == ["abc"]
    assert rule.depends == ["xyz", "def"]
    assert rule.needs == ["123", "456"]
    assert rule.builder is f
    assert rule.doc == "doc"


def test_taskdef() -> None:
    task = ruledef.Task(
        name="name",
        needs=["123", ["456"]],
        default=True,
        builder=None,
        doc="doc",
    )

    task.set_builder(f)

    assert task.depends == []
    assert task.needs == ["123", "456"]
    assert task.builder is f
    assert task.doc == "doc"


def test_ruleset_select_rule() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="abc", depends=["def"], needs=["123"])
    rules.rule(targets="abc", depends=["ghi"], needs="xyz")(f)
    rules.rule(targets="xxx", needs=["456"])

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert set(deps) == {"ghi"}
    assert set(needs) == {"xyz"}


def test_ruleset_select_path() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets=Path("abc"), depends=[Path("def")], needs=[Path("123")])(f)

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert set(deps) == {"def"}
    assert set(needs) == {"123"}


def test_ruleset_select_callable() -> None:
    rules = ruledef.RuleSet()

    def dep(rule: Any, match: re.Match[str]) -> tuple[str, list[str], Path]:
        return (match[0] + "-dep", ["dep2"], Path("dep3"))

    rules.rule(targets=Path("abc"), depends=[dep], needs=[dep])(f)

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert set(deps) == {"abc-dep", "dep2", "dep3"}
    assert set(needs) == {"abc-dep", "dep2", "dep3"}


def test_ruleset_select_multi_target() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets=[Path("abc"), "def"])(f)

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert rule.builder is f

    result = rules.select_rule("def")
    assert result is not None
    rule, deps, needs = result
    assert rule.builder is f


def test_ruleset_select_task_over_rules() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="abc")(f)

    def abc(target: str, depends: list[str], needs: list[str]) -> None:
        pass

    rules.task(abc)

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert rule.builder is abc


def test_ruleset_select_regex_literal() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="^ab.")(f)

    def abc(target: str, depends: list[str], needs: list[str]) -> None:
        pass

    rules.task(abc)

    result = rules.select_rule("abc")
    assert result is not None
    rule, deps, needs = result
    assert rule.builder is abc


def test_ruleset_select_default_target() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="abc")
    rules.rule(targets=re.compile("def"))
    rules.rule(targets="ghi", default=True)
    default = rules.select_default_target()
    assert default == "ghi"


def test_ruleset_select_default_error() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="abc", default=True)
    with pytest.raises(errors.RuleError):
        rules.rule(targets=re.compile("def"), default=True)
    with pytest.raises(errors.RuleError):
        rules.rule(targets=["a", "b"], default=True)


def test_ruleset_select_default_task() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets=re.compile("abc"))

    rules.task(f)

    default = rules.select_default_target()
    assert default == "f"


def test_ruleset_select_first_default_target() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets=re.compile("abc"))
    rules.rule(targets="def")
    rules.rule(targets="ghi")
    default = rules.select_default_target()
    assert default == "def"


def test_depgraph() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="a", depends=["a1", "a2"])(f)
    rules.rule(targets="a1", depends=["a2", "a3"])(f)
    rules.rule(targets="a2", depends=["a3", "a4"])(f)
    rules.rule(targets="a4", depends=["a5"])(f)

    g = depgraph.DepGraph()
    g.addtarget(rules, "a")

    assert g._nodes["a"].depends == ["a1", "a2"]
    assert g._nodes["a1"].depends == ["a2", "a3"]
    assert g._nodes["a2"].depends == ["a3", "a4"]
    assert g._nodes["a4"].depends == ["a5"]

    g.detectloop()


def test_depgraph_detectloop_simple() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="a", depends=["a1", "a2"])(f)
    rules.rule(targets="a1", depends=["a2"])(f)
    rules.rule(targets="a2", depends=["a1"])(f)

    g = depgraph.DepGraph()
    g.addtarget(rules, "a")

    with pytest.raises(errors.RuleError):
        g.detectloop()


def test_depgraph_detectloop() -> None:
    rules = ruledef.RuleSet()

    rules.rule(targets="a", depends=["a1", "a2"], needs=["n1", "n2"])(f)
    rules.rule(targets="a1", depends=["a2", "a3"])(f)
    rules.rule(targets="a2", depends=["a3", "a4"])(f)
    rules.rule(targets="a4", depends=["a5"])(f)

    g = depgraph.DepGraph()
    g.addtarget(rules, "a")

    g.detectloop()

    rules.rule(targets="a5", depends=["a2"])(f)
    g.addtarget(rules, "a5")

    with pytest.raises(errors.RuleError):
        g.detectloop()


def mtime(target: str) -> None:
    pass


def test_mtime() -> None:
    rules = ruledef.RuleSet()
    rules.mtime(targets="a")(mtime)
    assert mtime is rules.get_mtime_func(target="a")


def test_mtime_targets() -> None:
    rules = ruledef.RuleSet()
    rules.mtime(targets=["a", "b"])(mtime)
    assert mtime is rules.get_mtime_func(target="a")
    assert mtime is rules.get_mtime_func(target="b")


def test_mtime_regex() -> None:
    rules = ruledef.RuleSet()
    rules.mtime(targets="^.$")(mtime)
    assert mtime is rules.get_mtime_func(target="a")
    assert rules.default_get_file_mtime is rules.get_mtime_func(target="ab")


def test_mtime_default() -> None:
    rules = ruledef.RuleSet()
    assert rules.get_mtime_func(target="a") is rules.default_get_file_mtime
