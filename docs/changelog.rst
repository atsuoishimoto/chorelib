Changelog
=========

v0.2.1
------
2026/04/01

Remove incorrect warning messages.

v0.2.0
------
2026/02/23

- Add no_default parameter to Main class to exit with an error when no
  targets are specified instead of falling back to default targets.

v0.1.1
------

2026/02/10

- Improved documentation
- Fixed subtle bugs


v0.1.0
------

2026/02/09

*Initial release.*

- Decorator-based DSL with ``@rule``, ``@task``, and ``@mtime``
- Regex target patterns with backreferences in dependencies
- Async parallel execution with configurable worker count
- mtime-based rebuild detection
- Custom mtime functions for non-file resources
- Order-only prerequisites (``needs``)
- CLI driver (``Main``) with help, target listing, and verbosity control
- Utility functions: ``shell()``, ``command()``, ``message()``
- ``schedule()`` for dynamically adding targets during builds
