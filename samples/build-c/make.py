# /// script
# dependencies = [
#   "chorelib"
# ]
# ///

"""
Sample build script for building a C program using chorelib.

This is the chorelib equivalent of the accompanying Makefile.
Run with: uv run python make.py
"""

import re

from chorelib import Main, command, rule, task

main = Main()

# Build configuration
APP = "hello.exe"  # Output executable name
CC = "gcc"  # C compiler
CFLAGS = ["-c", "-I."]  # Compile flags: -c for object file, -I. for local headers
DEPS = ["hello.h"]  # Header files that all .o files depend on
OBJS = ["hello.o", "main.o"]  # Object files to link


# Link object files into the executable.
# `default=True` makes this the default target (like the first rule in a Makefile).
# Rebuilds when any of the OBJS files are newer than APP.
@rule(APP, depends=OBJS, default=True)
def link(target, deps, needs):
    """
    Build executable
    """
    # command() automatically flattens nested sequences, so `deps` (a list)
    # is expanded into individual arguments: gcc -o hello.exe hello.o main.o
    command(CC, "-o", target, deps)


# Compile .c files into .o files.
# The regex pattern matches any .o file and the backreference `\1.c`
# automatically resolves the corresponding .c source file.
# e.g., "hello.o" depends on "hello.c" and DEPS (header files).
# `depends` flattens nested sequences — (r"\1.c", DEPS) becomes ["\1.c", "hello.h"].
@rule(re.compile(r"(.+)\.o"), depends=(r"\1.c", DEPS))
def compile(target, deps, needs):
    # CFLAGS is a list, but command() flattens it automatically:
    # gcc -o hello.o hello.c -c -I.
    command(CC, "-o", target, deps[0], CFLAGS)


# @task defines an always-execute target (equivalent to .PHONY in Make).
@task
def clean():
    """
    Remove the built files.
    """
    # OBJS is a list, but command() flattens it: rm -f hello.o main.o hello.exe
    command("rm", "-f", OBJS, APP)


# Depends on "clean" first, then APP, so it cleans and rebuilds in order.
@task(needs=("clean", APP))
def rebuild():
    """
    Clean and rebuild all files.
    """


@task(needs="rebuild")
def execute():
    """
    Rebuild and execute the program.
    """
    command("./" + APP)


if __name__ == "__main__":
    main.run()
