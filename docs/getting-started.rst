Getting Started
===============

Installation
------------

Install chorelib from PyPI:

.. code-block:: bash

   pip install chorelib

Or with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: bash

   uv add chorelib

chorelib requires Python 3.10 or later and has zero runtime dependencies.

Quick Start
-----------

Create a file called ``make.py``:

.. code-block:: python

   from chorelib import Main, rule, shell, task

   main = Main()
   SOURCES = ["a.txt", "b.txt", "c.txt"]

   @rule("output.txt", depends=SOURCES, default=True)
   def build(target, depends, needs):
       """Build output.txt from source files."""
       shell("cat", depends, ">", target)

   @task
   def clean():
       """Remove generated files."""
       shell("rm -f output.txt")

   if __name__ == "__main__":
       main.run()

Run it:

.. code-block:: bash

   python make.py              # Build the default target
   python make.py clean        # Run the clean task
   python make.py -w 4         # Build with 4 parallel workers
   python make.py -r           # Force rebuild all targets
   python make.py -h           # Show help with target docs
   python make.py -l           # List all available targets

Comparison with Make
--------------------

Here is a Makefile and its chorelib equivalent side by side.

**Makefile:**

.. code-block:: makefile

   CC=gcc
   CFLAGS=-I.
   DEPS = hello.h
   OBJS = main.o hello.o
   .PHONY: clean

   %.o: %.c $(DEPS)
   	$(CC) -c -o $@ $< $(CFLAGS)

   hello.exe: $(OBJS)
   	$(CC) -o $@ $^

   clean:
   	rm -f $(OBJS) hello.exe

**chorelib (make.py):**

.. code-block:: python

   import re
   from chorelib import Main, command, rule, task

   main = Main()
   APP = "hello.exe"
   CC = "gcc"
   CFLAGS = ["-c", "-I."]
   DEPS = ["hello.h"]
   OBJS = ["hello.o", "main.o"]

   @rule(APP, depends=OBJS, default=True)
   def link(target, deps, needs):
       """Build executable"""
       command(CC, "-o", target, deps)

   @rule(re.compile(r"(.+)\.o"), depends=(r"\1.c", DEPS))
   def compile(target, deps, needs):
       command(CC, "-o", target, deps[0], CFLAGS)

   @task
   def clean():
       """Remove the built files."""
       command("rm", "-f", OBJS, APP)

   if __name__ == "__main__":
       main.run()

Why chorelib over Make?
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - Make
     - chorelib
   * - Pattern rules
     - ``%.o: %.c``
     - ``r"^(.+)\.o"`` with backreferences
   * - Variables & logic
     - Limited macro language
     - Full Python
   * - Parallel builds
     - ``make -j4``
     - ``python make.py -w 4``
   * - Non-file targets
     - ``.PHONY``
     - ``@task`` decorator
   * - Custom mtime
     - Not supported
     - ``@mtime`` decorator for databases, S3, etc.
   * - Dependencies
     - File-only
     - Files, functions, or any callable

Command-Line Options
--------------------

All chorelib build scripts support these options via the ``Main`` class:

.. option:: -h, --help

   Show help message with target documentation extracted from docstrings.

.. option:: -C DIRECTORY

   Change to DIRECTORY before performing any operations.

.. option:: -w WORKERS

   Allow up to N workers to run simultaneously (default: 1).

.. option:: -r, --rebuild

   Force rebuild all targets regardless of mtime.

.. option:: -l, --list-targets

   List all registered targets with their types, dependencies, and builders.

.. option:: -v

   Increase verbosity level. Can be repeated (``-vv``, ``-vvv``).

.. option:: -V, --version

   Show version information.
