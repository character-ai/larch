"""Unit coverage for the Python residual-Bash linter implementations."""

from __future__ import annotations

from pathlib import Path

from larch.lint.engine import fenced_markdown_lines
from larch.lint.shell_lints import scan_awk_multibyte, scan_bare_grep, scan_bash32


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_fenced_markdown_lines_tracks_matching_markers() -> None:
    lines = ["````bash", "rg pattern", "```", "rg outside", "````"]
    active = [(line.number, line.language) for line in fenced_markdown_lines(lines)]
    assert active == [(1, None), (2, "bash"), (3, "bash"), (4, "bash"), (5, "bash")]


def test_bare_grep_scans_only_bash_fences(tmp_path: Path) -> None:
    _write(tmp_path, "skills/demo/SKILL.md", "```bash\nrg PATTERN\n```\n```python\nrg PATTERN\n```\n")
    findings = scan_bare_grep(tmp_path)
    assert len(findings) == 1
    assert "skills/demo/SKILL.md:2:" in findings[0]


def test_awk_multibyte_scans_manifest_shell_and_awk_files(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/residual-bash-paths.txt", "scripts/in-scope.sh\n")
    _write(tmp_path, "scripts/in-scope.sh", "awk 'match($0, \"—\")'\n")
    _write(tmp_path, "scripts/standalone.awk", 'BEGIN { match($0, "—") }\n')
    findings = scan_awk_multibyte(tmp_path)
    assert {item.split(":", 1)[0] for item in findings} == {
        "scripts/in-scope.sh",
        "scripts/standalone.awk",
    }


def test_bash32_scans_requested_paths_only(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/a.sh", "declare -A seen=()\n")
    _write(tmp_path, "scripts/b.sh", "declare -A skipped=()\n")
    findings, diagnostics = scan_bash32(tmp_path, ["scripts/a.sh"])
    assert not diagnostics
    assert len(findings) == 1
    assert "scripts/a.sh:1:" in findings[0]
