#!/usr/bin/env python3
"""Validates local-rig-specs GPU JSON records: schema conformance,
vendor-file consistency, and duplicate ids/names."""
import json
import sys
from pathlib import Path

import duckdb
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = {
    "gpus": REPO_ROOT / "schema" / "gpu.schema.json",
}


def load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text())


class InvalidVendorFileError(Exception):
    """Raised when a vendor JSON file's top-level value isn't a list of entries."""


def load_category_files(category_dir: Path) -> dict[str, list[dict]]:
    """Returns {filename: [entries...]} for every *.json file in category_dir."""
    files = {}
    for path in sorted(category_dir.glob("*.json")):
        parsed = json.loads(path.read_text())
        if not isinstance(parsed, list):
            raise InvalidVendorFileError(
                f"{path.name}: expected a top-level JSON array of entries, "
                f"got {type(parsed).__name__}"
            )
        files[path.name] = parsed
    return files


def validate_schema(entries_by_file: dict[str, list[dict]], schema: dict) -> list[str]:
    """Returns human-readable error strings, empty if every entry is valid."""
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = []
    for filename, entries in entries_by_file.items():
        for index, entry in enumerate(entries):
            for error in validator.iter_errors(entry):
                errors.append(f"{filename}[{index}]: {error.message}")
    return errors


def check_vendor_consistency(entries_by_file: dict[str, list[dict]]) -> list[str]:
    """Every entry's manufacturer must match the vendor its filename names."""
    errors = []
    for filename, entries in entries_by_file.items():
        vendor_slug = filename.removesuffix(".json")
        for index, entry in enumerate(entries):
            manufacturer = entry.get("manufacturer", "")
            if not isinstance(manufacturer, str):
                continue
            if manufacturer.lower() != vendor_slug.lower():
                errors.append(
                    f"{filename}[{index}]: manufacturer {manufacturer!r} does not match "
                    f"the vendor file name (expected {vendor_slug!r})"
                )
    return errors


def check_duplicates(all_entries: list[tuple[str, dict]]) -> list[str]:
    """all_entries is a list of (filename, entry) pairs across every category/file.
    Returns error strings for duplicate ids and duplicate (manufacturer, name)
    pairs, both checked globally across all vendor files."""
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE entries (filename VARCHAR, id VARCHAR, manufacturer VARCHAR, name VARCHAR)"
    )
    for filename, entry in all_entries:
        con.execute(
            "INSERT INTO entries VALUES (?, ?, ?, ?)",
            [filename, entry.get("id"), entry.get("manufacturer"), entry.get("name")],
        )

    errors = []

    dup_ids = con.execute(
        "SELECT id, list(filename) AS files, count(*) AS n "
        "FROM entries GROUP BY id HAVING count(*) > 1"
    ).fetchall()
    for id_, files, n in dup_ids:
        errors.append(f"duplicate id {id_!r} appears {n} times, in {files}")

    dup_names = con.execute(
        "SELECT manufacturer, name, list(filename) AS files, count(*) AS n "
        "FROM entries GROUP BY manufacturer, name HAVING count(*) > 1"
    ).fetchall()
    for manufacturer, name, files, n in dup_names:
        errors.append(
            f"duplicate (manufacturer, name) ({manufacturer!r}, {name!r}) "
            f"appears {n} times, in {files}"
        )

    return errors


def main() -> int:
    all_errors: list[str] = []
    all_entries: list[tuple[str, dict]] = []
    counts: dict[str, int] = {}

    for category_name, schema_path in CATEGORIES.items():
        category_dir = REPO_ROOT / category_name
        schema = load_schema(schema_path)

        try:
            entries_by_file = load_category_files(category_dir)
        except json.JSONDecodeError as e:
            print(f"FATAL: could not parse JSON in {category_name}/: {e}", file=sys.stderr)
            return 1
        except InvalidVendorFileError as e:
            print(f"FATAL: invalid vendor file in {category_name}/: {e}", file=sys.stderr)
            return 1

        all_errors.extend(validate_schema(entries_by_file, schema))
        all_errors.extend(check_vendor_consistency(entries_by_file))

        category_count = 0
        for filename, entries in entries_by_file.items():
            category_count += len(entries)
            for entry in entries:
                all_entries.append((f"{category_name}/{filename}", entry))
        counts[category_name] = category_count

    all_errors.extend(check_duplicates(all_entries))

    if all_errors:
        print(f"FAILED — {len(all_errors)} issue(s) found:\n", file=sys.stderr)
        for error in all_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK — {counts.get('gpus', 0)} GPUs validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
