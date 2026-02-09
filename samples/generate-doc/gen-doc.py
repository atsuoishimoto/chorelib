# /// script
# dependencies = [
#   "chorelib"
# ]
# ///

"""
Sample chorelib script to concatenate text files into a single document.

Demonstrates a simple file-based build rule with multiple source files
and common include files as dependencies. Rebuilds only when any of
the source or include files are newer than the output.

Run with: uv run python gen-doc.py
"""

from chorelib import Main, rule, shell, task

main = Main()

# Build configuration
DOC = "DOC.txt"  # Output file
SRCFILES = ["a.txt", "b.txt", "c.txt"]  # Primary source files
COMMON = ["inc1.txt", "inc2.txt"]  # Common files included in every build


# Concatenate all source and common files into DOC.txt using shell redirection.
# Rebuilds when any file in SRCFILES or COMMON is newer than DOC.
# `depends` accepts nested sequences — (SRCFILES, COMMON) is automatically
# flattened to ["a.txt", "b.txt", "c.txt", "inc1.txt", "inc2.txt"].
@rule(DOC, depends=(SRCFILES, COMMON))
def build_doc(target, depends, needs):
    """Builds target text"""
    # shell() also flattens nested sequences, so passing `depends` (a list)
    # as a single argument works — it expands to individual file names.
    shell("cat", depends, ">", target)


@task
def clean():
    """Remove the generated document."""
    shell("rm", "-f", DOC)


if __name__ == "__main__":
    main.run()
