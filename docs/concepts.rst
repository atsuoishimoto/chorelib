Concepts
========

This page explains chorelib's core concepts and design decisions.

Rule vs Task
------------

chorelib has two kinds of build targets:

**Rule** (``@rule``)
   A file-based target with mtime checking. The builder runs only when the
   target is missing or older than its dependencies. Rules associate a target
   name (or regex pattern) with a builder function.

   .. code-block:: python

      @rule("output.txt", depends="input.txt")
      def build(target, depends, needs):
          shell("cp", depends[0], target)

   The builder function receives three arguments:

   - ``target`` — the target file name (``str``)
   - ``depends`` — list of dependency file names (``list[str]``)
   - ``needs`` — list of order-only prerequisite names (``list[str]``)

**Task** (``@task``)
   An always-execute target, analogous to Make's ``.PHONY``. Tasks run their
   builder every time they are requested, regardless of mtime. They are
   identified by name (derived from the function name or explicitly given).

   .. code-block:: python

      @task
      def clean():
          shell("rm -f output.txt")

   Task builders take no arguments. Tasks cannot have ``depends`` — they only
   support ``needs`` for ordering.

depends vs needs
----------------

Both ``depends`` and ``needs`` express that one target requires another to be
built first. The critical difference is whether changes trigger a rebuild:

**depends**
   A dependency that triggers rebuilds. If any dependency is newer than the
   target (based on mtime comparison), the target is rebuilt.

   .. code-block:: python

      @rule("app.js", depends=["main.js", "util.js"])
      def bundle(target, depends, needs):
          ...

**needs**
   An order-only prerequisite. The needed target is built before the current
   target, but its mtime is *not* compared. Changes to a ``needs`` target do
   not trigger a rebuild.

   .. code-block:: python

      @rule("build/output.html", depends="input.md", needs="build")
      def convert(target, depends, needs):
          ...

   Common use case: ensuring a directory exists before writing files into it.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Property
     - ``depends``
     - ``needs``
   * - Build order
     - Built first
     - Built first
   * - Triggers rebuild
     - Yes (mtime comparison)
     - No
   * - Typical use
     - Source files, headers
     - Directories, setup tasks

Automatic Flattening of Parameters
-----------------------------------

Parameters that accept sequences — ``targets``, ``depends``, ``needs``, and
the ``*cmd`` arguments of ``shell()`` / ``command()`` — automatically flatten
arbitrarily nested lists. This means you never need to manually concatenate or
unpack lists when composing dependencies.

For example, you can mix single values and nested lists freely:

.. code-block:: python

   HEADERS = ["hello.h", "config.h"]
   LIBS = ["libfoo.a", "libbar.a"]

   @rule("app", depends=[HEADERS, LIBS, "main.c"])
   def build(target, depends, needs):
       ...

   # depends is flattened to:
   # ["hello.h", "config.h", "libfoo.a", "libbar.a", "main.c"]

The same applies to ``shell()`` and ``command()``:

.. code-block:: python

   CFLAGS = ["-O2", "-Wall"]

   command("gcc", CFLAGS, "-o", target, depends)
   # Executed as: gcc -O2 -Wall -o app hello.h config.h ...

Strings are treated as atomic values (not iterated character by character),
and ``None`` values are silently ignored.

This design eliminates boilerplate list operations like ``[*A, *B, c]`` or
``A + B + [c]``, keeping build scripts concise and readable. The flattening
is performed by ``chorelib.utils.flatten()``.

Regex Target Patterns
---------------------

Target names can be regex patterns, allowing a single rule to match many
targets. There are two ways to specify a regex target:

1. **Compiled pattern**: Pass a ``re.compile()`` object.

   .. code-block:: python

      @rule(re.compile(r"(.+)\.o"), depends=r"\1.c")
      def compile(target, depends, needs):
          ...

2. **String starting with** ``^``: Strings that start with ``^`` are
   automatically compiled as regex patterns.

   .. code-block:: python

      @rule(r"^(.+)\.o", depends=r"\1.c")
      def compile(target, depends, needs):
          ...

Backreferences (``\1``, ``\2``, etc.) in ``depends`` and ``needs`` are expanded
using the regex match. Named groups (``(?P<name>...)``) are also supported.

Pattern matching uses ``re.fullmatch()`` — the pattern must match the entire
target name.

mtime-Based Rebuild Detection
------------------------------

chorelib decides whether to rebuild a target by comparing modification times:

1. If the target does not exist, it is built.
2. If any ``depends`` dependency is newer than the target, it is rebuilt.
3. Otherwise, the target is up to date and skipped.

This is the same logic Make uses, applied through Python's ``os.path.getmtime``.

Use ``-r`` (``--rebuild``) to force all targets to rebuild regardless of mtime.

Custom mtime Functions
----------------------

The ``@mtime`` decorator overrides the default ``os.path.getmtime`` for
targets matching a pattern. This enables chorelib to manage non-filesystem
resources.

.. code-block:: python

   @mtime(re.compile(r"^s3://.*"))
   def s3_mtime(target):
       # Return a numeric timestamp, datetime, or None
       ...

The mtime function should:

- Return a numeric timestamp (``float``) or ``datetime`` object if the target exists.
- Return ``None`` if the target does not exist (this triggers a build).

When a ``datetime`` is returned, naive datetimes (without timezone info) are
treated as UTC. Timezone-aware datetimes are converted to timestamps
automatically.

Multiple ``@mtime`` decorators can coexist. The first one whose pattern matches
a given target is used.

Dependency Graph and Cycle Detection
-------------------------------------

Before any build execution, chorelib constructs a dependency graph (DAG) from
all requested targets and their transitive dependencies. It then performs a
depth-first search to detect circular dependencies.

If a cycle is detected, a ``RuleError`` is raised immediately — before any
builder runs.

.. code-block:: text

   A depends on B
   B depends on C
   C depends on A  ← cycle detected → RuleError

Parallel Execution Model
-------------------------

chorelib uses Python's ``asyncio`` event loop with a ``ThreadPoolExecutor`` to
run builder functions in parallel:

- The dependency graph determines the execution order.
- Targets with no dependency relationship run concurrently.
- The ``-w N`` flag controls the maximum number of parallel workers.
- ``-w 1`` (default) runs builders sequentially.

Builder functions run in worker threads via the executor, while dependency
resolution and scheduling happen on the asyncio event loop thread.

schedule()
----------

``schedule()`` allows builder functions to dynamically add new targets to the
running build:

.. code-block:: python

   from chorelib import schedule

   @task
   def discover():
       targets = find_targets()
       schedule(targets)

``schedule()`` is thread-safe — it works correctly from both the event loop
thread and worker threads. Internally, when called from a worker thread, it
uses ``asyncio.run_coroutine_threadsafe()`` to safely interact with the event
loop.

RuleSet
-------

A ``RuleSet`` is a collection of rules, tasks, and mtime definitions. chorelib
provides a default ``RuleSet`` instance that powers the module-level
``@rule``, ``@task``, and ``@mtime`` decorators:

.. code-block:: python

   import chorelib

   # These use the default RuleSet
   @chorelib.rule("output.txt", depends="input.txt")
   def build(target, depends, needs):
       ...

For advanced use cases (e.g., composing multiple independent build configurations),
you can create your own ``RuleSet``:

.. code-block:: python

   from chorelib import RuleSet, Main

   rules = RuleSet()

   @rules.rule("output.txt", depends="input.txt")
   def build(target, depends, needs):
       ...

   if __name__ == "__main__":
       Main(rules).run()
