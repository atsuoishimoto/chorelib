# Thumbnail Banner Sample

Flag images organized by region are combined into banner JPEGs.

```
flags/
  asia/      *.png  ─┐
  europe/    *.png  ─┤
  africa/    *.png  ─┼─► <region>.jpeg ──► world.jpeg
  america/   *.png  ─┤
  oceania/   *.png  ─┘
```

## Purpose

This sample demonstrates the following chorelib features:

- **Regex targets with named groups** — `^(?P<REGION>[^.]+).jpeg` matches any `<region>.jpeg`, capturing the region name for use in dependency resolution
- **Callable dependencies** — Instead of a static file list, a Python function (`get_region_files`) is passed as `depends`. chorelib calls it at build time with the regex match object, so it can dynamically discover flag files for the matched region
- **Two-level dependency chain** — Flag PNGs → region banners → world banner. Changing a single flag PNG triggers a rebuild of only its region banner and the world banner
- **Parallel builds** — Each region banner is independent, so they can be built concurrently with `-w`

## Usage

```bash
uv run make.py              # Build world.jpeg (default target)
uv run make.py -w 5         # Build region banners in parallel
uv run make.py asia.jpeg    # Build only the Asia banner
uv run make.py clean        # Remove generated JPEG files
uv run make.py -h           # Show help
```

## Requirements

- Python 3.10+
- [Pillow](https://pypi.org/project/Pillow/) (listed in the inline script metadata, installed automatically by `uv run`)
