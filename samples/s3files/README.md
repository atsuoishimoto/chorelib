# s3files: Upload Files to Amazon S3

A chorelib sample that uploads local files to S3, demonstrating custom `@mtime` handlers for non-filesystem resources.

## Overview

This sample shows how chorelib can manage resources beyond the local filesystem. By defining a custom `@mtime` handler for S3 URLs, chorelib compares the last-modified time of a local file against the corresponding S3 object and **skips the upload when the S3 copy is already up to date** -- just like Make skips rebuilding when a target is newer than its sources.

```
S3TEST.txt (local)  -->  s3://bucket/S3TEST.txt (S3)
```

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- [AWS CLI](https://aws.amazon.com/cli/) installed and configured (`aws configure`)
- An existing S3 bucket

## Usage

```bash
# Upload a file to S3
uv run s3files.py s3://YOUR_BUCKET/S3TEST.txt

# The file is skipped if the S3 object is already up to date
uv run s3files.py s3://YOUR_BUCKET/S3TEST.txt

# Verbose output
uv run s3files.py -v s3://YOUR_BUCKET/S3TEST.txt
```

## Files

| File | Description |
|---|---|
| `s3files.py` | Build script defining chorelib rules and custom mtime handler |
| `S3TEST.txt` | Sample local file to upload |

## chorelib Features Demonstrated

- **Custom `@mtime` handler** -- `check_s3file` returns the `LastModified` timestamp of an S3 object (or `None` if it doesn't exist). This lets chorelib treat S3 objects as build targets with mtime-based rebuild detection, just like local files.
- **Regex target patterns** -- `TARGET = r"^s3://([^/]+)/([^/]+)"` matches S3 URLs. The capture groups extract the bucket name and object key.
- **Regex backreferences in dependencies** -- `depends=r"\2"` maps the S3 object key back to the local filename. For example, target `s3://mybucket/S3TEST.txt` automatically depends on local file `S3TEST.txt`.
