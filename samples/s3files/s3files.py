# /// script
# dependencies = [
#   "chorelib",
#   "boto3",
# ]
# ///

"""Upload local files to Amazon S3 using chorelib.

Demonstrates chorelib's custom mtime feature: by defining a custom @mtime
handler for S3 URLs, chorelib can compare the last-modified time of a local
file against the S3 object and skip uploads when the S3 copy is already
up to date.

Usage:
    uv run s3files.py s3://BUCKETNAME/S3TEST.txt
"""

from urllib.parse import urlparse

import boto3
import botocore

from chorelib import Main, mtime, rule

main = Main()

s3 = boto3.client("s3")

# Regex target pattern: matches S3 URLs like "s3://bucket/key".
# Capture groups: \1 = bucket name, \2 = object key (used as local filename).
TARGET = r"^s3://([^/]+)/(.+)"


def parse_s3url(s3url):
    """Parse an S3 URL into (bucket, key)."""
    parsed = urlparse(s3url)
    return parsed.netloc, parsed.path.lstrip("/")


# Build rule: upload a local file to S3.
# The regex backreference \2 maps the S3 object key to the local file dependency.
# e.g. "s3://mybucket/S3TEST.txt" depends on local file "S3TEST.txt".
@rule(targets=TARGET, depends=r"\2")
def copyfile(target, depends, *args):
    """Upload a local file to an S3 bucket."""
    bucket, key = parse_s3url(target)
    print(f"Copy {depends} to {target}")
    s3.upload_file(Filename=str(depends[0]), Bucket=bucket, Key=key)


# Custom mtime handler for S3 URLs.
# Returns the LastModified timestamp of the S3 object, or None if the object
# does not exist. chorelib uses this to compare against the local file's mtime
# and decide whether an upload is needed.
@mtime(r"^s3://[^/]+/.+")
def check_s3file(target):
    """Return the last-modified time of an S3 object, or None if not found."""
    bucket, key = parse_s3url(target)
    try:
        return s3.head_object(Bucket=bucket, Key=key)["LastModified"]
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None
        raise


if __name__ == "__main__":
    main.run()
