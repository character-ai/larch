"""Assert larch readability directives stay wired to the shared preamble."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

EXTERNAL_STYLE_LINE = "Style requirements: `<READABILITY_STYLE>`."
PLAN_REVIEW_STYLE_LINE = "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`."
PUBLIC_STYLE_PATH = "${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md"
DEV_STYLE_PATH = "$PWD/skills/shared/readability-style.md"
MANIFEST_COLUMN_COUNT = 5
COUNTED_VARIANTS = {"orchestrator-inline", "external-prompt"}
METADATA_FLOOR_VARIANT = "metadata-min-count"
SKILL_EXEMPT_VARIANT = "skill-exempt"
MANDATORY_DIRECTIVE_RE = re.compile(r"MANDATORY:\s+READ\s+ENTIRE\s+FILE", re.IGNORECASE)


@dataclass(frozen=True)
class ManifestRow:
    path: str
    variant: str
    expected_count: int
    prompt_kind: str
    step_markers: str


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint readability-preamble", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _manifest_rows(manifest: Path) -> tuple[int, list[ManifestRow]]:
    if not manifest.is_file():
        print(f"lint-readability-preamble.sh: manifest not found: {manifest}", file=sys.stderr)
        return 2, []
    rows: list[ManifestRow] = []
    for row_num, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        while len(parts) < MANIFEST_COLUMN_COUNT:
            parts.append("")
        path, variant, expected_count, prompt_kind, step_markers = parts[:MANIFEST_COLUMN_COUNT]
        if not path or not variant:
            print(
                f"lint-readability-preamble.sh: invalid manifest row {row_num} in {manifest}: path and variant are required",
                file=sys.stderr,
            )
            return 2, []
        if not expected_count.isdigit():
            print(
                f"lint-readability-preamble.sh: invalid expected_count in {manifest} for row {path}",
                file=sys.stderr,
            )
            return 2, []
        rows.append(
            ManifestRow(
                path=path,
                variant=variant,
                expected_count=int(expected_count),
                prompt_kind=prompt_kind,
                step_markers=step_markers,
            )
        )
    return 0, rows


def _style_path_for_row(rel_path: str) -> str:
    if rel_path.startswith(".claude/skills/"):
        return DEV_STYLE_PATH
    return PUBLIC_STYLE_PATH


def _orchestrator_anchor(rel_path: str) -> str:
    return f"`{_style_path_for_row(rel_path)}`.**"


def _orchestrator_style_re(*, rel_path: str) -> re.Pattern[str]:
    style_path = re.escape(_style_path_for_row(rel_path))
    return re.compile(
        rf"^\*\*{MANDATORY_DIRECTIVE_RE.pattern}.*`{style_path}`\.\*\*$",
        re.IGNORECASE,
    )


def check_step_placement(*, text: str, rel_path: str, step_markers: str) -> bool:
    ok = True
    lines = text.splitlines()
    anchor = _orchestrator_anchor(rel_path)
    for raw_step in step_markers.split(","):
        step_id = raw_step.strip()
        if not step_id:
            continue
        in_step = False
        found_marker = False
        count = 0
        failed = False
        marker_re = re.compile(rf"^<!--\s*step:{re.escape(step_id)}(?:\s|:)")
        for line in lines:
            if marker_re.match(line):
                if in_step and found_marker and count < 1:
                    print(
                        f'{rel_path}: step "{step_id}": expected >=1 orchestrator-inline readability-style directive in step body, found 0',
                        file=sys.stderr,
                    )
                    failed = True
                    break
                in_step = True
                found_marker = True
                count = 0
                continue
            if in_step and line.startswith("<!-- step:"):
                if count < 1:
                    print(
                        f'{rel_path}: step "{step_id}": expected >=1 orchestrator-inline readability-style directive in step body, found 0',
                        file=sys.stderr,
                    )
                    failed = True
                in_step = False
                count = 0
                if failed:
                    break
            if in_step and anchor in line:
                count += 1
        if failed:
            ok = False
            continue
        if not found_marker:
            print(f'{rel_path}: step "{step_id}": orchestrator-inline step marker not found', file=sys.stderr)
            ok = False
        elif in_step and count < 1:
            print(
                f'{rel_path}: step "{step_id}": expected >=1 orchestrator-inline readability-style directive in step body, found 0',
                file=sys.stderr,
            )
            ok = False
    return ok


def _count_exact(*, text: str, needle: str) -> int:
    return sum(1 for line in text.splitlines() if line == needle)


def _count_orchestrator_directives(*, text: str, rel_path: str) -> int:
    style_re = _orchestrator_style_re(rel_path=rel_path)
    return sum(1 for line in text.splitlines() if style_re.search(line))


def _check_external_prompt(*, row: ManifestRow, text: str) -> bool:
    if (row.prompt_kind or "standard") == "plan-review":
        count = _count_exact(text=text, needle=PLAN_REVIEW_STYLE_LINE)
    else:
        count = _count_exact(text=text, needle=EXTERNAL_STYLE_LINE)
    if count == row.expected_count:
        return True
    print(
        f"{row.path}: expected {row.expected_count} external-prompt readability-style directives, found {count}",
        file=sys.stderr,
    )
    return False


def _check_orchestrator(*, row: ManifestRow, text: str) -> bool:
    count = _count_orchestrator_directives(text=text, rel_path=row.path)
    if count != row.expected_count:
        print(
            f"{row.path}: expected {row.expected_count} orchestrator-inline readability-style directives, found {count}",
            file=sys.stderr,
        )
        return False
    return not row.step_markers or check_step_placement(text=text, rel_path=row.path, step_markers=row.step_markers)


def _check_counted_row(*, root: Path, row: ManifestRow) -> bool | None:
    file_path = root / row.path
    if not file_path.is_file():
        print(f"{row.path}: missing {row.variant} readability-style directive", file=sys.stderr)
        return False
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if row.variant == "external-prompt":
        return _check_external_prompt(row=row, text=text)
    if row.variant == "orchestrator-inline":
        return _check_orchestrator(row=row, text=text)
    return None


def _skill_files(root: Path) -> tuple[Path, ...]:
    public = sorted((root / "skills").glob("*/SKILL.md"))
    dev = sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    return tuple(path for path in (*public, *dev) if path.is_file() and not path.is_symlink())


def _agent_files(root: Path) -> tuple[Path, ...]:
    agents = root / "agents"
    paths = [agents / "code-reviewer.md", *sorted(agents.glob("reviewer-*.md"))]
    return tuple(path for path in paths if path.is_file() and not path.is_symlink())


def _skill_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _check_skill_path_form(*, root: Path, exemptions: set[str]) -> bool:
    ok = True
    for path in _skill_files(root):
        rel = _skill_rel(path, root)
        text = path.read_text(encoding="utf-8", errors="replace")
        if rel in exemptions:
            continue
        expected = _style_path_for_row(rel)
        forbidden = PUBLIC_STYLE_PATH if expected == DEV_STYLE_PATH else DEV_STYLE_PATH
        style_re = _orchestrator_style_re(rel_path=rel)
        if not any(style_re.search(line) for line in text.splitlines()):
            print(f"{rel}: missing per-skill readability directive for {expected}", file=sys.stderr)
            ok = False
        if forbidden in text:
            print(f"{rel}: uses wrong readability directive path form", file=sys.stderr)
            ok = False
    return ok


def _check_agent_path_form(*, root: Path) -> bool:
    ok = True
    for path in _agent_files(root):
        rel = _skill_rel(path, root)
        text = path.read_text(encoding="utf-8", errors="replace")
        expected = _style_path_for_row(rel)
        style_re = _orchestrator_style_re(rel_path=rel)
        if not any(style_re.search(line) for line in text.splitlines()):
            print(f"{rel}: missing reviewer readability directive for {expected}", file=sys.stderr)
            ok = False
        if DEV_STYLE_PATH in text:
            print(f"{rel}: uses wrong readability directive path form", file=sys.stderr)
            ok = False
    return ok


def _check_exemption_rows(rows: list[ManifestRow]) -> tuple[bool, set[str]]:
    ok = True
    exemptions: set[str] = set()
    for row in rows:
        if row.variant != SKILL_EXEMPT_VARIANT:
            continue
        reason = row.prompt_kind or row.step_markers
        if row.expected_count != 0 or not reason.strip():
            print(
                f"lint-readability-preamble.sh: invalid skill exemption row for {row.path}: expected_count must be 0 and reason required",
                file=sys.stderr,
            )
            ok = False
        exemptions.add(row.path)
    return ok, exemptions


def _check_floor(rows: list[ManifestRow]) -> bool:
    floors = [row.expected_count for row in rows if row.variant == METADATA_FLOOR_VARIANT]
    if len(floors) > 1:
        print("lint-readability-preamble.sh: duplicate metadata-min-count rows", file=sys.stderr)
        return False
    if not floors:
        return True
    total = sum(row.expected_count for row in rows if row.variant in COUNTED_VARIANTS)
    if total >= floors[0]:
        return True
    print(
        f"lint-readability-preamble.sh: expected_count floor {floors[0]} exceeds manifest total {total}",
        file=sys.stderr,
    )
    return False


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv=argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(parsed.root)
    manifest = root / "scripts" / "lint-readability-preamble.tsv"
    rc, rows = _manifest_rows(manifest)
    if rc != 0:
        return rc
    exempt_ok, exemptions = _check_exemption_rows(rows)
    if not exempt_ok:
        return 2
    missing = False
    if not _check_floor(rows):
        missing = True
    for row in rows:
        if row.variant in {METADATA_FLOOR_VARIANT, SKILL_EXEMPT_VARIANT}:
            continue
        if row.variant not in COUNTED_VARIANTS:
            print(f"lint-readability-preamble.sh: unknown manifest variant: {row.variant}", file=sys.stderr)
            return 2
        row_ok = _check_counted_row(root=root, row=row)
        if row_ok is False:
            missing = True
    if not _check_skill_path_form(root=root, exemptions=exemptions):
        missing = True
    if not _check_agent_path_form(root=root):
        missing = True
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
