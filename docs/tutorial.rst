Tutorial
========

This tutorial walks through chorelib's features step by step, from basic rules
to advanced patterns like custom mtime functions and dynamic dependencies.

Your First Build Script
-----------------------

The simplest chorelib script defines a rule and runs it. A **rule** describes
how to produce a target file from its dependencies.

.. code-block:: python

   # gen-doc.py
   from chorelib import Main, rule, shell, task

   SRCFILES = ["a.txt", "b.txt", "c.txt"]
   COMMON = ["inc1.txt", "inc2.txt"]

   @rule("DOC.txt", depends=[SRCFILES, COMMON], default=True)
   def generate(target, depends, needs):
       """Generate DOC.txt from source files."""
       shell("cat", depends, ">", target)

   @task
   def clean():
       """Remove generated files."""
       shell("rm -f DOC.txt")

   if __name__ == "__main__":
       Main().run()

Key points:

- ``@rule("DOC.txt", depends=..., default=True)`` declares that ``DOC.txt`` is
  built from the listed source files. ``default=True`` makes it the target when
  none is specified on the command line.
- The builder function receives three arguments: ``target`` (the target name),
  ``depends`` (list of dependency names), and ``needs`` (list of order-only prerequisites).
- ``shell()`` executes a command through the system shell. Nested lists in
  arguments are automatically flattened.
- ``@task`` defines an always-execute target (like Make's ``.PHONY``). Tasks take
  no arguments and run every time they are requested.

Run the script:

.. code-block:: bash

   python gen-doc.py          # Build DOC.txt
   python gen-doc.py          # Run again — skipped because DOC.txt is up to date
   python gen-doc.py clean    # Remove DOC.txt

Regex Patterns and Backreferences
---------------------------------

When you have many targets that follow the same pattern (e.g., compiling ``.c``
files to ``.o`` files), you can use a regex pattern as the target:

.. code-block:: python

   import re
   from chorelib import Main, command, rule, task

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
       Main().run()

How it works:

- ``re.compile(r"(.+)\.o")`` matches any ``.o`` file. The capture group ``(.+)``
  captures the stem (e.g., ``main`` from ``main.o``).
- ``r"\1.c"`` in ``depends`` is a backreference — it expands to the captured
  group, so ``main.o`` depends on ``main.c``.
- ``command()`` executes a program directly without a shell, which is safer than
  ``shell()`` because it avoids shell injection.

.. tip::

   You can also use a string starting with ``^`` as a shorthand for regex:
   ``r"^(.+)\.o"`` is equivalent to ``re.compile(r"^(.+)\.o")``. Note that
   ``re.compile()`` without ``^`` performs a full match on the entire target name.

Named Capture Groups
^^^^^^^^^^^^^^^^^^^^

For more complex patterns, use named capture groups:

.. code-block:: python

   import re
   from chorelib import rule

   @rule(re.compile(r"(?P<REGION>[^.]+)\.jpeg"), depends=get_region_files)
   def build_banner(target, depends, needs):
       ...

The match object is passed to callable dependencies, so ``get_region_files``
can access ``match.group("REGION")`` to determine which files to include.

Callable Dependencies
^^^^^^^^^^^^^^^^^^^^^

Dependencies can be functions that are called at build time to dynamically
determine the actual dependency list:

.. code-block:: python

   import re
   from pathlib import Path
   from chorelib import rule

   def get_region_files(rule, match):
       """Return flag PNG files for the matched region."""
       region = match.group("REGION")
       return sorted(Path(f"flags/{region}").glob("*.png"))

   @rule(re.compile(r"(?P<REGION>[^.]+)\.jpeg"), depends=get_region_files)
   def build_banner(target, depends, needs):
       ...

The callable receives two arguments:

- ``rule`` — the Rule object
- ``match`` — the regex match object for the target

It should return an iterable of dependency names (strings or Paths).

Order-Only Prerequisites (needs)
--------------------------------

Sometimes you need a dependency to be built *before* your target, but you don't
want changes to that dependency to trigger a rebuild. Use ``needs`` for this:

.. code-block:: python

   BUILD = "build"

   @rule(re.compile(rf"^{BUILD}/(.+)\.html"), depends=r"\1.md", needs=BUILD)
   def md_to_html(target, depends, needs):
       """Convert Markdown to HTML."""
       ...

   @rule(BUILD)
   def make_build_dir(target, depends, needs):
       """Create build directory."""
       command("mkdir", "-p", target)

Here, the ``build`` directory must exist before HTML files are generated, but
creating or modifying the directory should not cause all HTML files to be
rebuilt. The ``needs`` parameter achieves exactly this.

- ``depends`` — triggers a rebuild when the dependency is newer than the target
- ``needs`` — ensures build order only; changes do not trigger rebuilds

Custom mtime Functions
----------------------

By default, chorelib uses the file system's modification time (``os.path.getmtime``)
to decide whether a target needs rebuilding. The ``@mtime`` decorator lets you
override this for targets that aren't local files.

SQLite Example
^^^^^^^^^^^^^^

This example stores timestamps in a SQLite database:

.. code-block:: python

   import sqlite3
   from chorelib import Main, mtime, rule

   DB = "mydata.db"

   @mtime(re.compile(r"\w+"))
   def get_db_mtime(target):
       """Get mtime from SQLite database."""
       conn = sqlite3.connect(DB)
       cur = conn.execute(
           "SELECT mtime FROM entries WHERE name = ?", (target,)
       )
       row = cur.fetchone()
       conn.close()
       if row:
           return row[0]
       return None  # Target does not exist — triggers a build

   @rule(re.compile(r"\w+"), default=True)
   def fetch_data(target, depends, needs):
       """Fetch and store data."""
       ...

   if __name__ == "__main__":
       Main().run()

Key points:

- The ``@mtime`` function should return a numeric timestamp, a ``datetime``
  object, or ``None`` if the target does not exist.
- Returning ``None`` tells chorelib the target is missing and needs to be built.
- The ``@mtime`` pattern matching works the same as ``@rule`` — regex patterns
  and string literals are both supported.

S3 Example
^^^^^^^^^^

You can also use custom mtime to manage remote resources like S3 objects:

.. code-block:: python

   import re
   import boto3
   from chorelib import mtime, rule

   s3 = boto3.client("s3")

   @mtime(re.compile(r"^s3://([^/]+)/(.+)"))
   def s3_mtime(target):
       """Check S3 object modification time."""
       m = re.match(r"^s3://([^/]+)/(.+)", target)
       bucket, key = m.group(1), m.group(2)
       try:
           resp = s3.head_object(Bucket=bucket, Key=key)
           return resp["LastModified"]
       except s3.exceptions.ClientError:
           return None

   @rule(re.compile(r"^s3://([^/]+)/(.+)"), depends=r"\2")
   def upload(target, depends, needs):
       """Upload local file to S3."""
       m = re.match(r"^s3://([^/]+)/(.+)", target)
       bucket, key = m.group(1), m.group(2)
       s3.upload_file(depends[0], bucket, key)

Dynamic Targets with schedule()
-------------------------------

Within a builder function, you can dynamically add new targets to the current
build using ``schedule()``:

.. code-block:: python

   from chorelib import rule, schedule, task

   @task
   def discover():
       """Discover and build all .txt files."""
       files = find_files_to_process()
       schedule(files)

``schedule()`` is thread-safe and can be called from any builder, even when
running with multiple workers.

Parallel Execution
------------------

Use the ``-w`` flag to run independent build steps concurrently:

.. code-block:: bash

   python make.py -w 4    # Use 4 parallel workers

chorelib automatically determines which targets can be built in parallel based
on the dependency graph. Targets with no dependency relationship between them
are built concurrently.

Subclassing Main
----------------

You can subclass ``Main`` to add custom command-line arguments:

.. code-block:: python

   from chorelib import Main

   class MyMain(Main):
       def add_arguments(self, parser):
           parser.add_argument("--dbfile", default="data.db",
                               help="Database file path")

   if __name__ == "__main__":
       MyMain().run()

The parsed arguments are available as ``self.args`` within the ``Main`` instance.
Override ``add_arguments()`` to add your own arguments to the
``argparse.ArgumentParser``.
