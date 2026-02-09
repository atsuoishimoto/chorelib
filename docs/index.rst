chorelib
========

**A Python build automation framework — like Make, but in Python.**

chorelib uses a decorator-based DSL for defining build rules and tasks, with
dependency management, parallel execution, and mtime-based rebuild detection.
By providing custom mtime functions, it can manage not just local files but any
resource — databases, S3 objects, and more.

.. code-block:: python

   import chorelib

   @chorelib.rule("output.txt", depends="input.txt")
   def build_output(target, depends, needs):
       chorelib.shell(f"cp {depends[0]} {target}")

   if __name__ == "__main__":
       chorelib.Main().run()

Features
--------

- **Decorator-based DSL** — Define build rules with ``@rule`` and tasks with ``@task``
- **Regex target patterns** — Match multiple targets with regex and use backreferences (``\1``) in dependencies
- **mtime-based rebuild** — Skip up-to-date targets automatically, just like Make
- **Custom mtime functions** — Override mtime checking for non-file resources (databases, S3, etc.)
- **Order-only prerequisites** — ``needs`` dependencies ensure build order without triggering rebuilds
- **Zero dependencies** — Pure Python, no external packages required

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting-started
   tutorial
   concepts
   api
   samples
   changelog
