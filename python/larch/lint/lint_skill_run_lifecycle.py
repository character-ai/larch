"""Require every shipped skill to declare shared run lifecycle wiring or migration debt."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

from larch.lint.engine import EXIT_CLEAN, EXIT_ERROR, EXIT_FINDINGS, RuleCli, run_root_cli

SHARED_MARKER_RE: Final = re.compile(
    r"^# larch-run-lifecycle: shared-v1 skill=([a-z0-9][a-z0-9-]*)$",
    re.MULTILINE,
)
MIGRATION_MARKER: Final = "# pending:7827"
MARKER_PREFIX: Final = "# larch-run-lifecycle:"
SHARED_CONTRACT: Final = Path("skills/shared/run-lifecycle.md")
SHARED_REFERENCE: Final = "skills/shared/run-lifecycle.md"
REQUIRED_TERMINAL_VERBS: Final = (
    "lifecycle-finalize",
    "lifecycle-failure",
    "lifecycle-cancel",
    "lifecycle-early-return",
)


def _skill_files(root: Path) -> list[Path]:
    skills = root / "skills"
    if skills.is_symlink() or not skills.is_dir():
        raise OSError(f"shipped skills directory is missing or unsafe: {skills}")
    found: list[Path] = []
    for child in sorted(skills.iterdir(), key=lambda item: item.name):
        if child.name == "shared":
            continue
        if child.is_symlink():
            raise OSError(f"shipped skill directory is a symlink: {child}")
        if not child.is_dir():
            continue
        prompt = child / "SKILL.md"
        if prompt.is_symlink():
            raise OSError(f"shipped skill prompt is a symlink: {prompt}")
        if not prompt.is_file():
            continue
        found.append(prompt)
    return found


def lint_skill_text(  # noqa: PLR0911 - each malformed declaration class returns one stable finding.
    *, relative_path: str, skill: str, text: str
) -> list[str]:
    """Return stable lifecycle-declaration findings for one shipped skill prompt."""
    marker_lines = [
        line
        for line in text.splitlines()
        if MARKER_PREFIX in line or line.startswith("# pending:")
    ]
    if not marker_lines:
        return [
            f"{relative_path}: missing shared run lifecycle declaration or "
            f"exact temporary marker {MIGRATION_MARKER}"
        ]
    if len(marker_lines) != 1:
        return [f"{relative_path}: expected exactly one run lifecycle declaration"]
    marker = marker_lines[0]
    if marker == MIGRATION_MARKER:
        return []
    match = SHARED_MARKER_RE.fullmatch(marker)
    if match is None:
        return [f"{relative_path}: malformed or partial run lifecycle declaration"]
    if match.group(1) != skill:
        return [
            f"{relative_path}: declared lifecycle skill {match.group(1)!r} "
            f"does not match directory {skill!r}"
        ]
    if text.count(SHARED_REFERENCE) != 1:
        return [
            f"{relative_path}: shared lifecycle declaration must reference "
            f"{SHARED_REFERENCE} exactly once"
        ]
    return []


def _shared_contract_findings(root: Path) -> list[str]:
    path = root / SHARED_CONTRACT
    if path.is_symlink() or not path.is_file():
        return [f"{SHARED_CONTRACT}: shared lifecycle contract is missing or unsafe"]
    text = path.read_text(encoding="utf-8")
    required = ("lifecycle-start", *REQUIRED_TERMINAL_VERBS)
    missing = [verb for verb in required if text.count(verb) != 1]
    if missing:
        return [
            f"{SHARED_CONTRACT}: partially wired lifecycle contract; "
            f"expected each verb exactly once, invalid={','.join(missing)}"
        ]
    return []


def lint_root(root: Path) -> int:
    """Scan the complete shipped skill inventory and print findings."""
    try:
        findings = _shared_contract_findings(root)
        for prompt in _skill_files(root):
            relative = prompt.relative_to(root).as_posix()
            findings.extend(
                lint_skill_text(
                    relative_path=relative,
                    skill=prompt.parent.name,
                    text=prompt.read_text(encoding="utf-8"),
                )
            )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"lint-skill-run-lifecycle: {exc}", file=sys.stderr)
        return EXIT_ERROR
    for finding in findings:
        print(f"skill-run-lifecycle: {finding}", file=sys.stderr)
    return EXIT_FINDINGS if findings else EXIT_CLEAN


def main(argv: list[str] | None = None) -> int:
    """Run the shipped-skill lifecycle declaration lint."""
    return run_root_cli(
        argv or [],
        cli=RuleCli(
            prog="cli.py lint skill-run-lifecycle",
            description=__doc__,
        ),
        action=lint_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
