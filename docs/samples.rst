Samples
=======

chorelib ships with several sample projects that demonstrate different features.
Each sample is a self-contained build script in the ``samples/`` directory.

build-c — C Program Compilation
--------------------------------

**Directory:** ``samples/build-c/``

A direct replacement for a Makefile that compiles a C program. Demonstrates
the core chorelib workflow: regex pattern rules, backreferences, tasks, and
the ``command()`` function.

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

**Features demonstrated:**

- Regex target patterns with backreferences
- ``command()`` for safe subprocess execution
- ``default=True`` for the main build target
- ``@task`` for clean-up operations

generate-doc — File Concatenation
----------------------------------

**Directory:** ``samples/generate-doc/``

The simplest chorelib example. Concatenates multiple text files into a single
output file using ``shell()``.

.. code-block:: python

   from chorelib import Main, rule, shell, task

   main = Main()
   SRCFILES = ["a.txt", "b.txt", "c.txt"]
   COMMON = ["inc1.txt", "inc2.txt"]

   @rule("DOC.txt", depends=[SRCFILES, COMMON], default=True)
   def generate(target, depends, needs):
       """Generate DOC.txt from source files."""
       shell("cat", depends, ">", target)

   @task
   def clean():
       """Remove the generated file."""
       shell("rm -f DOC.txt")

   if __name__ == "__main__":
       main.run()

**Features demonstrated:**

- Nested lists in ``depends`` (automatically flattened)
- ``shell()`` for shell command execution

md-to-pdf — Markdown to PDF Pipeline
-------------------------------------

**Directory:** ``samples/md-to-pdf/``

A two-stage pipeline that converts Markdown files to HTML (using Mistune with
Pygments syntax highlighting) and then to PDF (using Playwright's headless
Chromium).

**Features demonstrated:**

- Dependency chains (Markdown → HTML → PDF)
- Order-only prerequisites (``needs`` for the build directory)
- Regex backreferences in multi-stage pipelines

s3files — S3 File Upload
-------------------------

**Directory:** ``samples/s3files/``

Uploads local files to Amazon S3, using a custom ``@mtime`` function to check
whether the S3 object is up to date before uploading.

.. code-block:: python

   import re
   import boto3
   from chorelib import Main, mtime, rule

   BUCKET = "my-bucket"
   s3 = boto3.client("s3")

   @mtime(re.compile(r"^s3://([^/]+)/(.+)"))
   def s3_mtime(target):
       m = re.match(r"^s3://([^/]+)/(.+)", target)
       bucket, key = m.group(1), m.group(2)
       try:
           resp = s3.head_object(Bucket=bucket, Key=key)
           return resp["LastModified"]
       except s3.exceptions.ClientError:
           return None

   @rule(re.compile(r"^s3://([^/]+)/(.+)"), depends=r"\2")
   def upload(target, depends, needs):
       m = re.match(r"^s3://([^/]+)/(.+)", target)
       bucket, key = m.group(1), m.group(2)
       s3.upload_file(depends[0], bucket, key)

**Features demonstrated:**

- Custom ``@mtime`` for remote resources
- ``datetime`` return values (automatically converted to timestamps)
- Regex capture groups mapping S3 URLs to local files

sqlite — Database-Backed mtime
-------------------------------

**Directory:** ``samples/sqlite/``

Demonstrates managing non-file resources with a SQLite database as the mtime
backend. Fetches country data from a REST API and stores it in a database.

**Features demonstrated:**

- Custom ``@mtime`` reading timestamps from a database
- Subclassing ``Main`` to add custom CLI arguments (``--dbfile``)
- REST API integration within builder functions

thumbnails — Image Banner Generation
-------------------------------------

**Directory:** ``samples/thumbnails/``

Combines flag images by geographic region into banner JPEGs using Pillow.
Demonstrates a two-level dependency chain with dynamic dependency discovery.

**Features demonstrated:**

- Named regex groups (``(?P<REGION>...)``)
- Callable dependencies for dynamic file discovery at build time
- Two-level dependency chain (flags → region banners → world banner)
- Parallel builds (``-w 4``) for image processing
