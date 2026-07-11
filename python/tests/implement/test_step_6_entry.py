"""Subprocess regressions for production step-6-entry.sh identity-aware rejoin."""

from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

from larch.implement import checks_result_identity as cri

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "skills" / "implement" / "scripts" / "step-6-entry.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "init")
    return repo.resolve()


def _write_stub_cli(plugin_root: Path, *, start_marker: Path) -> None:
    cli = plugin_root / "python" / "cli.py"
    cli.parent.mkdir(parents=True, exist_ok=True)
    real_cli = ROOT / "python" / "cli.py"
    (plugin_root / "python" / "larch").mkdir(parents=True, exist_ok=True)
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import os, subprocess, sys
        sys.path.insert(0, {str(ROOT / "python")!r})
        argv = sys.argv[1:]
        if argv[:1] == ["bgjob"] and len(argv) > 1 and argv[1] == "start":
            step = ""
            for i, tok in enumerate(argv):
                if tok == "--step" and i + 1 < len(argv):
                    step = argv[i + 1]
            open({str(start_marker)!r}, "w", encoding="utf-8").write("started:" + step + "\\n")
            print(f"BGJOB_STATUS=STARTED STEP={{step}} PGID=1")
            raise SystemExit(0)
        if argv[:1] == ["bgjob"] and len(argv) > 1 and argv[1] == "wait":
            tmpdir = ""
            step = ""
            for i, tok in enumerate(argv):
                if tok == "--tmpdir" and i + 1 < len(argv):
                    tmpdir = argv[i + 1]
                if tok == "--step" and i + 1 < len(argv):
                    step = argv[i + 1]
            result = os.path.join(tmpdir, "bgjob", f"{{step}}.result.env")
            print("BGJOB_STATUS=DONE")
            if os.path.isfile(result):
                sys.stdout.write(open(result, encoding="utf-8").read())
            raise SystemExit(0)
        raise SystemExit(subprocess.call([sys.executable, {str(real_cli)!r}, *argv]))
        """
    )
    cli.write_text(script, encoding="utf-8")
    cli.chmod(cli.stat().st_mode | stat.S_IXUSR)


def _session(tmpdir: Path, repo: Path) -> None:
    (tmpdir / "session-env.sh").write_text(
        f"REPO_ROOT={repo}\nLARCH_TOKEN_SESSION_ID=\nLARCH_CLAUDE_SOURCE_FILE=\nLARCH_TIMING_LEDGER=\n",
        encoding="utf-8",
    )
    (tmpdir / "bgjob").mkdir(parents=True, exist_ok=True)


def _run_launcher(*, tmpdir: Path, plugin_root: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "IMPLEMENT_TMPDIR": str(tmpdir),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "PYTHONPATH": str(ROOT / "python"),
    }
    return subprocess.run(
        ["bash", str(LAUNCHER), *(extra or [])],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_step6_stale_failed_result_relaunches_after_drift(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    _session(tmpdir, repo)
    live = cri.compute_identity(repo_root=repo)
    step = "implement-step6-checks"
    result = tmpdir / "bgjob" / f"{step}.result.env"
    result.write_text(
        "\n".join(
            [
                f"STEP={step}",
                "BGJOB_RC=0",
                "NEXT_ACTION=checks-failed",
                *[f"{k}={v}" for k, v in live.as_rows()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "README").write_text("fixed\n", encoding="utf-8")
    plugin = tmp_path / "plugin"
    start_marker = tmp_path / "started"
    _write_stub_cli(plugin, start_marker=start_marker)
    proc = _run_launcher(tmpdir=tmpdir, plugin_root=plugin, extra=["--force-checks", "true"])
    assert proc.returncode == 0, proc.stderr
    assert "BGJOB_STATUS=STARTED" in proc.stdout
    assert start_marker.exists()
    assert not result.exists()


def test_step6_skip_to_7a_rejoins_when_identity_matches(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    _session(tmpdir, repo)
    live = cri.compute_identity(repo_root=repo)
    step = "implement-step6-checks"
    result = tmpdir / "bgjob" / f"{step}.result.env"
    result.write_text(
        "\n".join(
            [
                f"STEP={step}",
                "BGJOB_RC=0",
                "NEXT_ACTION=skip-to-7a",
                *[f"{k}={v}" for k, v in live.as_rows()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    plugin = tmp_path / "plugin"
    start_marker = tmp_path / "started"
    _write_stub_cli(plugin, start_marker=start_marker)
    proc = _run_launcher(tmpdir=tmpdir, plugin_root=plugin)
    assert proc.returncode == 0, proc.stderr
    assert "BGJOB_STATUS=DONE" in proc.stdout
    assert "NEXT_ACTION=skip-to-7a" in proc.stdout
    assert not start_marker.exists()


def test_step6_child_drift_before_checks(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    _session(tmpdir, repo)
    live = cri.compute_identity(repo_root=repo)
    merge = tmpdir / "bgjob" / "implement-step6-checks.merge.env"
    merge.parent.mkdir(parents=True, exist_ok=True)
    (repo / "README").write_text("child-drift\n", encoding="utf-8")
    env = {
        **os.environ,
        "IMPLEMENT_TMPDIR": str(tmpdir),
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "PYTHONPATH": str(ROOT / "python"),
    }
    proc = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--bgjob-child",
            "--merge-result-env",
            str(merge),
            "--repo-root",
            str(repo),
            "--launch-head",
            live.head_sha,
            "--launch-fp",
            live.tree_fingerprint,
            "--launch-schema",
            live.fingerprint_schema,
            "--force-checks",
            "true",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    text = merge.read_text(encoding="utf-8")
    assert "NEXT_ACTION=identity-integrity-failed" in text
