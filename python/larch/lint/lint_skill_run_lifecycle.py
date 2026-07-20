"""Require every public and developer skill to use the shared run lifecycle."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

from larch.core import config
from larch.lint.engine import EXIT_CLEAN, EXIT_ERROR, EXIT_FINDINGS, RuleCli, run_root_cli

_MARKER_PARTS: Final = config.SKILL_LIFECYCLE_MARKER_TEMPLATE.partition("{skill}")
_MARKER_PREFIX: Final = _MARKER_PARTS[0]
_MARKER_FIELD: Final = _MARKER_PARTS[1]
_MARKER_SUFFIX: Final = _MARKER_PARTS[2]
if _MARKER_FIELD != "{skill}":
    raise RuntimeError("skill lifecycle marker template must contain {skill}")
SHARED_MARKER_RE: Final = re.compile(
    rf"^{re.escape(_MARKER_PREFIX)}([a-z0-9][a-z0-9-]*){re.escape(_MARKER_SUFFIX)}$",
    re.MULTILINE,
)
ALLOWED_TOOLS_RE: Final = re.compile(r"^allowed-tools:\s*([^\n]+)$", re.MULTILINE)
MARKER_PREFIX: Final = "# larch-run-lifecycle:"
SHARED_CONTRACT: Final = Path("skills/shared/run-lifecycle.md")
SHARED_REFERENCE: Final = "skills/shared/run-lifecycle.md"
SKILL_ROOTS: Final = (Path("skills"), Path(".claude/skills"))
REQUIRED_TERMINAL_VERBS: Final = (
    "lifecycle-finalize",
    "lifecycle-failure",
    "lifecycle-cancel",
    "lifecycle-early-return",
)


def _skill_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for relative_root in SKILL_ROOTS:
        skills = root / relative_root
        if skills.is_symlink() or not skills.is_dir():
            raise OSError(f"skill directory is missing or unsafe: {skills}")
        for child in sorted(skills.iterdir(), key=lambda item: item.name):
            if child.name == "shared":
                continue
            if child.is_symlink():
                raise OSError(f"skill directory is a symlink: {child}")
            if not child.is_dir():
                continue
            prompt = child / "SKILL.md"
            if prompt.is_symlink():
                raise OSError(f"skill prompt is a symlink: {prompt}")
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
            f"{relative_path}: missing shared run lifecycle declaration"
        ]
    if len(marker_lines) != 1:
        return [f"{relative_path}: expected exactly one run lifecycle declaration"]
    marker = marker_lines[0]
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
    instruction = config.SKILL_LIFECYCLE_INSTRUCTION_TEMPLATE.format(skill=skill)
    if text.count(instruction) != 1:
        return [
            f"{relative_path}: shared lifecycle declaration must include its exact "
            "mandatory instruction once"
        ]
    allowed_tools = ALLOWED_TOOLS_RE.search(text)
    if allowed_tools is not None and not any(
        tool.strip() == "Bash" or tool.strip().startswith("Bash(")
        for tool in allowed_tools.group(1).split(",")
    ):
        return [
            f"{relative_path}: shared lifecycle declaration requires Bash permission"
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
