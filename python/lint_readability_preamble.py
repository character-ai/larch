"""Assert every /design readability amendment site references the shared preamble."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXTERNAL_STYLE_LINE = "Style requirements: `<READABILITY_STYLE>`."
PLAN_REVIEW_STYLE_LINE = "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`."
ORCHESTRATOR_STYLE_ANCHOR = "readability-style.md`.**"
MANIFEST_COLUMN_COUNT = 5


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint readability-preamble", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _manifest_rows(manifest: Path) -> tuple[int, list[tuple[str, str, str, str, str]]]:
    if not manifest.is_file():
        print(f"lint-readability-preamble.sh: manifest not found: {manifest}", file=sys.stderr)
        return 2, []
    rows: list[tuple[str, str, str, str, str]] = []
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        while len(parts) < MANIFEST_COLUMN_COUNT:
            parts.append("")
        path, variant, expected_count, prompt_kind, step_markers = parts[:MANIFEST_COLUMN_COUNT]
        if not expected_count.isdigit():
            print(
                f"lint-readability-preamble.sh: invalid expected_count in {manifest} for row {path}",
                file=sys.stderr,
            )
            return 2, []
        rows.append((path, variant, expected_count, prompt_kind, step_markers))
    return 0, rows


def check_step_placement( *,text: str, rel_path: str, step_markers: str) -> bool:
    ok = True
    lines = text.splitlines()
    for raw_step in step_markers.split(","):
        step_id = raw_step.strip()
        if not step_id:
            continue
        in_step = False
        found_marker = False
        count = 0
        failed = False
        for line in lines:
            if line.startswith(f"<!-- step:{step_id} "):
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
            if in_step and ORCHESTRATOR_STYLE_ANCHOR in line:
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


def _count_exact( *,text: str, needle: str) -> int:
    return sum(1 for line in text.splitlines() if line == needle)


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv=argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(parsed.root)
    manifest = root / "scripts" / "lint-readability-preamble.tsv"
    rc, rows = _manifest_rows(manifest)
    if rc != 0:
        return rc
    missing = False
    for path, variant, expected_count_text, prompt_kind, step_markers in rows:
        expected_count = int(expected_count_text)
        file_path = root / path
        ok = False
        count_message_emitted = False
        if file_path.is_file():
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if variant == "external-prompt":
                if (prompt_kind or "standard") == "plan-review":
                    count = _count_exact(text=text, needle=PLAN_REVIEW_STYLE_LINE)
                else:
                    count = _count_exact(text=text, needle=EXTERNAL_STYLE_LINE)
                if count == expected_count:
                    ok = True
                else:
                    print(
                        f"{path}: expected {expected_count} external-prompt readability-style directives, found {count}",
                        file=sys.stderr,
                    )
                    count_message_emitted = True
            elif variant == "orchestrator-inline":
                count = text.count(ORCHESTRATOR_STYLE_ANCHOR)
                if count == expected_count:
                    ok = True
                else:
                    print(
                        f"{path}: expected {expected_count} orchestrator-inline readability-style directives, found {count}",
                        file=sys.stderr,
                    )
                    count_message_emitted = True
                if ok and step_markers and not check_step_placement(text=text, rel_path=path, step_markers=step_markers):
                    ok = False
            else:
                print(f"lint-readability-preamble.sh: unknown manifest variant: {variant}", file=sys.stderr)
                return 2
        if not ok:
            if not count_message_emitted:
                print(f"{path}: missing {variant} readability-style directive", file=sys.stderr)
            missing = True
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
