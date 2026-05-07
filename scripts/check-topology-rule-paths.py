#!/usr/bin/env python3
"""Check topology TSV runtime authorities against topology rule paths."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import NoReturn

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_TSV = REPO_ROOT / "skills/shared/topology.tsv"
RULE_FILE = REPO_ROOT / ".claude/rules/topology-generation.md"
RULE_PATH = ".claude/rules/topology-generation.md"


def fail(message: str) -> NoReturn:
    print(f"check-topology-rule-paths: {message}", file=sys.stderr)
    sys.exit(1)


def path_has_segment(path: str, segment: str) -> bool:
    return segment in path.split("/")


def validate_repo_path(row: int, path: str) -> None:
    if path != path.strip():
        fail(f"row {row}: runtime_authority must not contain leading or trailing whitespace")
    if not path:
        fail(f"row {row}: empty runtime_authority")
    if path.startswith("/"):
        fail(f"row {row}: runtime_authority must be repo-relative: {path}")
    if path.startswith("./"):
        fail(f"row {row}: runtime_authority must not start with ./ : {path}")
    if path.startswith("-"):
        fail(f"row {row}: runtime_authority must not start with -: {path}")
    if path.startswith(":"):
        fail(f"row {row}: runtime_authority must not start with : (reserved for git pathspec magic): {path}")
    if "//" in path:
        fail(f"row {row}: runtime_authority must not contain duplicate slash: {path}")
    if "\t" in path:
        fail(f"row {row}: runtime_authority must not contain tabs")
    if "\n" in path:
        fail(f"row {row}: runtime_authority must not contain newlines")
    if path_has_segment(path, ".."):
        fail(f"row {row}: runtime_authority must not contain parent traversal: {path}")
    if path_has_segment(path, "."):
        fail(f"row {row}: runtime_authority must not contain . path segments: {path}")


def read_topology_authorities() -> set[str]:
    authorities: set[str] = set()
    try:
        with open(TOPOLOGY_TSV, encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        fail(f"unable to read skills/shared/topology.tsv: {exc}")

    for row, line in enumerate(text.split("\n"), 1):
        if "\r" in line:
            fail(f"row {row}: CRLF line endings not allowed (use LF)")
        if line == "" or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 4 or fields[0] == "" or fields[1] == "" or fields[3] == "":
            fail(
                f"row {row}: malformed row; expected exactly four tab-separated columns "
                "with key, value, and runtime_authority non-empty"
            )
        validate_repo_path(row, fields[3])
        authorities.add(fields[3])

    if not authorities:
        fail("skills/shared/topology.tsv has no data rows")
    return authorities


def extract_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0] not in ("---\n", "---\r\n", "---"):
        fail(f"no YAML frontmatter found in {RULE_PATH}")

    frontmatter_lines: list[str] = []
    for line in lines[1:]:
        if line in ("---\n", "---\r\n", "---"):
            frontmatter = "".join(frontmatter_lines)
            if "\r" in "".join(lines[: len(frontmatter_lines) + 2]):
                fail(f"{RULE_PATH}: CRLF line endings not allowed")
            return frontmatter
        frontmatter_lines.append(line)

    fail(f"no YAML frontmatter found in {RULE_PATH}")


def read_rule_paths() -> set[str]:
    try:
        with open(RULE_FILE, encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        fail(f"unable to read {RULE_PATH}: {exc}")

    frontmatter = extract_frontmatter(text)
    try:
        parsed = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        fail(f"invalid YAML frontmatter in {RULE_PATH}: {exc}")

    if not isinstance(parsed, dict):
        fail(f"{RULE_PATH} frontmatter must be a mapping")
    if "paths" not in parsed:
        fail(f"{RULE_PATH} frontmatter must define paths")
    paths = parsed["paths"]
    if not isinstance(paths, list):
        fail(f"{RULE_PATH} frontmatter paths must be a list")
    for index, path in enumerate(paths):
        if not isinstance(path, str):
            fail(f"{RULE_PATH} frontmatter paths[{index}] must be a string")
    return set(paths)


def main() -> int:
    if len(sys.argv) != 1:
        fail("usage: scripts/check-topology-rule-paths.py")

    missing = sorted(read_topology_authorities() - read_rule_paths())
    if missing:
        print(
            f"check-topology-rule-paths: TSV runtime authorities missing from {RULE_PATH} paths:",
            file=sys.stderr,
        )
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
