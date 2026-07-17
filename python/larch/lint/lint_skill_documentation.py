"""Require every shipped or dev-only skill in both public documentation catalogs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

README_PATH = Path("README.md")
SKILLS_DOCUMENT_PATH = Path("docs/skills.md")
SKILL_ROOTS = (Path("skills"), Path(".claude/skills"))
SUMMARY_TABLE_RE = re.compile(r"<table\b[^>]*>(?P<body>.*?)</table>", re.DOTALL | re.IGNORECASE)
SUMMARY_ENTRY_RE = re.compile(
    r'<td>\s*<a\s+href="docs/skills\.md#(?P<name>[a-z0-9-]+)">\s*'
    r"<code>/(?P=name)</code>\s*</a>\s*</td>",
    re.IGNORECASE,
)
MARKDOWN_SUMMARY_ENTRY_RE = re.compile(
    r"^\|\s*\[`/(?P<name>[a-z0-9-]+)`\]\(docs/skills\.md#(?P=name)\)",
    re.MULTILINE,
)
DETAIL_HEADING_RE = re.compile(r"^###\s+`/(?P<name>[a-z0-9-]+)`\s*$", re.MULTILINE)


@dataclass(frozen=True)
class DocumentedSkills:
    """Skill names found in the README summary table and detailed reference."""

    summary: frozenset[str]
    detailed: frozenset[str]


def _relative(path: Path, *, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_required_document(path: Path, *, root: Path) -> str:
    rel = _relative(path, root=root)
    try:
        if path.is_symlink():
            raise LintError(f"lint-skill-documentation: {rel}: documentation file must not be a symlink")
        if not path.is_file():
            raise LintError(f"lint-skill-documentation: required documentation file is missing: {rel}")
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LintError(f"lint-skill-documentation: {rel}: documentation is not UTF-8") from exc
    except OSError as exc:
        raise LintError(f"lint-skill-documentation: cannot read {rel}: {exc}") from exc


def documented_skills(root: Path) -> DocumentedSkills:
    """Read the two catalogs and return their documented skill names."""
    readme: str = _read_required_document(root / README_PATH, root=root)
    skills_document: str = _read_required_document(root / SKILLS_DOCUMENT_PATH, root=root)
    summary: set[str] = set()
    for table in SUMMARY_TABLE_RE.finditer(readme):
        summary.update(match.group("name") for match in SUMMARY_ENTRY_RE.finditer(table.group("body")))
    summary.update(match.group("name") for match in MARKDOWN_SUMMARY_ENTRY_RE.finditer(readme))
    detailed: frozenset[str] = frozenset(match.group("name") for match in DETAIL_HEADING_RE.finditer(skills_document))
    return DocumentedSkills(summary=frozenset(summary), detailed=detailed)


def _defined_skill_name(entry: Path, *, root: Path) -> str | None:
    """Return one skill name after validating its directory and definition file."""
    entry_label: str = _relative(entry, root=root)
    definition: Path = entry / "SKILL.md"
    try:
        if entry.is_symlink():
            raise LintError(
                f"lint-skill-documentation: skill directory must not be a symlink: {entry_label}"
            )
        if definition.is_symlink():
            definition_label: str = _relative(definition, root=root)
            raise LintError(
                f"lint-skill-documentation: skill definition must not be a symlink: {definition_label}"
            )
        if not definition.exists():
            return None
        definition_label = _relative(definition, root=root)
        if not definition.is_file():
            raise LintError(
                f"lint-skill-documentation: skill definition is not a regular file: {definition_label}"
            )
    except OSError as exc:
        raise LintError(f"lint-skill-documentation: cannot inspect {entry_label}: {exc}") from exc
    return entry.name


def _defined_skills_in_root(skill_root: Path, *, root: Path) -> set[str]:
    """Return validated direct skill names from one optional skill root."""
    root_label: str = _relative(skill_root, root=root)
    try:
        if skill_root.is_symlink():
            raise LintError(f"lint-skill-documentation: skill root must not be a symlink: {root_label}")
        if not skill_root.is_dir():
            return set()
        entries: list[Path] = sorted(skill_root.iterdir())
    except OSError as exc:
        raise LintError(f"lint-skill-documentation: cannot enumerate {root_label}: {exc}") from exc
    return {name for entry in entries if (name := _defined_skill_name(entry, root=root)) is not None}


def defined_skills(root: Path) -> frozenset[str]:
    """Return direct skill-directory names, rejecting unsafe skill definitions."""
    names: set[str] = set()
    for relative_root in SKILL_ROOTS:
        names.update(_defined_skills_in_root(root / relative_root, root=root))
    return frozenset(names)


def find_target(root: Path) -> list[Path]:
    """Return one target so the cross-document parity check runs exactly once."""
    return [root / README_PATH]


def lint_file(*, path: Path, root: Path) -> list[str]:
    """Report live/documented skill-set differences and catalog drift."""
    _ = path
    defined: frozenset[str] = defined_skills(root)
    documented: DocumentedSkills = documented_skills(root)
    return [
        *(f"lint-skill-documentation: README.md: missing summary-table entry for /{name}" for name in sorted(defined - documented.summary)),
        *(f"lint-skill-documentation: docs/skills.md: missing detailed skill heading for /{name}" for name in sorted(defined - documented.detailed)),
        *(f"lint-skill-documentation: README.md: summary-table entry /{name} has no matching skill definition" for name in sorted(documented.summary - defined)),
        *(f"lint-skill-documentation: docs/skills.md: detailed skill heading /{name} has no matching skill definition" for name in sorted(documented.detailed - defined)),
        *(f"lint-skill-documentation: README.md: summary-table entry /{name} has no matching detailed skill heading" for name in sorted(documented.summary - documented.detailed)),
        *(f"lint-skill-documentation: docs/skills.md: detailed skill heading /{name} has no matching summary-table entry" for name in sorted(documented.detailed - documented.summary)),
    ]


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-skill-documentation",
        description=(__doc__ or "").splitlines()[0],
        iter_files=find_target,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
