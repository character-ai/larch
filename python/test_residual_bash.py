from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from larch.core import residual_bash


def test_manifest_includes_combine_issues_helper() -> None:
    paths = residual_bash.read_residual_paths(Path(__file__).resolve().parents[1])
    assert ".claude/skills/combine-issues/scripts/search-implementing-issue.sh" in paths


def test_manifest_excludes_retired_bash_artifacts() -> None:
    paths = set(residual_bash.read_residual_paths(Path(__file__).resolve().parents[1]))
    # Split retired-path literals at the directory boundary so this fixture
    # file does not itself reference a retired path. See docs/python-migration.md:
    # "Do NOT write retired-path literals in test fixtures."
    retired = {
        "scripts/" + "lib-quiet.sh",
        "scripts/" + "lib-net.sh",
        "scripts/" + "lib-redact.sh",
        "scripts/" + "lib-execution-issues.sh",
        "scripts/" + "lib-phantom-probe.sh",
        "scripts/" + "lib-sparse-dirs.sh",
        "scripts/" + "lib-larch-dev-clone.sh",
        "scripts/" + "lib-submodule-prohibition.sh",
        "scripts/" + "extract-closes-issue-from-pr.sh",
        "scripts/" + "oos-disposition-shared.inc.bash",
        "scripts/" + "run-log-terminal-outcomes.inc.bash",
    }
    assert paths.isdisjoint(retired)


def test_manifest_excludes_non_residual_orchestration() -> None:
    paths = set(residual_bash.read_residual_paths(Path(__file__).resolve().parents[1]))
    orchestration = {
        "skills/design/scripts/design-step3-review.sh",
        "skills/implement/scripts/cleanup.sh",
        "skills/implement/scripts/" + "lib-implement-clone-tag.sh",
        "skills/implement/scripts/" + "step-2-entry.sh",
        "skills/implement/scripts/" + "step-2-entry.md",
        "skills/implement/scripts/step-8-ship.sh",
    }
    assert paths.isdisjoint(orchestration)


def test_manifest_paths_exist_on_disk() -> None:
    root = Path(__file__).resolve().parents[1]
    assert residual_bash.paths_main(["--root", str(root), "--check-exists"]) == 0


def test_intersect_git_limits_to_tracked_manifest_rows(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path
    manifest = root / "scripts" / "residual-bash-paths.txt"
    manifest.parent.mkdir(parents=True)
    tracked = root / "scripts" / "tracked.sh"
    _ = tracked.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = manifest.write_text("scripts/tracked.sh\nscripts/listed-but-untracked.sh\n", encoding="utf-8")
    _ = subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    _ = subprocess.run(["git", "add", "scripts/tracked.sh", "scripts/residual-bash-paths.txt"], cwd=root, check=True)
    proc = subprocess.run(
        [sys.executable, str(repo / "python" / "cli.py"), "residual-bash", "paths", "--root", str(root), "--intersect-git"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert proc.stdout.splitlines() == ["scripts/tracked.sh"]


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
