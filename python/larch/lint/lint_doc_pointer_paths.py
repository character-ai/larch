"""Reject dead path-shaped inline-backtick pointers in Tier-1 docs.

Scans ``AGENTS.md`` and ``SECURITY.md`` for inline backtick tokens that look
like repository-relative file paths. Tokens with an approved prefix, a slash,
and no placeholder or whitespace characters must resolve to an existing file
under the repository root. Fenced code blocks are skipped. Same-line
suppressions require a non-empty reason.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TOOL_FAILURE_EXIT = 2
DOCUMENTS = ("AGENTS.md", "SECURITY.md")
APPROVED_PREFIXES = (
    "python/",
    "skills/",
    "scripts/",
    "docs/",
    "hooks/",
    "agents/",
    ".claude/",
    ".claude-plugin/",
    ".github/",
)
FORBIDDEN_CHARS = frozenset("<>*${}? ")
TOKEN_RE = re.compile(r"`([^`\n]+)`")
SUPPRESSION_RE = re.compile(
    r"<!--\s*lint-doc-pointer-paths:\s*ok(?:\s+(\S[^>]*?)|\s*)\s*-->"
)
SKIP_PREFIX = "larch-logs/"


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int
    token: str
    message: str


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint doc-pointer-paths",
        description=__doc__,
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _is_candidate_token(token: str) -> bool:
    if "/" not in token:
        return False
    if any(ch in token for ch in FORBIDDEN_CHARS):
        return False
    if token.startswith(SKIP_PREFIX):
        return False
    return token.startswith(APPROVED_PREFIXES)


def _probe_path(token: str) -> str:
    return token.split("::", 1)[0].split("#", 1)[0]


def _path_escapes_root(*, root: Path, probe: str) -> bool:
    if not probe or Path(probe).is_absolute():
        return True
    candidate = (root / probe).resolve()
    try:
        _ = candidate.relative_to(root.resolve())
    except ValueError:
        return True
    return ".." in Path(probe).parts


def _open_required_doc(*, root: Path, relpath: str) -> tuple[Path, str] | Finding:
    path = root / relpath
    if path.is_symlink():
        return Finding(
            file=relpath,
            lineno=0,
            token="",
            message=f"{relpath}: refusing symlink input",
        )
    if not path.exists():
        return Finding(
            file=relpath,
            lineno=0,
            token="",
            message=f"{relpath}: missing required Tier-1 document",
        )
    if not path.is_file():
        return Finding(
            file=relpath,
            lineno=0,
            token="",
            message=f"{relpath}: not a regular file",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return Finding(
            file=relpath,
            lineno=0,
            token="",
            message=f"{relpath}: unreadable: {exc}",
        )
    return path, text


def scan_document(*, root: Path, relpath: str, text: str) -> list[Finding]:
    """Return findings for one Tier-1 Markdown document body."""
    findings: list[Finding] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        suppression = SUPPRESSION_RE.search(line)
        if suppression is not None:
            reason = (suppression.group(1) or "").strip()
            if not reason:
                findings.append(
                    Finding(
                        file=relpath,
                        lineno=lineno,
                        token="<!-- lint-doc-pointer-paths: ok -->",  # noqa: S106 - literal suppression marker text, not a credential
                        message=(
                            f"{relpath}:{lineno}: empty lint-doc-pointer-paths "
                            "suppression reason"
                        ),
                    )
                )
                # Empty-reason pragma is itself a finding; still scan tokens
                # on the line so callers see every problem in one run.
            else:
                continue

        for token in TOKEN_RE.findall(line):
            if not _is_candidate_token(token):
                continue
            probe = _probe_path(token)
            if _path_escapes_root(root=root, probe=probe):
                findings.append(
                    Finding(
                        file=relpath,
                        lineno=lineno,
                        token=token,
                        message=(
                            f"{relpath}:{lineno}: dead or escaping doc pointer "
                            f"`{token}`"
                        ),
                    )
                )
                continue
            candidate = root / probe
            if candidate.is_symlink() or not candidate.exists():
                findings.append(
                    Finding(
                        file=relpath,
                        lineno=lineno,
                        token=token,
                        message=f"{relpath}:{lineno}: dead doc pointer `{token}`",
                    )
                )
    return findings


def check_root(root: Path) -> tuple[int, list[Finding]]:
    """Return ``(exit_code, findings)`` for the Tier-1 doc-pointer scan."""
    if not root.is_dir():
        return TOOL_FAILURE_EXIT, [
            Finding(
                file="",
                lineno=0,
                token="",
                message=f"lint-doc-pointer-paths: --root is not a directory: {root}",
            )
        ]

    findings: list[Finding] = []
    for relpath in DOCUMENTS:
        opened = _open_required_doc(root=root, relpath=relpath)
        if isinstance(opened, Finding):
            return TOOL_FAILURE_EXIT, [opened]
        _path, text = opened
        findings.extend(scan_document(root=root, relpath=relpath, text=text))

    findings.sort(key=lambda item: (item.file, item.lineno, item.token))
    return (1 if findings else 0), findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint doc-pointer-paths``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    code, findings = check_root(root)
    for finding in findings:
        print(finding.message, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
