# generate-doc sample

A minimal example that demonstrates how to use chorelib to concatenate multiple text files into a single document, with mtime-based rebuild detection.

## Overview

This script concatenates source files (`a.txt`, `b.txt`, `c.txt`) and common include files (`inc1.txt`, `inc2.txt`) into a single output file (`DOC.txt`). It only rebuilds when any of the input files are newer than the output.

This is the simplest chorelib example — a single `@rule` with file dependencies and a shell command.

### Key concepts demonstrated

- **`@rule`** — File-based build rule with mtime checking
- **Multiple dependencies** — Both `SRCFILES` and `COMMON` are listed as dependencies; a change to any of them triggers a rebuild
- **`shell()`** — Executes a command through the shell, allowing redirection (`>`)

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Usage

Run from this directory:

```bash
# Build DOC.txt from source files
uv run python gen-doc.py

# Clean the generated file
uv run python gen-doc.py clean

# Verbose output
uv run python gen-doc.py -v
```

After running the build, `DOC.txt` will contain the concatenated contents of all input files:

```
a
b
c
inc1
inc2
```

Running it again without changing any input files will skip the build (up-to-date).

## File structure

| File        | Description                                   |
| ----------- | --------------------------------------------- |
| `gen-doc.py`| Chorelib build script                         |
| `a.txt`     | Source file                                    |
| `b.txt`     | Source file                                    |
| `c.txt`     | Source file                                    |
| `inc1.txt`  | Common include file                            |
| `inc2.txt`  | Common include file                            |
| `DOC.txt`   | Generated output (concatenation of all inputs) |
