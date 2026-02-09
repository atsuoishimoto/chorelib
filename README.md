# chorelib

A Python build automation framework — like Make, but in Python.
chorelib focuses on keeping Make-style speed and rebuild behavior while letting you write build logic in real Python.

chorelib uses a decorator-based DSL for defining build rules and tasks, with dependency management, parallel execution, and mtime-based rebuild detection.

## Features

- **Decorator-based DSL** — Define build rules with `@rule` and tasks with `@task`, using familiar Python syntax
- **Regex target patterns** — Match multiple targets with regex and use backreferences (`\1`) in dependency specifications
- **Async parallel execution** — Run independent build steps concurrently with configurable worker count
- **mtime-based rebuild** — Skip up-to-date targets automatically, just like Make
- **Custom mtime functions** — Override mtime checking per target pattern to manage non-file resources (databases, S3 objects, etc.)
- **Order-only prerequisites** — `needs` dependencies ensure build order without triggering rebuilds
- **Auto-generated help** — `-h` shows usage with target documentation from docstrings, `-l` lists all available targets
- **Custom command-line options** — Subclass `Main` to add your own `argparse` options for build configuration
- **Zero dependencies** — Pure Python, no external packages required

**Best for:** developers who want Make-like rebuild behavior but need Python for complex logic or non-file resources.
It also works well as a simple task runner for everyday scripts.

## Documentation

Full documentation is available at https://chorelib.readthedocs.io/en/latest/

## Installation

```bash
pip install chorelib
```

## Quick Start

Here is a Makefile and its chorelib equivalent side by side.

**Makefile:**

```makefile
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
```

**chorelib (`make.py`):**

```python
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
```

```bash
uv run make.py              # Build default target
uv run make.py clean        # Run the clean task
uv run make.py -w 4         # Build with 4 parallel workers
uv run make.py -r           # Force rebuild all
uv run make.py -h           # Show help with target docs
uv run make.py -l           # List all available targets
```

`-h` displays usage information along with target documentation extracted from docstrings:

```
$ uv run make.py -h
usage: make.py [-h] [-C DIRECTORY] [-w WORKERS] [-r] [-l] [-v] [-V] [targets ...]

Sample build script for building a C program using chorelib.

hello.exe [default]:
    Build executable

clean:
    Remove the built files.

rebuild:
    Clean and rebuild all files.

execute:
    Rebuild and execute the program.
...
```

`-l` lists all registered targets with their types, dependencies, and builder functions:

```
$ uv run make.py -l
[rule] hello.exe:
  depends: hello.o, main.o
  needs:
  function: link

[rule] re: (.+)\.o:
  depends: \1.c, hello.h
  needs:
  function: compile

[task] clean:
  needs:
  builder: clean
...
```

## Why chorelib over Make?

| | Make | chorelib |
|---|---|---|
| Pattern rules | `%.o: %.c` | `r"^(.+)\.o"` with backreferences |
| Variables & logic | Limited macro language | Full Python |
| Parallel builds | `make -j4` | `python make.py -w 4` |
| Non-file targets | `.PHONY` | `@task` decorator |
| Custom mtime | Not supported | `@mtime` decorator for databases, remote objects, etc. |
| Dependencies | File-only | Files, functions, or any callable |

## License

MIT
