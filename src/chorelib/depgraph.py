"""Dependency graph construction and cycle detection.

Builds a directed acyclic graph (DAG) of build targets and their
dependencies. Detects circular dependencies via depth-first search
before any build execution begins.
"""

from collections.abc import Sequence
from typing import Any

from .errors import RuleError
from .ruledef import RuleBase, RuleSet, Task


class BuildInfo:
    """A node in the dependency graph representing a single build target.

    Attributes:
        target: The target name (file path or task name).
        rule: The Rule or Task that produces this target.
        depends: List of dependency target names that trigger rebuilds.
        needs: List of order-only prerequisite target names.
    """

    def __init__(
        self, target: str, rule: RuleBase, depends: Sequence[str], needs: Sequence[str]
    ) -> None:
        self.rule = rule
        self.target = target
        self.depends = depends
        self.needs = needs

    def __repr__(self) -> str:
        return f"<BuildInfo> {self.rule}:{self.target}:{self.depends}:{self.needs}"

    def is_task(self) -> bool:
        """Return True if this node represents a Task (always-execute)."""
        return isinstance(self.rule, Task)

    def run_builder(self) -> Any:
        """Execute the builder function for this target."""
        return self.rule.run_builder(target=self.target, depends=self.depends, needs=self.needs)


class DepGraph:
    """Dependency graph that manages BuildInfo nodes and detects cycles.

    Nodes are registered by recursively resolving each target's dependencies
    through the RuleSet. After registration, ``detectloop`` should be called
    to verify the graph is acyclic.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, BuildInfo] = {}

    def addtarget(self, ruleset: RuleSet, target: str) -> bool:
        """Add a target and all its transitive dependencies to the graph.

        Returns:
            True if the target was newly registered, False if already present.
        """
        return self._register(ruleset, target)

    def get(self, target: str) -> BuildInfo | None:
        """Return the BuildInfo node for a target, or None if not registered."""
        return self._nodes.get(target)

    def _register(self, ruleset: RuleSet, target: str) -> bool:
        """Recursively register a target and its dependencies.

        Looks up the matching rule in the ruleset, creates a BuildInfo node,
        and recurses into each dependency and need.
        """
        if target in self._nodes:
            return False

        ret = ruleset.select_rule(target)
        if ret:
            rule, deps, needs = ret
            node = BuildInfo(target, rule, deps, needs)
            self._nodes[target] = node

            # Recursively register all dependencies
            for dep in deps:
                self._register(ruleset, dep)

            # Recursively register all order-only prerequisites
            for need in needs:
                self._register(ruleset, need)

        return True

    def detectloop(self) -> None:
        """Detect circular dependencies in the graph using DFS.

        Raises:
            RuleError: If a dependency cycle is found.
        """
        done: set[BuildInfo] = set()

        def _walk(node: BuildInfo, seen: set[BuildInfo]) -> None:
            """DFS traversal tracking the current path in ``seen``."""
            if node in seen:
                raise RuleError(f"Dependency cycle detected: {node}")

            if node in done:
                return

            seen.add(node)
            try:
                for dep in node.depends:
                    depnode = self._nodes.get(dep)
                    if depnode:
                        _walk(depnode, seen)
                for need in node.needs:
                    neednode = self._nodes.get(need)
                    if neednode:
                        _walk(neednode, seen)
            finally:
                seen.remove(node)
            done.add(node)

        for node in self._nodes.values():
            seen: set[BuildInfo] = set()
            _walk(node, seen)
