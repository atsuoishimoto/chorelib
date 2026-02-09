# sqlite sample

A sample that demonstrates how to use chorelib with a custom mtime backend backed by SQLite, instead of the default file-based modification time checking.

## Overview

This script manages country information fetched from the [REST Countries API](https://restcountries.com/). Instead of building files, it stores data in a SQLite database and uses a custom `@mtime` function to track whether a country has already been registered.

This showcases a key chorelib feature: by providing a custom mtime function, you can manage any resource — not just local files.

### Key concepts demonstrated

- **`@mtime`** — Custom mtime function that reads timestamps from SQLite instead of the filesystem. Returns `None` for unregistered countries, triggering the build rule.
- **`@rule` with regex** — Matches any word as a target name (e.g., `japan`, `france`), so you don't need to define a rule per country.
- **Subclassing `Main`** — Adds a `--dbfile` option and ensures the database table exists before any targets run.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Internet connection (to fetch data from REST Countries API)

## Usage

Run from this directory:

```bash
# List all registered countries (default target)
uv run python sqlitesample.py

# Register a country (fetches data from API and stores in DB)
uv run python sqlitesample.py japan

# Register multiple countries
uv run python sqlitesample.py japan france brazil

# Use a different database file
uv run python sqlitesample.py --dbfile mydata.db japan

# Delete the database file
uv run python sqlitesample.py clean
```

Running a country target a second time does nothing, because the custom `@mtime` function detects it is already registered.

## File structure

| File              | Description                                        |
| ----------------- | -------------------------------------------------- |
| `sqlitesample.py` | Chorelib build script with SQLite mtime backend    |
| `sample.db`       | SQLite database file (created automatically)       |
