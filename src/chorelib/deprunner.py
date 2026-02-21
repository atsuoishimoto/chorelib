"""Asynchronous build runner with parallel execution support.

Executes build targets based on the dependency graph, comparing mtimes
to skip up-to-date targets. Builder functions run in a ThreadPoolExecutor
for parallelism.
"""

import asyncio
import errno
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import get_ident, local
from typing import Any, Sequence

from .depgraph import BuildInfo, DepGraph
from .errors import RuleNotFoundError, TargetNotFoundError
from .ruledef import MTimeFunc, RuleSet
from .utils import message, to_timestamp

logger = logging.getLogger(__name__)


class Runner:
    """Asynchronous build runner that manages building targets based on dependencies.

    Coordinates the build process: resolves the dependency graph, compares
    mtimes to determine what needs rebuilding, and executes builder functions
    in parallel using a ThreadPoolExecutor.

    Attributes:
        rules: The RuleSet containing all rule, task, and mtime definitions.
        graph: The DepGraph tracking registered targets.
        build_tasks: Dict mapping target names to their asyncio Tasks.
        skipped_targets: Set of targets that were up-to-date and skipped.
        build_always: If True, rebuild all targets regardless of mtime.
    """

    def __init__(
        self, rules: RuleSet, num_workers: int | None = 0, build_always: bool = False
    ) -> None:
        self.loop = asyncio.get_event_loop()
        self.threadid = get_ident()
        self.running = False
        self.num_workers = num_workers
        self.build_always = build_always

        self.rules = rules
        self.graph = DepGraph()
        self.build_tasks: dict[str, asyncio.Task[Any]] = {}
        self.skipped_targets: set[str] = set()

        logger.debug(
            f"Initializing Runner with num_workers={self.num_workers}, "
            f"build_always={self.build_always}"
        )

        # Use a thread pool for parallel builds when multiple workers requested
        self.executor: ThreadPoolExecutor | None = None
        if self.num_workers is None or self.num_workers > 1:
            self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

    async def _run_in_executor(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Run a function in the thread pool executor, or inline if single-threaded.

        Sets up thread-local state so that ``schedule()`` can find the
        active runner from within builder functions.
        """

        def wrapper() -> Any:
            if getattr(_runner, "running", None):
                raise RuntimeError(f"Nested calls to _run_in_executor are not allowed: {func}")

            _runner.running = self
            try:
                logger.debug(f"Running {func} in executor")
                return func(*args, **kwargs)
            finally:
                _runner.running = None

        if self.executor:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, wrapper)
        else:
            return func(*args, **kwargs)

    async def _get_mtime(self, mtimefunc: MTimeFunc, target: str) -> Any:
        """Retrieve the mtime of a target using its mtime function.

        Raises:
            TargetNotFoundError: If the mtime function returns None
                (target does not exist).
        """
        message(f"Running mtime function {mtimefunc} for target: {target}", 2)
        ret = await self._run_in_executor(mtimefunc, target)
        ret = to_timestamp(ret)
        if ret is None:
            raise TargetNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), target)
        return ret

    async def _run_build_deps(self, node: BuildInfo, build_always: bool) -> Any | None:
        """Build dependencies of the node and return the latest timestamp among them."""
        deps = [self._ensure_target(t, build_always) for t in node.depends]
        needs = [self._ensure_target(t, False) for t in node.needs]
        dep_timestamps: list[Any] = list(await asyncio.gather(*deps))
        await asyncio.gather(*needs)
        if dep_timestamps:
            return max(dep_timestamps)
        else:
            # No dependencies
            return None

    async def _run_builder(self, node: BuildInfo) -> Any:
        """Run the builder function for the node."""
        logger.debug(f"Starting {node.run_builder} for `{node.target}`")
        ts = await self._run_in_executor(node.run_builder)
        timestamp = to_timestamp(ts)
        if timestamp is None:
            timestamp = time.time()
        return timestamp

    @staticmethod
    def default_get_file_mtime(name: str) -> Any:
        """default function to get file modification time on local filesystem."""
        return os.path.getmtime(name)

    async def _build_target(self, target: str, build_always: bool) -> Any:
        """Build a single target and return its timestamp.

        For tasks or forced rebuilds, the builder runs unconditionally.
        For rules, the target's mtime is compared against its dependencies'
        mtimes to decide whether a rebuild is needed.
        """
        message(f"Building target: {target}", 1)

        if not self.running:
            return None

        node = self.graph.get(target)

        # Tasks and forced rebuilds always execute the builder
        if node and (build_always or node.is_task()):
            await self._run_build_deps(node, build_always)
            timestamp = await self._run_builder(node)
            return timestamp

        # Check the current mtime of the target
        mtimefunc = self.rules.get_mtime_func(target)
        timestamp_or_none: Any
        try:
            timestamp_or_none = await self._get_mtime(mtimefunc, target)
        except (FileNotFoundError, TargetNotFoundError) as e:
            message(f"File not found for target '{target}': {e!s}", 2)
            if not node:
                # No builder defined for this target
                raise RuleNotFoundError(target) from e
            timestamp_or_none = None

        if node:
            # Build dependencies and compare mtimes
            dep_timestamp = await self._run_build_deps(node, build_always)
            if (timestamp_or_none is None) or (
                (dep_timestamp is not None) and (timestamp_or_none < dep_timestamp)
            ):
                # Target is missing or older than dependencies — rebuild
                message(f"Start building '{target}'", 2)
                timestamp_or_none = await self._run_builder(node)
            else:
                self.skipped_targets.add(target)
                message(f"Skipping build for target '{target}'; up to date.", 1)

        return timestamp_or_none

    def _ensure_target(self, target: str, build_always: bool) -> asyncio.Task[Any]:
        """Ensure that the target is built and return its timestamp."""
        task = self.build_tasks.get(target)
        if not task:
            task = asyncio.create_task(self._build_target(target, build_always))
            task.set_name(target)
            self.build_tasks[target] = task
        return task

    def _addtargets(self, targets: Sequence[str]) -> list[str]:
        """Add targets to the build graph."""
        added: list[str] = []
        for target in targets:
            if self.graph.addtarget(self.rules, target):
                added.append(target)

        if added:
            self.graph.detectloop()

        for target in added:
            self._ensure_target(target, self.build_always)

        return added

    async def wait_until_done(self) -> None:
        """Wait until all registered build tasks have completed."""
        seen: set[str] = set()
        try:
            while True:
                tasks = {
                    target: task for target, task in self.build_tasks.items() if target not in seen
                }
                if not tasks:
                    break
                seen.update(tasks.keys())
                await asyncio.gather(*(tasks.values()))
        except Exception:
            self.running = False
            for task in self.build_tasks.values():
                task.cancel()
            raise

    async def run(self, targets: Sequence[str]) -> None:
        """Run the build for the specified targets."""
        self.running = True
        _runner.running = self
        self.skipped_targets = set()

        # start building
        self._addtargets(targets)
        await self.wait_until_done()

        for target in targets:
            if target in self.skipped_targets:
                message(f"{target!r} is up to date.")
            else:
                message(f"Nothing to be done for {target!r}")


# Thread-local storage for tracking the active Runner instance.
# Used by schedule() to find the runner from within builder functions.
_runner = local()


def schedule(*targets: str) -> None:
    """Dynamically add new targets to the running build from within a builder.

    This function can be called from a builder function to request that
    additional targets be built. It is thread-safe and works from both
    the event loop thread and worker threads.

    Args:
        targets: A list of target names to schedule for building.

    Raises:
        RuntimeError: If no build runner is currently active.
    """
    runner: Runner | None = getattr(_runner, "running", None)
    if not runner:
        raise RuntimeError("No build runner is running.")

    if runner.threadid != get_ident():
        # Called from a worker thread — schedule via the event loop
        async def _schedule_targets() -> None:
            runner._addtargets(targets)

        fut = asyncio.run_coroutine_threadsafe(_schedule_targets(), runner.loop)
        fut.result()
    else:
        # Called from the event loop thread directly
        runner._addtargets(targets)


async def run(
    rules: RuleSet,
    targets: Sequence[str],
    num_workers: int | None = 0,
    rebuild: bool = False,
) -> None:
    """Run the build process for the specified targets.

    Args:
        rules: The RuleSet containing rule, task, and mtime definitions.
        targets: A list of target names to build.
        num_workers: Maximum number of parallel worker threads.
            0 or 1 for single-threaded, None for unlimited.
        rebuild: If True, rebuild all targets regardless of mtime.
    """
    runner = Runner(rules, num_workers=num_workers, build_always=rebuild)
    await runner.run(targets)
