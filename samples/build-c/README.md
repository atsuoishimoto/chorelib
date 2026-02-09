# build-c sample

A simple example that demonstrates how to use chorelib as a replacement for Make to build a C program.

## Overview

This sample builds a "Hello, World!" C program (`hello.exe`) from two source files (`main.c`, `hello.c`). The build script `make.py` is the chorelib equivalent of the accompanying `Makefile`, showcasing the following features:

- **`@rule`** — File-based build rules with mtime-based rebuild detection
- **`@task`** — Always-execute targets (equivalent to `.PHONY` in Make)
- **Regex patterns** — A single `@rule` with a regex pattern compiles any `.c` file into a `.o` file, using backreferences to resolve dependencies automatically
- **`default=True`** — Marks the default target to build when no target is specified

## Prerequisites

- GCC (`gcc`)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Usage

Run from this directory:

```bash
# Build the executable (default target)
uv run python make.py

# Clean built files
uv run python make.py clean

# Clean and rebuild
uv run python make.py rebuild

# Rebuild and run the program
uv run python make.py execute
```

### Useful options

```bash
# Show available targets and their descriptions
uv run python make.py -h

# Verbose output (show executed commands)
uv run python make.py -v

# Force rebuild all targets regardless of mtime
uv run python make.py -r

# Run up to 4 tasks in parallel
uv run python make.py -w 4
```

## File structure

| File       | Description                                      |
| ---------- | ------------------------------------------------ |
| `make.py`  | Chorelib build script (equivalent to `Makefile`) |
| `Makefile`  | Traditional Makefile for comparison              |
| `main.c`   | Entry point — calls `hello()`                    |
| `main.h`   | Common includes (`stdio.h`)                      |
| `hello.c`  | Implements `hello()` function                    |
| `hello.h`  | Header for the hello module                      |

## Comparison with Makefile

The `Makefile` is included so you can compare the two approaches side by side.

**Makefile:**

```makefile
%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

hello.exe: $(OBJS)
	$(CC) -o $@ $^
```

**make.py:**

```python
@rule(re.compile(r"(.+)\.o"), depends=(r"\1.c", DEPS))
def compile(target, deps, needs):
    command(CC, "-o", target, deps[0], CFLAGS)

@rule(APP, depends=OBJS, default=True)
def link(target, deps, needs):
    command(CC, "-o", target, deps)
```

Both achieve the same result — chorelib uses Python regex patterns where Make uses `%` wildcards, and Python functions where Make uses shell recipes.
