"""Tests for migration_lint.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.lint import migration_lint


CLI_PATH = Path(__file__).with_name("cli.py")


def _make_git_repo(tmp_path: Path) -> Path:
    """Initialize a minimal git repo for ls-files testing."""
    _ = subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    _ = subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    return tmp_path


def _add_file(repo: Path, rel: str, content: str, *, binary: bool = False) -> Path:
    """Write and git-add a file in the repo."""
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        _ = target.write_bytes(b"\x00binary\x00")
    else:
        _ = target.write_text(content, encoding="utf-8")
    _ = subprocess.run(["git", "add", rel], check=True, capture_output=True, cwd=str(repo))
    return target


def _make_manifest(repo: Path, entries: list[tuple[str, str]]) -> Path:
    """Write and git-add a manifest TSV."""
    lines = ["# manifest\n"]
    for path, retired_by in entries:
        lines.append(f"{path}\t{retired_by}\n")
    content = "".join(lines)
    return _add_file(repo, "manifest.tsv", content)


# ---------------------------------------------------------------------------
# Unit / in-process tests
# ---------------------------------------------------------------------------


def test_empty_manifest_exits_0(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    manifest = _make_manifest(repo, [])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_manifest_not_found_exits_2(tmp_path: Path) -> None:
    rc = migration_lint.main([
        "--manifest", str(tmp_path / "nonexistent.tsv"),
        "--root", str(tmp_path),
    ])
    assert rc == 2


def test_malformed_row_exits_2(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    manifest = repo / "manifest.tsv"
    _ = manifest.write_text("bad-line-no-tab\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "manifest.tsv"], check=True, capture_output=True, cwd=str(repo))
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 2


def test_clean_tree_exits_0(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, "docs/safe.md", "This file has no references.\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_full_path_flag_detected(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, "docs/consumer.md", f"Call {retired} to do things.\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_dev_skill_markdown_bare_basename_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/classify-bump.md",
        "Call classify-bump.sh for release classification.\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_dev_skill_markdown_backtick_bare_basename_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = [
        ".claude/skills/release/scripts/" + "classify-bump.sh",
        ".claude/skills/release/scripts/" + "release-prepare.sh",
    ]
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/classify-bump.md",
        "Call `classify-bump.sh` before `release-prepare.sh`.\n",
    )
    manifest = _make_manifest(repo, [(path, "#test") for path in retired])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_dev_skill_markdown_bare_basename_lint_ignore(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/classify-bump.md",
        "Call classify-bump.sh here. # lint-ignore\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_full_path_with_lint_ignore_still_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/classify-bump.md",
        f"Call {retired} here. # lint-ignore\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_dev_skill_cross_directory_bare_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/other/scripts/consumer.md",
        "Call classify-bump.sh for release classification.\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_dev_skill_path_like_bare_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/classify-bump.md",
        "Call other/path/classify-bump.sh for release classification.\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_dev_skill_non_markdown_bare_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/notes.txt",
        "Call classify-bump.sh for release classification.\n",
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_dev_skill_markdown_live_sibling_bare_basename_not_flagged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = _make_git_repo(tmp_path / "repo")
    retired = ".claude/skills/release/scripts/" + "classify-bump.sh"
    _ = _add_file(
        repo,
        ".claude/skills/release/scripts/consumer.md",
        "Call classify-bump.sh for release classification.\n",
    )
    _ = _add_file(repo, ".claude/skills/release/scripts/consumer.sh", "echo live\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    monkeypatch.chdir(tmp_path)
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_top_level_scripts_markdown_bare_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = [
        "scripts/" + "append-execution-issue.sh",
        "scripts/" + "test-lint-skill-invocations.sh",
    ]
    _ = _add_file(
        repo,
        "scripts/contract.md",
        "Mentions append-execution-issue.sh and test-lint-skill-invocations.sh.\n",
    )
    manifest = _make_manifest(repo, [(path, "#test") for path in retired])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_live_same_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old/run-analysis.sh"
    # A live file with the same basename but different path should NOT be flagged.
    _ = _add_file(repo, "docs/consumer.md", "see other/path/run-analysis.sh\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    # "other/path/run-analysis.sh" does not match "scripts/old/run-analysis.sh"
    assert rc == 0


def test_script_dir_basename_reference_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/" + "resolve" + "-repo.sh"
    basename = retired.rsplit("/", 1)[1]
    _ = _add_file(repo, "scripts/caller.sh", f'REPO=$("$SCRIPT_DIR/{basename}")\n')
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_cross_directory_bare_basename_not_flagged(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/" + "resolve" + "-repo.sh"
    basename = retired.rsplit("/", 1)[1]
    _ = _add_file(repo, "docs/consumer.md", f"See helpers/{basename} for examples.\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_ship_pr_record_failure_label_is_stale_ref(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "python/cli.py ci wait"
    _ = _add_file(
        repo,
        "scripts/ship-driver.txt",
        'record_failure checks "python/cli.py ci wait exited unexpectedly" "$rc"\n',
    )
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_ship_pr_comment_is_stale_ref(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/synthetic-retired-helper.sh"
    _ = _add_file(repo, "scripts/ship-driver.txt", "# prose mentions scripts/synthetic-retired-helper.sh only\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_ship_pr_sh_reference_is_stale_ref(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-ship-pr.sh"
    _ = _add_file(repo, "docs/consumer.md", f"Invoke {retired} for shipping.\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_larch_logs_excluded(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, f"larch-logs/implement/run-1/{retired}", f"ref: {retired}\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_changelog_excluded(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, "CHANGELOG.md", f"- Removed {retired}\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_protected_plugin_manifest_excluded(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, ".claude-plugin/plugin.json", f'{{"description": "{retired}"}}\n')
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_manifest_self_reference_ignored(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_binary_skipped(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    bin_path = repo / "assets" / "image.bin"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    _ = bin_path.write_bytes(b"\x00" + retired.encode() + b"\x00")
    _ = subprocess.run(["git", "add", "assets/image.bin"], check=True, capture_output=True, cwd=str(repo))
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0


def test_still_present_manifest_path_errors(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, retired, "#!/bin/bash\necho old\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_retired_non_sh_path_reference(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "python/old_ci_helper.py"
    _ = _add_file(repo, "docs/consumer.md", f"Import {retired} for CI helpers.\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1


def test_kv_present_on_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _make_git_repo(tmp_path)
    manifest = _make_manifest(repo, [])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "LINT_STATUS=ok" in captured.out
    assert "RETIRED_PATHS=0" in captured.out
    assert "RETIRED_REFS=0" in captured.out
    assert "EMBEDDED_LEGACY_REFS=" in captured.out


def test_kv_present_on_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, "docs/consumer.md", f"uses {retired}\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    rc = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    assert rc == 1
    captured = capsys.readouterr()
    assert "LINT_STATUS=findings" in captured.out
    assert "RETIRED_REFS=" in captured.out


def test_file_line_on_stderr_under_quiet(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Diagnostics appear on stderr (BreadcrumbWriter default stream)."""
    repo = _make_git_repo(tmp_path)
    retired = "scripts/old-helper.sh"
    _ = _add_file(repo, "docs/consumer.md", f"uses {retired}\n")
    manifest = _make_manifest(repo, [(retired, "#test")])
    _ = migration_lint.main([
        "--manifest", str(manifest),
        "--root", str(repo),
    ])
    captured = capsys.readouterr()
    assert "docs/consumer.md:1" in captured.err
    assert retired in captured.err


# ---------------------------------------------------------------------------
# Subprocess tests
# ---------------------------------------------------------------------------


def test_subprocess_clean_tree(tmp_path: Path) -> None:
    repo = _make_git_repo(tmp_path)
    manifest = _make_manifest(repo, [])
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "lint",
            "retired-scripts",
            "--manifest",
            str(manifest),
            "--root",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "LINT_STATUS=ok" in result.stdout
