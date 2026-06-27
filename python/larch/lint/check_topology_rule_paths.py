"""Check topology TSV runtime authorities against topology rule paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import NoReturn

RULE_PATH = ".claude/rules/topology-generation.md"
_INT_RE = re.compile(r"[-+]?(0|[1-9][0-9]*)")
_FLOAT_RE = re.compile(r"[-+]?(\d+\.\d*|\.\d+)([eE][-+]?\
d+)?$")
EXPECTED_TSV_COLUMNS = 4


def fail(message: str) -> NoReturn:
    print(f"check-topology-rule-paths: {message}", file=sys.stderr)
    sys.exit(1)


def path_has_segment( *,path: str, segment: str) -> bool:
    return segment in path.split("/")


def validate_repo_path( *,row: int, path: str, repo_root: Path, repo_root_resolved: Path) -> None:
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
    if path_has_segment(path=path, segment=".."):
        fail(f"row {row}: runtime_authority must not contain parent traversal: {path}")
    if path_has_segment(path=path, segment="."):
        fail(f"row {row}: runtime_authority must not contain . path segments: {path}")
    resolved = (repo_root / path).resolve(strict=False)
    try:
        _ = resolved.relative_to(repo_root_resolved)
    except ValueError:
        fail(f"row {row}: runtime_authority must resolve within repo root: {path}")


def read_topology_authorities( *,topology_tsv: Path, repo_root: Path, repo_root_resolved: Path) -> set[str]:
    authorities: set[str] = set()
    try:
        with topology_tsv.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        fail(f"unable to read skills/shared/topology.tsv: {exc}")

    for row, line in enumerate(text.split("\n"), 1):
        if "\r" in line:
            fail(f"row {row}: CRLF line endings not allowed (use LF)")
        if line == "" or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != EXPECTED_TSV_COLUMNS or fields[0] == "" or fields[1] == "" or fields[3] == "":
            fail(
                f"row {row}: malformed row; expected exactly four tab-separated columns "
                "with key, value, and runtime_authority non-empty"
            )
        validate_repo_path(row=row, path=fields[3], repo_root=repo_root, repo_root_resolved=repo_root_resolved)
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


def _split_flow_tokens(body: str) -> list[str]:
    tokens: list[str] = []
    start = 0
    in_quote = False
    escaped = False
    for index, char in enumerate(body):
        if in_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_quote = False
            continue
        if char == '"':
            in_quote = True
            continue
        if char == ",":
            tokens.append(body[start:index].strip())
            start = index + 1
    tokens.append(body[start:].strip())
    return [] if len(tokens) == 1 and tokens[0] == "" else tokens


def _decode_quoted_path( *,token: str, index: int) -> str:
    if not (token.startswith('"') and token.endswith('"')):
        fail(f"{RULE_PATH} frontmatter paths[{index}] must be a string")
    try:
        parsed: object = json.loads(token)
    except json.JSONDecodeError as exc:
        fail(f"invalid YAML frontmatter in {RULE_PATH}: {exc}")
    if not isinstance(parsed, str):
        fail(f"{RULE_PATH} frontmatter paths[{index}] must be a string")
    return parsed


def _bare_token_is_string(token: str) -> bool:
    stripped = token.strip()
    if not stripped:
        return False
    if stripped[0] in "{&*[":
        return False
    lowered = stripped.lower()
    if lowered in {"null", "true", "false", "~"}:
        return False
    if _INT_RE.fullmatch(stripped) is not None:
        return False
    return _FLOAT_RE.fullmatch(stripped) is None


def _parse_flow_paths(value: str) -> list[str]:
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        fail(f"{RULE_PATH} frontmatter paths must be a list")
    body = stripped[1:-1]
    paths: list[str] = []
    for index, token in enumerate(_split_flow_tokens(body)):
        paths.append(_decode_quoted_path(token=token, index=index))
    return paths


def _parse_block_path( *,token: str, index: int) -> str:
    stripped = token.strip()
    if stripped.startswith('"'):
        return _decode_quoted_path(token=stripped, index=index)
    if not stripped or stripped.startswith("[") or not _bare_token_is_string(stripped):
        fail(f"{RULE_PATH} frontmatter paths[{index}] must be a string")
    return stripped


def parse_frontmatter_paths(frontmatter: str) -> list[str]:
    lines = frontmatter.split("\n")
    paths_line: int | None = None
    inline_value: str | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "paths:":
            paths_line = index
            inline_value = None
            break
        if stripped.startswith("paths:"):
            paths_line = index
            inline_value = stripped.removeprefix("paths:").strip()
            break

    if paths_line is None:
        fail(f"{RULE_PATH} frontmatter must define paths")
    if inline_value is not None:
        return _parse_flow_paths(inline_value)

    paths: list[str] = []
    for line in lines[paths_line + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading == 0:
            break
        entry = line.lstrip(" ")
        if not entry.startswith("-"):
            fail(f"{RULE_PATH} frontmatter paths must be a list")
        token = entry[1:].strip()
        paths.append(_parse_block_path(token=token, index=len(paths)))
    if not paths:
        fail(f"{RULE_PATH} frontmatter paths must be a list")
    return paths


def read_rule_paths(rule_file: Path) -> set[str]:
    try:
        with rule_file.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        fail(f"unable to read {RULE_PATH}: {exc}")

    frontmatter = extract_frontmatter(text)
    paths = parse_frontmatter_paths(frontmatter)
    return set(paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root to validate (default: this module's parent directory).",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    repo_root = args.root.resolve()
    repo_root_resolved = repo_root.resolve()
    topology_tsv = repo_root / "skills/shared/topology.tsv"
    rule_file = repo_root / RULE_PATH

    missing = sorted(
        read_topology_authorities(topology_tsv=topology_tsv, repo_root=repo_root, repo_root_resolved=repo_root_resolved)
        - read_rule_paths(rule_file)
    )
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
