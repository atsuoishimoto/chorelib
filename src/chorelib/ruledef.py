"""Core DSL definitions for build rules, tasks, and mtime functions.

This module provides the decorator-based DSL used to define build rules
(file-based targets with mtime checking), tasks (always-execute targets),
and custom mtime functions. Rules support regex patterns with backreferences
in dependencies.
"""

import logging
import os
import re
from collections.abc import Callable, Iterable
from pathlib import Path, PurePath
from re import Match, Pattern
from typing import Any, TypeAlias, Union

from .errors import RuleError
from .utils import flatten, to_timestamp, unique_list

logger = logging.getLogger(__name__)

TargetType: TypeAlias = Union[str, "Pattern[str]"]

TargetParamType: TypeAlias = Union[Path, TargetType]
TargetsParamType: TypeAlias = Union[
    TargetParamType, "list[Union[TargetParamType, TargetsParamType]]"
]

DepType: TypeAlias = Union[str, "Callable[..., Any]"]

DepParamType: TypeAlias = Union[DepType, Path]
DepsParamType: TypeAlias = Union[DepParamType, "list[Union[DepParamType, DepsParamType]]"]

BuilderFunc: TypeAlias = Callable[..., Any]
MTimeFunc: TypeAlias = Callable[[str], Any]


class RuleBase:
    """Base class for Rule and Task definitions."""

    depends: list[str | Callable[..., Any]]
    needs: list[str | Callable[..., Any]]
    doc: str | None
    builder: BuilderFunc | None
    default: bool
    is_static: bool = False
    targets: list[TargetType]

    def __init__(
        self,
        builder: BuilderFunc | None,
        depends: DepsParamType | None,
        needs: DepsParamType | None,
        default: bool = False,
        doc: str | None = None,
    ) -> None:
        """Initialize a RuleBase instance.
        Args:
            builder: The function that builds the target.
            target: A target name or pattern (str, Path, or Pattern).
            depends: An iterable of dependencies (str, Path, or Callable).
            needs: An iterable of order-only prerequisites where the order
                   matters but changes do not trigger rebuilds (str, Path, or Callable).
            default: Whether this rule is a default target.
            doc: Documentation string for the rule.
        """
        # todo: named-dependencies e.g. depends={'src': r'src/\1.c'}
        self.targets = []
        self.builder = builder
        self.depends = []
        if depends:
            for t in unique_list(flatten(depends)):
                match t:
                    case Path():
                        self.depends.append(str(t))
                    case str():
                        self.depends.append(t)
                    case _ if callable(t):
                        self.depends.append(t)
                    case _:
                        raise TypeError(f"Invalid depends: {t}")

        self.needs = []
        if needs:
            for t in unique_list(flatten(needs)):
                match t:
                    case Path():
                        self.needs.append(str(t))
                    case str():
                        self.needs.append(t)
                    case _ if callable(t):
                        self.needs.append(t)
                    case _:
                        raise TypeError(f"Invalid needs: {t}")

        self.default = default
        self.doc = doc

    def __repr__(self) -> str:
        """Return a string representation of the RuleBase instance."""
        return f"{type(self).__qualname__}: {self.builder}"

    def set_builder(self, builder: BuilderFunc) -> None:
        """Set the builder function for the rule."""
        self.builder = builder

    def _get_deps(self, match: Match[str]) -> tuple[list[str], list[str]]:
        """Get the dependencies and needs for a matched target."""

        def expand_dep(match: Match[str], dep: str | Callable[..., Any]) -> Any:
            """Expand a dependency based on its type."""
            if isinstance(dep, str):
                return match.expand(dep)
            elif isinstance(dep, PurePath):
                return str(dep)
            elif callable(dep):
                return list(str(d) for d in flatten(dep(self, match)))
            else:
                raise TypeError(f"Invalid dependency: {dep}")

        deps: list[str] = unique_list(flatten([expand_dep(match, dep) for dep in self.depends]))
        needs: list[str] = unique_list(flatten([expand_dep(match, need) for need in self.needs]))
        return deps, needs

    def match(self, target: str) -> tuple[list[str], list[str]] | None:
        """Match the target against the rule's targets and return dependencies."""
        for pattern in self.targets:
            if isinstance(pattern, Pattern):
                m = pattern.fullmatch(target)
                if m:
                    return self._get_deps(m)
            elif isinstance(pattern, str):
                m = re.fullmatch(re.escape(pattern), target)
                if m:
                    return self._get_deps(m)
        return None

    def run_builder(self, target: str, depends: list[str], needs: list[str]) -> Any:
        """Run the builder function for the rule.
        Returns a timestamp of the target."""
        if not self.builder:
            raise RuleError(f"No builder defined for {self}")
        ret = self.builder(target, depends, needs)
        return to_timestamp(ret)

    def get_doc(self) -> tuple[str | None, str | None]:
        """Get the documentation for the rule."""
        return None, None

    def get_descr(self) -> str:
        """Get a description string for the rule."""
        return ""


def _get_builder_name(builder: BuilderFunc | None) -> str:
    if not builder:
        return ""

    name = getattr(builder, "__qualname__", "")
    if not name:
        name = getattr(builder, "__name__", "")
    if not name:
        name = str(builder)
    return name


def _get_dep_name(dep: str | Callable[..., Any] | Pattern[str]) -> str:
    match dep:
        case Callable():
            return _get_builder_name(dep)
        case Pattern():
            return f"re: {dep.pattern}"
        case _:
            return str(dep)


def _compile_regex_literal(s: str) -> str | Pattern[str]:
    if len(s) >= 2 and s.startswith("^"):
        return re.compile(s)
    else:
        return s


class Rule(RuleBase):
    """A file-based build rule with mtime checking.

    Rules associate a target (file path or regex pattern) with a builder
    function that produces the target. The builder is invoked only when the
    target is missing or older than its dependencies.

    When the target is a regex ``Pattern``, the rule can match multiple
    targets and backreferences (e.g. ``\\1``) can be used in dependency
    specifications.
    """

    def __init__(
        self,
        builder: BuilderFunc | None,
        targets: TargetsParamType | None,
        depends: DepsParamType | None,
        needs: DepsParamType | None,
        default: bool = False,
        doc: str | None = None,
    ) -> None:
        super().__init__(
            builder=builder,
            depends=depends,
            needs=needs,
            default=default,
            doc=doc,
        )
        self.targets = []
        for target in flatten(targets):
            match target:
                case Pattern():
                    self.targets.append(target)
                case str():
                    self.targets.append(_compile_regex_literal(target))
                case Path():
                    self.targets.append(str(target))
                case _:
                    raise TypeError(f"Invalid target: {target}")

        # Static targets have a single, fixed string name (not a regex pattern)
        self.is_static = (len(self.targets) == 1) and all(
            isinstance(target, str) for target in self.targets
        )

        if default:
            if not self.is_static:
                raise RuleError(f"{self}: Only static targets (single string name) can be default")

    def __repr__(self) -> str:
        """Return a string representation of the Rule instance."""
        return f"{type(self).__qualname__}: {self.builder}: {self.targets}"

    def _get_target_name(self) -> str:
        """Get the name of the static target."""
        if isinstance(self.targets[0], str):
            return self.targets[0]
        return ""

    def _get_doc(self) -> str:
        """Return the documentation string, preferring the builder's docstring."""
        doc = ""
        if self.doc:
            doc = self.doc
        if self.builder and self.builder.__doc__:
            doc = self.builder.__doc__
        return doc.strip()

    def get_doc(self) -> tuple[str, str]:
        """Get the documentation for the rule."""
        doc = self._get_doc()
        name = self._get_target_name()
        return name, doc

    def get_descr(self) -> str:
        targets = ", ".join(_get_dep_name(t) for t in self.targets)
        depends = ", ".join(_get_dep_name(d) for d in self.depends)
        needs = ", ".join(_get_dep_name(n) for n in self.needs)
        builder = _get_builder_name(self.builder)

        return f"""[rule] {targets}:
  depends: {depends}
  needs: {needs}
  function: {builder}
"""


class Task(RuleBase):
    """An always-execute target, analogous to Make's .PHONY.

    Tasks run their builder every time they are requested, regardless of
    mtime comparisons. They are identified by name rather than file path.
    """

    name: str | None

    def __init__(
        self,
        builder: BuilderFunc | None,
        name: str | None,
        needs: DepsParamType | None,
        default: bool,
        doc: str | None = None,
    ) -> None:
        super().__init__(
            builder=builder,
            depends=[],
            needs=needs,
            default=default,
            doc=doc,
        )

        self.name = name
        if builder:
            self._set_funcname(builder)

    def set_builder(self, builder: BuilderFunc) -> None:
        """Set the builder function and derive the task name from it."""
        super().set_builder(builder)
        self._set_funcname(builder)

    def _set_funcname(self, f: BuilderFunc) -> None:
        """Set the task name from the function name if not explicitly given."""
        if not self.name:
            if not f.__name__ or f.__name__ == "<lambda>":
                raise RuleError("Task function should have a name. Use @task(name='name')")
            self.name = f.__name__
        self.targets = [self.name]

    def get_doc(self) -> tuple[str, str]:
        """Return the task name and its documentation string."""
        title = (self.name or "").strip()
        doc = ""
        if self.doc:
            doc = self.doc.strip()
        elif self.builder and self.builder.__doc__:
            doc = self.builder.__doc__.strip()
        return title, doc

    def run_builder(self, target: str, depends: list[str], needs: list[str]) -> int:
        """Execute the task's builder function.

        Returns -1 to indicate the target is always considered out-of-date.
        """
        if self.builder:
            self.builder()
        return -1

    def get_descr(self) -> str:
        needs = ", ".join(str(n) for n in self.needs)
        builder = _get_builder_name(self.builder)
        return f"""[task] {self.name}:
  needs: {needs}
  builder: {builder}
"""


class MTime:
    """Custom mtime function definition for a target pattern.

    By default, chorelib uses ``os.path.getmtime`` to check file
    modification times. MTime allows overriding this for specific targets,
    enabling mtime tracking for non-filesystem resources such as database
    rows or remote objects.
    """

    targets: list[TargetType]

    def __init__(
        self,
        targets: TargetParamType | Iterable[TargetParamType],
        mtime: MTimeFunc | None = None,
    ) -> None:
        self.targets = []
        for target in flatten(targets):
            match target:
                case Pattern():
                    self.targets.append(target)
                case Path():
                    self.targets.append(str(target))
                case str():
                    self.targets.append(_compile_regex_literal(target))
                case _:
                    raise TypeError(f"Invalid target: {target}")

        self.mtime = mtime

    def __repr__(self) -> str:
        """Return a string representation of the MTime instance."""
        return f"{type(self).__qualname__}: {self.mtime} {self.targets}"

    def set_mtime(self, mtime: MTimeFunc) -> None:
        """Set the mtime callback function."""
        self.mtime = mtime

    def match(self, target: str) -> Match[str] | None:
        """Check if a target name matches this MTime definition.

        Returns:
            A regex match object if matched, or None.
        """
        for pattern in self.targets:
            if isinstance(pattern, Pattern):
                m = pattern.fullmatch(target)
                if m:
                    return m
            elif isinstance(pattern, str):
                m = re.fullmatch(re.escape(pattern), target)
                if m:
                    return m
        return None


class RuleSet:
    """A collection of rules, tasks, and mtime definitions.

    RuleSet provides decorator methods (``rule``, ``task``, ``mtime``) for
    registering build rules. It also handles target matching and default
    target selection.
    """

    def __init__(self) -> None:
        self.rules: list[RuleBase] = []
        self.mtimes: list[MTime] = []

    def rule(
        self,
        targets: TargetsParamType | None,
        *,
        depends: DepsParamType | None = None,
        needs: DepsParamType | None = None,
        default: bool = False,
        doc: str | None = None,
    ) -> Callable[[BuilderFunc], BuilderFunc]:
        """Decorator to register a file-based build rule.

        Args:
            targets: Target file path(s) or regex pattern(s). Accepts a single
                value or arbitrarily nested lists — nested lists are
                recursively flattened. Each element can be a ``str``,
                ``Path``, or compiled ``re.Pattern``. A string starting
                with ``^`` is automatically compiled as a regex.
            depends: Dependencies that trigger rebuilds when newer than the
                target. Accepts a single value or arbitrarily nested
                lists — nested lists are recursively flattened. Each
                element can be a ``str``, ``Path``, or callable.
                Backreferences (``\\1``, ``\\2``) are expanded against
                the regex match when the target is a pattern.
            needs: Order-only prerequisites (built first but do not trigger
                rebuilds). Accepts the same types as *depends* and is
                also recursively flattened.
            default: If True, use this target when no targets are specified.
            doc: Documentation string for the rule.

        Returns:
            A decorator that registers the decorated function as the builder.
        """
        rule = Rule(
            builder=None,
            targets=targets,
            depends=depends,
            needs=needs,
            default=default,
            doc=doc,
        )
        self.rules.append(rule)

        def deco(f: BuilderFunc) -> BuilderFunc:
            rule.set_builder(f)
            return f

        return deco

    def task(
        self,
        name_or_func: str | BuilderFunc | None = None,
        *,
        needs: DepsParamType | None = None,
        default: bool = False,
        doc: str | None = None,
    ) -> BuilderFunc | Callable[[BuilderFunc], BuilderFunc]:
        """Decorator to register a task (always-execute target).

        Can be used with or without arguments::

            @ruleset.task
            def clean():
                ...

            @ruleset.task("build", needs="setup")
            def build_all():
                ...

        Args:
            name_or_func: Task name (str) or the function itself
                (when used without arguments).
            needs: Order-only prerequisites. Accepts a single value or
                arbitrarily nested lists — nested lists are recursively
                flattened. Each element can be a ``str``, ``Path``, or
                callable.
            default: If True, use this task when no targets are specified.
            doc: Documentation string for the task.

        Returns:
            A decorator or the original function if called without arguments.
        """
        name: str | None
        func: BuilderFunc | None
        if isinstance(name_or_func, str):
            name = name_or_func
            func = None
        else:
            name = None
            func = name_or_func

        task = Task(
            builder=None,
            name=name,
            needs=needs,
            default=default,
            doc=doc,
        )
        self.rules.append(task)

        if func:
            task.set_builder(func)
            return func

        def deco(f: BuilderFunc) -> BuilderFunc:
            task.set_builder(f)
            return f

        return deco

    def mtime(
        self,
        targets: TargetParamType | Iterable[TargetParamType],
        mtime: MTimeFunc | None = None,
    ) -> Callable[[MTimeFunc], MTimeFunc]:
        """Decorator to register a custom mtime function for targets.

        Args:
            targets: Target name(s) or regex pattern(s) to match. Accepts
                a single value or arbitrarily nested lists — nested lists
                are recursively flattened. Each element can be a ``str``,
                ``Path``, or compiled ``re.Pattern``. A string starting
                with ``^`` is automatically compiled as a regex.
            mtime: Optional mtime function. If None, the decorated
                function is used.

        Returns:
            A decorator that registers the decorated function as the
            mtime callback.
        """
        mtimedef = MTime(targets=targets, mtime=mtime)
        self.mtimes.append(mtimedef)

        def deco(f: MTimeFunc) -> MTimeFunc:
            mtimedef.set_mtime(f)
            return f

        return deco

    def select_rule(self, target: str) -> tuple[RuleBase, list[str], list[str]] | None:
        """Select a rule that matches the target."""
        has_builder: RuleBase | None = None
        deps: list[str] = []
        needs: list[str] = []
        for rule in self.rules:
            logger.debug(f"Checking rule {rule} for target '{target}'")

            if not rule.builder:
                logger.warning(f"Skipping rule {rule} for target '{target}' (no builder)")
                continue

            ret = rule.match(target)
            if ret:
                if isinstance(rule, Task):
                    logger.debug(f"Matched task {rule} for target '{target}'")
                    return rule, ret[0], ret[1]

                if rule.builder is not None:
                    logger.debug(f"Found {rule} for target '{target}'")
                    if not has_builder:
                        has_builder = rule
                        deps, needs = ret

        if has_builder:
            logger.debug(f"Matched {has_builder} for target '{target}'")
            return has_builder, deps, needs
        else:
            logger.debug(f"No rule found for target '{target}'")
            return None

    def select_default_target(self) -> TargetType | None:
        """Select default targets from the rules."""

        first: TargetType | None = None
        for rule in self.rules:
            if rule.default:
                logger.debug(f"Selected default target: {rule}")
                if isinstance(rule, Task):
                    return rule.name
                else:
                    return rule.targets[0]

            if not first:
                if isinstance(rule, Task):
                    first = rule.name
                elif rule.is_static:
                    first = rule.targets[0]

        logger.debug(f"Selected default target: {first}")
        return first

    def get_target_names(self) -> list[TargetType | None]:
        """Return a list of all static target names and task names."""
        ret: list[TargetType | None] = []
        for rule in self.rules:
            if isinstance(rule, Task):
                ret.append(rule.name)
            elif rule.is_static:
                ret.append(rule.targets[0])
        return ret

    def _select_mtime(self, target: str) -> MTime | None:
        """Select an mtime funcion that matches the target."""
        for mtime in self.mtimes:
            logger.debug(f"Checking mtime {mtime} for target '{target}'")
            if mtime.match(target):
                logger.debug(f"Found mtime {mtime} for target '{target}'")
                return mtime
        logger.debug(f"No mtime found for target '{target}'")
        return None

    @staticmethod
    def default_get_file_mtime(name: str) -> Any:
        """default function to get file modification time on local filesystem."""
        return os.path.getmtime(name)

    def get_mtime_func(self, target: str) -> MTimeFunc:
        """Get the mtime function for the target."""
        mtime = self._select_mtime(target)
        if not mtime or not mtime.mtime:
            return self.default_get_file_mtime
        return mtime.mtime

    def get_docs(self) -> list[tuple[str | None, str | None]]:
        """Return documentation for all named rules and tasks.

        Returns:
            A list of (title, doc) tuples for rules with non-empty titles.
        """
        default = self.select_default_target() or ""
        ret: list[tuple[str | None, str | None]] = []
        for rule in self.rules:
            title, doc = rule.get_doc()
            if title:
                if default and default == title:
                    title += " [default]"
                ret.append((title, doc))
        return ret
