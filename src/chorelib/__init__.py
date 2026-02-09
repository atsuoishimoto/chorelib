"""Chorelib: An async-first Python build automation framework.

Provides a decorator-based DSL for defining build rules and tasks with
dependency management, parallel execution, and mtime-based rebuild detection.

Typical usage::

    import chorelib

    @chorelib.rule("output.txt", depends="input.txt")
    def build_output(target, depends, needs):
        chorelib.shell(f"cp {depends[0]} {target}")

    if __name__ == "__main__":
        chorelib.Main().run()
"""

from .depmain import Main
from .deprunner import schedule
from .ruledef import RuleSet
from .utils import command, message, shell

__version__ = "0.1.1"

# Default RuleSet instance used by the module-level decorators.
# Users can use `@chorelib.rule(...)` and `@chorelib.task` directly
# without creating a RuleSet manually.
_default_rules = RuleSet()
rule = _default_rules.rule
task = _default_rules.task
mtime = _default_rules.mtime

# Global verbosity level controlling message output.
# 0 = normal, 1 = verbose, 2 = debug messages, 3+ = logging debug.
verbose: int = 0

__all__ = [
    "RuleSet",
    "rule",
    "task",
    "mtime",
    "Main",
    "schedule",
    "verbose",
    "command",
    "message",
    "shell",
]
