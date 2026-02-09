"""
Sample build script using SQLite as a custom mtime backend.

Demonstrates how chorelib can manage non-file resources by providing a custom
@mtime function. Instead of checking file modification times, this script
stores and retrieves timestamps from a SQLite database.

Usage:
    uv run python sqlitesample.py             # List registered countries
    uv run python sqlitesample.py japan        # Fetch and register a country
    uv run python sqlitesample.py clean        # Delete the database file
"""

import os
import re
import sqlite3
from datetime import UTC, datetime
from urllib.request import urlopen

from chorelib import Main, mtime, rule, task


# Subclass Main to add a --dbfile option and ensure the database table exists
# before any build targets run.
class SqliteMain(Main):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dbfile",
            dest="dbfile",
            default="sample.db",
            help="SQLite database file name (default: sample.db)",
        )

    def get_con(self):
        return sqlite3.connect(self.args.dbfile)

    def create_db(self):
        """Create database file"""
        with self.get_con() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS countries (
                    name TEXT NOT NULL,
                    registered_at REAL NOT NULL,
                    json TEXT NOT NULL
                )""")

    # Ensure the database table is created before executing any targets.
    def build(self, targets):
        self.create_db()
        super().build(targets)


main = SqliteMain()


# Default target: list all registered countries from the database.
@task(default=True)
def list():
    """List countries"""
    n = 0
    with main.get_con() as con:
        cursor = con.cursor()
        for name, registered_at, json in cursor.execute(
            "SELECT name, registered_at, json FROM countries ORDER BY name"
        ).fetchall():
            print(name, registered_at, repr(json))
            n = 1
    if not n:
        print("No country recorded")


@task()
def clean():
    """Delete database file"""
    os.unlink(main.args.dbfile)


# Custom mtime function: returns the timestamp stored in the database
# for the given target name, or None if the target has not been registered.
# This replaces the default file-based mtime check, allowing chorelib
# to decide whether a target needs to be rebuilt based on database records.
@mtime(re.compile(".+"))
def get_db_date(target):
    with main.get_con() as con:
        target = target.upper()
        cursor = con.cursor()
        rec = cursor.execute(
            "SELECT registered_at FROM countries WHERE name=?", (target,)
        ).fetchone()
        if not rec:
            return None
        else:
            return rec[0]


# Rule that matches any word as a target name (e.g., "japan", "france").
# Fetches country data from the REST Countries API and stores it in the database.
# Because get_db_date returns None for unregistered countries, this rule
# will only run once per country (unless the database record is deleted).
@rule(re.compile(r"\w+"))
def register_country(target, *args):
    target = target.upper()
    with urlopen(f"https://restcountries.com/v3.1/name/{target}") as f:
        json = f.read().decode("utf-8")
    with main.get_con() as con:
        cursor = con.cursor()
        cursor.execute(
            """
            INSERT INTO countries(name, registered_at, json) VALUES (?, ?, ?)
            """,
            (target, datetime.now(tz=UTC).isoformat(), json),
        )
        con.commit()


if __name__ == "__main__":
    main.run()
