from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import residual_bash


def test_manifest_includes_combine_issues_helper() -> None:
    paths = residual_bash.read_residual_paths(Path(__file__).resolve().parents[1])
    assert ".claude/skills/combine-issues/scripts/search-implementing-issue.sh" in paths


def test_manifest_excludes_retired_bash_artifacts() -> None:
    paths = set(residual_bash.read_residual_paths(Path(__file__).resolve().parents[1]))
    retired = {
        "scripts/lib-quiet.sh",
        "scripts/lib-net.sh",
        "scripts/lib-redact.sh",
        "scripts/lib-execution-issues.sh",
        "scripts/lib-phantom-probe.sh",
        "scripts/lib-sparse-dirs.sh",
        "scripts/lib-larch-dev-clone.sh",
        "scripts/lib-submodule-prohibition.sh",
        "scripts/extract-closes-issue-from-pr.sh",
        "scripts/oos-disposition-shared.inc.bash",
        "scripts/run-log-terminal-outcomes.inc.bash",
    }
    assert paths.isdisjoint(retired)


def test_manifest_excludes_vendored_paths(tmp_path: Path) -> None:
    root = tmp_path
    manifest = root / "scripts" / "residual-bash-paths.txt"
    manifest.parent.mkdir()
    _ = manifest.write_text("scripts/kept.sh\nnode_modules/vendor.sh\n", encoding="utf-8")
    assert residual_bash.paths_main(["--root", str(root)]) == 2


def test_cli_newline_and_null_delimited() -> None:
    root = Path(__file__).resolve().parents[1]
    base = [sys.executable, str(root / "python" / "cli.py"), "residual-bash", "paths", "--root", str(root)]
    newline = subprocess.run(base, check=True, text=True, capture_output=True)
    assert "scripts/sleep-seconds.sh\n" in newline.stdout
    nul = subprocess.run([*base, "--null-delimited"], check=True, capture_output=True)
    assert b"scripts/sleep-seconds.sh\0" in nul.stdout


def test_root_fixture_reads_fixture_manifest(tmp_path: Path) -> None:
    root = tmp_path
    manifest = root / "scripts" / "residual-bash-paths.txt"
    manifest.parent.mkdir()
    _ = manifest.write_text("scripts/fixture-only.sh\n", encoding="utf-8")
    assert residual_bash.read_residual_paths(root) == ["scripts/fixture-only.sh"]
