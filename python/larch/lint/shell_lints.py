"""Python implementations for the residual Bash-targeting linters."""
# ruff: noqa: C901, PLR0912, PLR0915 - scanners intentionally mirror shell grammar.

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

from larch.core.residual_bash import read_residual_paths

_SHELL_SUFFIXES = (".sh", ".inc.bash")
_EXCLUDED_PARTS = frozenset({".git", "node_modules", "larch-logs", ".venv", ".agents"})
_BASH32_BASELINE = "scripts/lint-bash32-empty-array-baseline.tsv"
_ASCII_CONTROL_LIMIT = 32
_ASCII_PRINTABLE_LIMIT = 126
_BASELINE_COLUMNS = 3
_CLOSED_QUOTE_COUNT = 2


def _repo_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_lines(path: Path) -> list[str] | None:
    raw = path.read_bytes()
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None


def _walk(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.name.endswith(suffixes)
        and not _EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
    )


def _residual_shell_paths(root: Path) -> list[Path]:
    manifest = root / "scripts/residual-bash-paths.txt"
    if manifest.is_file():
        return [root / rel for rel in read_residual_paths(root) if (root / rel).is_file()]
    return _walk(root, _SHELL_SUFFIXES)


def _has_nonascii(value: str) -> bool:
    return any((ord(char) < _ASCII_CONTROL_LIMIT and char != "\t") or ord(char) > _ASCII_PRINTABLE_LIMIT for char in value)


def _suppressed(line: str, token: str) -> bool:
    return re.search(rf"#\s*{re.escape(token)}:\s*ok\s+[^\s#]", line) is not None


def _report(path: str, line: int, message: str) -> str:
    return f"{path}:{line}: {message}"


def scan_awk_multibyte(root: Path) -> list[str]:
    """Find non-ASCII dynamic regex values in shell and standalone awk files."""
    paths = _residual_shell_paths(root) + _walk(root, (".awk",))
    seen: set[Path] = set()
    findings: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        lines = _read_lines(path)
        if lines is None:
            continue
        rel = _repo_path(root, path)
        is_awk = path.suffix == ".awk"
        pending = ""
        pending_line = 0
        heredoc: str | None = None
        generic_heredoc: str | None = None
        single_body = False
        for number, raw in enumerate(lines, start=1):
            logical = raw
            line_number = number
            if logical.rstrip().endswith("\\"):
                pending = f"{pending} {logical.rstrip()[:-1]}".strip()
                pending_line = number
                continue
            if pending:
                logical = f"{pending} {logical}"
                line_number = number
                pending = ""
            if generic_heredoc is not None:
                if _closes_heredoc(logical, generic_heredoc):
                    generic_heredoc = None
                continue
            if heredoc is not None:
                _awk_body_findings(findings, rel, line_number, logical)
                if _closes_heredoc(logical, heredoc):
                    heredoc = None
                continue
            if single_body:
                _awk_body_findings(findings, rel, line_number, logical)
                if "'" in logical:
                    single_body = False
                continue
            if is_awk:
                _awk_value_findings(findings, rel, line_number, logical)
                _awk_body_findings(findings, rel, line_number, logical)
                continue
            if not _awk_command(logical):
                generic_heredoc = _heredoc_delimiter(logical)
                continue
            _awk_value_findings(findings, rel, line_number, logical)
            delimiter = _heredoc_delimiter(logical)
            if delimiter is not None:
                heredoc = delimiter
                _awk_body_findings(findings, rel, line_number, logical)
                continue
            body = _single_quoted_awk_body(logical)
            if body is not None:
                _awk_body_findings(findings, rel, line_number, body)
                if not _closed_quote_after_awk(logical):
                    single_body = True
        if pending and generic_heredoc is None:
            _awk_value_findings(findings, rel, pending_line, pending)
            if is_awk or single_body or heredoc is not None or _single_quoted_awk_body(pending) is not None:
                _awk_body_findings(findings, rel, pending_line, pending)
    return findings


def _awk_command(line: str) -> bool:
    return re.match(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)*awk(?:\s|$)", line) is not None


def _heredoc_delimiter(line: str) -> str | None:
    match = re.search(r"<<\s*-?['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
    return match.group(1) if match is not None else None


def _closes_heredoc(line: str, delimiter: str) -> bool:
    return re.fullmatch(rf"\s*{re.escape(delimiter)}\s*", line) is not None or re.search(
        rf"['\"]{re.escape(delimiter)}['\"]", line
    ) is not None


def _awk_value_findings(findings: list[str], rel: str, number: int, line: str) -> None:
    if re.match(r"^\s*#", line) or _suppressed(line, "lint-awk-multibyte-regex") or not _awk_command(line):
        return
    for match in re.finditer(r"-v\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"\\]+))", line):
        value = next(item for item in match.groups() if item is not None)
        if _has_nonascii(value):
            findings.append(_report(rel, number, f"lint-awk-multibyte-regex: awk-v-nonascii: {line[:120]}"))
            return


def _awk_body_findings(findings: list[str], rel: str, number: int, line: str) -> None:
    if re.match(r"^\s*#", line) or _suppressed(line, "lint-awk-multibyte-regex") or not _has_nonascii(line):
        return
    if re.search(r"(^|[^A-Za-z0-9_])(match|gsub|sub|split)\(", line) or re.search(r"\s!?(?:~)\s", line):
        findings.append(_report(rel, number, f"lint-awk-multibyte-regex: awk-body-nonascii-regex: {line[:120]}"))


def _single_quoted_awk_body(line: str) -> str | None:
    match = re.search(r"(?<![A-Za-z0-9_])awk(?:\s+-v\s+[A-Za-z_][A-Za-z0-9_]*(?:\s*=\s*(?:'[^']*'|\"[^\"]*\"|\S+))?)*\s+('.*)$", line)
    return match.group(1) if match is not None else None


def _closed_quote_after_awk(line: str) -> bool:
    body = _single_quoted_awk_body(line)
    return body is not None and body.count("'") >= _CLOSED_QUOTE_COUNT


_BASH32_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("declare -A associative arrays", re.compile(r"(^|[\s;|&({])declare\s+(?:-[A-Za-z]+\s+)*-[A-Za-z]*A[A-Za-z]*(?:[\s;|&)]|$)")),
    ("typeset -A associative arrays", re.compile(r"(^|[\s;|&({])typeset\s+(?:-[A-Za-z]+\s+)*-[A-Za-z]*A[A-Za-z]*(?:[\s;|&)]|$)")),
    ("mapfile/readarray", re.compile(r"(^|[\s;|&({])(mapfile|readarray)(?:[\s;|&)]|$)")),
    ("parameter case conversion", re.compile(r"\$\{[!A-Za-z_@*][A-Za-z0-9_]*\^\^?|\$\{[!A-Za-z_@*][A-Za-z0-9_]*,,?")),
    ("declare -n nameref", re.compile(r"(^|[\s;|&({])declare\s+(?:-[A-Za-z]+\s+)*-[A-Za-z]*n[A-Za-z]*(?:[\s;|&)]|$)")),
    ("local -n nameref", re.compile(r"(^|[\s;|&({])local\s+(?:-[A-Za-z]+\s+)*-[A-Za-z]*n[A-Za-z]*(?:[\s;|&)]|$)")),
    ("&>> append-all redirection", re.compile(r"&>>")),
    ("coproc", re.compile(r"(^|[\s;|&({])coproc(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{")),
    ("negative array index ${arr[-N]}", re.compile(r"\$\{[!A-Za-z_@*][A-Za-z0-9_]*\[\s*-[0-9]")),
    ("step brace expansion {x..y..incr}", re.compile(r"\{(?:-?[0-9]+|[A-Za-z])\.\.(?:-?[0-9]+|[A-Za-z])\.\.-?[0-9]")),
    ("if/elif command grep-family condition", re.compile(r"(^|[\s;|&(])(if|elif)\s+(!\s+)?command\s+(grep|egrep|fgrep|rg|ripgrep)(?:[\s;|&)]|$)")),
)


def _bash32_baseline(root: Path) -> set[tuple[str, str]]:
    path = root / _BASH32_BASELINE
    if not path.is_file():
        return set()
    rows: set[tuple[str, str]] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) == _BASELINE_COLUMNS and all(parts):
            rows.add((parts[0], parts[1]))
    return rows


def scan_bash32(root: Path, requested: Iterable[str] = ()) -> tuple[list[str], list[str]]:
    """Find Bash 3.2-incompatible constructs and return skip diagnostics."""
    paths: list[Path] = []
    skipped: list[str] = []
    values = list(requested)
    if not values:
        paths = _residual_shell_paths(root)
    else:
        for value in values:
            if not value.endswith(_SHELL_SUFFIXES):
                skipped.append(f"lint-bash32: skipping non-shell path: {value}")
                continue
            candidate = Path(value)
            absolute = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
            try:
                _ = absolute.relative_to(root)
            except ValueError:
                skipped.append(f"lint-bash32: skipping path outside lint root: {value}")
                continue
            paths.append(absolute)
    baseline = _bash32_baseline(root)
    findings: list[str] = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        rel = _repo_path(root, path)
        empty_arrays: set[str] = set()
        guard_depth: dict[str, int] = {}
        depth = 0
        for number, line in enumerate(_read_lines(path) or [], start=1):
            if "lint-bash32: ok" in line or re.match(r"^\s*#", line):
                continue
            guarded = set(re.findall(r"\$\{#([A-Za-z_][A-Za-z0-9_]*)\[@\]\}", line))
            for name, values_text in re.findall(r"(?:^|[\s;|&({])([A-Za-z_][A-Za-z0-9_]*)=\(([^)]*)\)", line):
                if values_text.strip():
                    empty_arrays.discard(name)
                    _ = guard_depth.pop(name, None)
                else:
                    empty_arrays.add(name)
                    _ = guard_depth.pop(name, None)
            opens = bool(re.search(r"(^|[\s;|&({])if\s+", line) and re.search(r"(^|[\s;|&({])then(?:[\s;|&)]|$)", line))
            for name in guarded:
                if opens:
                    guard_depth[name] = depth + 1
            for name in empty_arrays:
                for suffix in ("@", "*"):
                    if f"${{{name}[{suffix}]}}" in line and name not in guarded and depth < guard_depth.get(name, 10**9) and (rel, name) not in baseline:
                        findings.append(_report(rel, number, f"lint-bash32: Bash 3.2 incompatible: unguarded empty-array expansion ${{{name}[{suffix}]}}"))  # noqa: PERF401 - preserve one finding per matched expansion
            if opens:
                depth += 1
            if re.search(r"(^|[\s;|&({])fi(?:[\s;|&)]|$)", line) and depth:
                depth -= 1
            for label, pattern in _BASH32_RULES:
                if pattern.search(line):
                    findings.append(_report(rel, number, f"lint-bash32: Bash 3.2 incompatible: {label}"))
    return findings, skipped


def main(kind: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"cli.py lint {kind}")
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    if kind == "bash32":
        _ = parser.add_argument("files", nargs="*")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"lint-{kind}: --root is not a directory: {root}", file=sys.stderr)
        return 2
    if kind == "awk-multibyte-regex":
        findings = scan_awk_multibyte(root)
        diagnostics: list[str] = []
    else:
        findings, diagnostics = scan_bash32(root, args.files)
    for value in diagnostics + findings:
        print(value, file=sys.stderr)
    return 1 if findings else 0
