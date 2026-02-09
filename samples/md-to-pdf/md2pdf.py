# /// script
# dependencies = [
#   "chorelib",
#   "mistune",
#   "pygments",
#   "playwright"
# ]
# ///

"""Markdown to PDF converter using chorelib.

Converts Markdown files to PDF via an intermediate HTML step:
  .md -> .html -> .pdf

Features:
  - Syntax highlighting with Pygments
  - Math rendering with MathJax
  - Diagram rendering with Mermaid
  - Headless browser PDF generation with Playwright
"""

import threading
from pathlib import Path

import mistune
from pygments import highlight
from pygments.formatters import html
from pygments.lexers import get_lexer_by_name

from chorelib import Main, rule, shell, task

main = Main()

TEMPLATE = Path("template.html")  # HTML template with MathJax/Mermaid scripts
BUILD = Path(".build")  # Intermediate HTML output directory
PDF = Path("doc.pdf")  # Final PDF output


# Custom Mistune renderer that adds syntax highlighting for code blocks
# and passes through Mermaid diagram blocks for client-side rendering.
class HighlightRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        if info:
            # Mermaid blocks are rendered client-side by the Mermaid JS library
            if info == "mermaid":
                return "<pre class='mermaid'>\n" + mistune.escape(code) + "\n</pre>"
            # All other language-tagged blocks get Pygments syntax highlighting
            else:
                lexer = get_lexer_by_name(info, stripall=True)
                formatter = html.HtmlFormatter(noclasses=True)
                return highlight(code, lexer, formatter)
        return "<pre><code>" + mistune.escape(code) + "</code></pre>"


renderer = HighlightRenderer()
markdown = mistune.create_markdown(renderer=renderer, plugins=["math"])


# Build rule: .html -> .pdf
# Uses Playwright (headless Chromium) to render HTML and export as PDF.
# Waits for MathJax/Mermaid to finish rendering before PDF export.
@rule(PDF, depends=BUILD / "doc.html", needs=BUILD)
def make_pdf(target, depends, needs):
    """Build PDF from HTML using Playwright headless browser."""

    htmlfile = Path(depends[0]).resolve()
    print("run playwright")

    # Playwright's sync API cannot run inside an existing async event loop,
    # so we run it in a separate thread.
    def run_playwrite():
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(htmlfile.as_uri())
            # Wait for MathJax and Mermaid to finish rendering
            page.wait_for_timeout(3000)
            page.pdf(path=str(target))
            browser.close()

    t = threading.Thread(target=run_playwrite)
    t.start()
    t.join()


# Build rule: .md -> .html
# Uses a regex target pattern (^...) to match any .html file under BUILD/.
# The backreference \1 maps the HTML filename back to the source .md file.
# Rebuilds when the source .md or the HTML template changes.
@rule(rf"^{BUILD}/(.+).html", depends=(Path(r"\1.md"), TEMPLATE), needs=BUILD)
def make_html(target, depends, needs):
    """Convert Markdown to HTML using the template."""
    print(f"build {target}")
    body = markdown(open(depends[0]).read())
    html = Path(TEMPLATE).read_text().format(body=body)
    Path(target).write_text(html)


# Build rule: create the output directory
@rule(BUILD)
def make_dir(target, *args):
    """Create output directory."""
    Path(target).mkdir(parents=True, exist_ok=True)


# Task: clean up all generated files
@task
def clean():
    """Remove all generated files."""
    shell("rm", "-rf", BUILD, PDF)


if __name__ == "__main__":
    main.run()
