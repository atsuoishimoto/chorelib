# md-to-pdf: Markdown to PDF Converter

A chorelib sample that converts Markdown files to PDF, demonstrating regex target patterns, dependency chains, and integration with external tools.

## Overview

This sample builds a PDF from a Markdown source file through a two-stage pipeline:

```
doc.md  -->  .build/doc.html  -->  doc.pdf
```

1. **Markdown to HTML** -- Converts `.md` to `.html` using [Mistune](https://github.com/lepture/mistune), with syntax highlighting ([Pygments](https://pygments.org/)), math support ([MathJax](https://www.mathjax.org/)), and diagram support ([Mermaid](https://mermaid.js.org/)).
2. **HTML to PDF** -- Renders the HTML in a headless Chromium browser via [Playwright](https://playwright.dev/python/) and exports it as PDF.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Playwright browsers (`playwright install chromium`)

## Usage

```bash
# Install dependencies and Playwright browser
uv sync
playwright install chromium

# Build doc.pdf (default target)
uv run md2pdf.py

# Clean generated files
uv run md2pdf.py clean

# Verbose output
uv run md2pdf.py -v doc.pdf
```

## Files

| File | Description |
|---|---|
| `md2pdf.py` | Build script defining chorelib rules |
| `doc.md` | Sample Markdown source |
| `template.html` | HTML template with MathJax and Mermaid scripts |
| `.build/` | Intermediate HTML output (generated) |
| `doc.pdf` | Final PDF output (generated) |

## chorelib Features Demonstrated

- **Regex target patterns** -- `make_html` uses `rf"^{BUILD}/(.+).html"` to match any `.html` file under the build directory, with backreference `\1` to locate the corresponding `.md` source.
- **Dependency chains** -- `doc.pdf` depends on `.build/doc.html`, which depends on `doc.md` and `template.html`. chorelib resolves the full chain automatically.
- **`needs` (order-only prerequisites)** -- The `.build/` directory is an order-only prerequisite: it must exist before building, but changes to it don't trigger rebuilds.
- **Tasks** -- `clean` is a task (always runs, like Make's `.PHONY`).
