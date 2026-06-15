"""Tests for /design log publish flow port."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


def _write_fake_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
if args[:2] == ["run-log","init"]:
    raise SystemExit(0)
if args[:2] == ["redact","tmpdir-paths"] or args[:2] == ["redact","secrets"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_log_publish_dry_run_success(tmp_path: Path) -> None:
    cli_py = Path(__file__).with_name("cli.py")
    design = tmp_path / "design"
    design.mkdir()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gh_stub = fake_bin / "gh"
    gh_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    gh_stub.chmod(gh_stub.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH','')}"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "log-publish",
            "--design-tmpdir",
            str(design),
            "--run-id",
            "RUN1",
            "--issue",
            "12",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PUBLISH_OK=true" in result.stdout


def test_log_publish_writes_metadata_and_logs(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=False, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, check=False, capture_output=True)
    design = tmp_path / "design"
    design.mkdir()
    (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "log-publish",
            "--design-tmpdir",
            str(design),
            "--run-id",
            "RUN2",
            "--issue",
            "33",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PUBLISH_OK=true" in result.stdout
    assert (design / ".design-log-publish-metadata.env").is_file()
    assert (repo / "larch-logs" / "design" / "RUN2" / "artifact.txt").is_file()
