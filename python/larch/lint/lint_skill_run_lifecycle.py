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
OWNERSHIP_REGISTRY: Final = Path("skills/shared/run-lifecycle-ownership.tsv")
SHARED_REFERENCE: Final = "skills/shared/run-lifecycle.md"
SKILL_ROOTS: Final = (Path("skills"), Path(".claude/skills"))
REQUIRED_TERMINAL_VERBS: Final = (
    "lifecycle-finalize",
    "lifecycle-failure",
    "lifecycle-cancel",
    "lifecycle-early-return",
)
_OWNER_HEADER: Final = "skill\tstart_owner\tterminal_owner\tno_archive_exception"
_DIRECT_PUBLISHER_TOKENS: Final = ("run-log publish", "publish_log_run(")
_PYTHON_PUBLISHER_ALLOWLIST: Final = frozenset({Path("python/larch/report/run_lifecycle.py"), Path("python/larch/report/run_log_publish.py"), Path("python/larch/lint/lint_skill_run_lifecycle.py")})
_CHILD_SKILL_ARGS_RE: Final = re.compile(
    r"^Invoke the Skill tool:\n(?:^[ \t]*$\n|^- (?!args:).*$\n)*?^- args: (?P<args>[^\n]+)$",
    re.MULTILINE,
)
_CHILD_CONTEXT_PREFIX: Final = '--lifecycle-parent-context "$CONTEXT_FILE" '


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


def _ownership_rows(root: Path) -> tuple[dict[str, tuple[Path, Path, str]], list[str]]:
    path = root / OWNERSHIP_REGISTRY
    if path.is_symlink() or not path.is_file():
        return {}, [f"{OWNERSHIP_REGISTRY}: ownership registry is missing or unsafe"]
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != _OWNER_HEADER:
        return {}, [f"{OWNERSHIP_REGISTRY}: invalid ownership registry header"]
    rows: dict[str, tuple[Path, Path, str]] = {}
    findings: list[str] = []
    for line_number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(_OWNER_HEADER.split("\t")) or not all(fields):
            findings.append(f"{OWNERSHIP_REGISTRY}:{line_number}: expected four non-empty fields")
            continue
        skill, start_owner, terminal_owner, exception = fields
        if skill in rows:
            findings.append(f"{OWNERSHIP_REGISTRY}:{line_number}: duplicate skill {skill!r}")
            continue
        rows[skill] = (Path(start_owner), Path(terminal_owner), exception)
    if "*" not in rows:
        findings.append(f"{OWNERSHIP_REGISTRY}: missing default '*' ownership row")
    return rows, findings


def _owner_file_findings(*, root: Path, skill: str, role: str, relative_path: Path) -> list[str]:
    path = root / relative_path
    if path.is_symlink() or not path.is_file():
        return [f"{OWNERSHIP_REGISTRY}: {skill} {role} owner is missing or unsafe: {relative_path}"]
    text = path.read_text(encoding="utf-8")
    if role == "start":
        wired = "lifecycle-start" in text or "run_lifecycle.start_run(" in text
    else:
        wired = any(verb in text for verb in REQUIRED_TERMINAL_VERBS) or "run_lifecycle.finish_run(" in text
    if not wired:
        return [f"{OWNERSHIP_REGISTRY}: {skill} {role} owner is not lifecycle-wired: {relative_path}"]
    return []


def _publisher_findings(root: Path, prompts: list[Path]) -> list[str]:
    findings: list[str] = []
    for prompt in prompts:
        text = prompt.read_text(encoding="utf-8")
        if any(token in text for token in _DIRECT_PUBLISHER_TOKENS):
            findings.append(f"{prompt.relative_to(root).as_posix()}: direct terminal publisher bypasses lifecycle ownership")
    production = root / "python" / "larch"
    for path in sorted(production.rglob("*.py")):
        relative = path.relative_to(root)
        if relative in _PYTHON_PUBLISHER_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        if "publish_log_run(" in text:
            findings.append(f"{relative.as_posix()}: second terminal run-log publisher bypasses lifecycle ownership")
    return findings


def _child_handoff_findings(root: Path, prompts: list[Path]) -> list[str]:
    findings: list[str] = []
    for prompt in prompts:
        relative = prompt.relative_to(root).as_posix()
        findings.extend(
            f"{relative}: child Skill call omits leading lifecycle parent-context handoff"
            for match in _CHILD_SKILL_ARGS_RE.finditer(prompt.read_text(encoding="utf-8"))
            if not match.group("args").startswith(_CHILD_CONTEXT_PREFIX)
        )
    return findings


def lint_root(root: Path) -> int:
    """Scan the complete shipped skill inventory and print findings."""
    try:
        findings = _shared_contract_findings(root)
        prompts = _skill_files(root)
        rows, registry_findings = _ownership_rows(root)
        findings.extend(registry_findings)
        skill_names = {prompt.parent.name for prompt in prompts}
        for registered in sorted(set(rows) - {"*"} - skill_names):
            findings.append(f"{OWNERSHIP_REGISTRY}: ownership row has no shipped skill: {registered}")
        default = rows.get("*")
        for prompt in prompts:
            relative = prompt.relative_to(root).as_posix()
            skill = prompt.parent.name
            findings.extend(
                lint_skill_text(
                    relative_path=relative,
                    skill=skill,
                    text=prompt.read_text(encoding="utf-8"),
                )
            )
            ownership = rows.get(skill, default)
            if ownership is None:
                findings.append(f"{relative}: no lifecycle ownership row resolves")
                continue
            start_owner, terminal_owner, exception = ownership
            if exception not in {"-", "no-logs-commit"}:
                findings.append(f"{OWNERSHIP_REGISTRY}: unsupported no-archive exception for {skill}: {exception}")
            findings.extend(_owner_file_findings(root=root, skill=skill, role="start", relative_path=start_owner))
            findings.extend(_owner_file_findings(root=root, skill=skill, role="terminal", relative_path=terminal_owner))
        findings.extend(_publisher_findings(root, prompts))
        findings.extend(_child_handoff_findings(root, prompts))
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
