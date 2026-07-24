# pyright: reportPrivateUsage=false
"""Tests for /design log publish flow port."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from larch.design import design_log_publish_flow
from larch.design import design_summary
from larch.report import run_lifecycle, run_log_publish as run_log_publisher, run_logs
from larch.report import storage_config
from larch.report.storage_config import StorageBase, ToolRepositoryStorage
from test_support import operator_repo_with_remote as _base_operator_repo_with_remote
from test_support import write_gh_pr_stub as _write_gh_stub

RUN_ID = "ABCDEF01-2345-6789-ABCD-EF0123456789"


def _git(*argv: str, cwd: Path) -> None:
    _ = subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)

def _operator_repo_with_remote(tmp_path: Path) -> Path:
    repo = _base_operator_repo_with_remote(tmp_path)
    local_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    _git("remote", "set-url", "--push", "origin", local_remote, cwd=repo)
    _git("remote", "set-url", "origin", "git@github.com:fixture/consumer.git", cwd=repo)
    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://bucket"\n', encoding="utf-8"
    )
    _git("add", "tools-config.toml", cwd=repo)
    _git("commit", "-q", "-m", "storage config", cwd=repo)
    return repo


def _operator_repo_with_guidelines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = _operator_repo_with_remote(tmp_path)
    _ = (repo / "ARCHITECTURAL_GUIDELINES.md").write_text(
        "### G-Test-1: Test\n- Why: test.\n",
        encoding="utf-8",
    )
    _git("add", "ARCHITECTURAL_GUIDELINES.md", cwd=repo)
    _git("commit", "-q", "-m", "guidelines", cwd=repo)
    monkeypatch.chdir(repo)
    return repo




def _operator_repo_with_invariants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    text: str = "### I-Test-1: Test\nInvariant text.\n",
) -> Path:
    repo = _operator_repo_with_remote(tmp_path)
    _ = (repo / "ARCHITECTURAL_INVARIANTS.md").write_text(text, encoding="utf-8")
    _git("add", "ARCHITECTURAL_INVARIANTS.md", cwd=repo)
    _git("commit", "-q", "-m", "invariants", cwd=repo)
    monkeypatch.chdir(repo)
    return repo

def _run_publish(
    repo: Path,
    design: Path,
    bin_dir: Path,
    *,
    reason: str = "final",
    outcome: str = "approved",
) -> subprocess.CompletedProcess[str]:
    real_cli = Path(__file__).resolve().parents[2] / "cli.py"
    bin_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = bin_dir.parent / "remote"
    remote_dir.mkdir(parents=True, exist_ok=True)
    aws_stub = bin_dir / "aws"
    _ = aws_stub.write_text(
        """#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path(__file__).resolve().parent.parent / "remote"
if args[:2] == ["s3api", "put-object"]:
    if (root.parent / "fail-upload").exists():
        print("transport failed", file=sys.stderr)
        raise SystemExit(1)
    key = args[args.index("--key") + 1]
    source = Path(args[args.index("--body") + 1])
    target = root / key
    if target.exists():
        print("PreconditionFailed", file=sys.stderr)
        raise SystemExit(1)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print("{}")
elif args[:2] == ["s3api", "head-object"]:
    key = args[args.index("--key") + 1]
    print(json.dumps({"ContentLength": (root / key).stat().st_size}))
elif args[:2] == ["s3api", "get-object"]:
    key = args[args.index("--key") + 1]
    destination = Path(args[args.index("--key") + 2])
    shutil.copy2(root / key, destination)
    print("{}")
elif args[:2] == ["s3api", "list-objects-v2"]:
    print('{"Contents":[]}')
elif args[:2] == ["s3", "ls"]:
    raise SystemExit(0)
else:
    raise SystemExit(2)
""",
        encoding="utf-8",
    )
    aws_stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    _ = (repo / "tools-config.toml").write_text(
        '[larch]\nstorage_base_uri = "s3://bucket"\n', encoding="utf-8"
    )
    env["XDG_CACHE_HOME"] = str(bin_dir.parent / "cache")
    env["XDG_STATE_HOME"] = str(bin_dir.parent / "state")
    # The real cli is used for run-log init/commit + redact; all git writes are
    # cwd-scoped to the disposable worktree, never the operator or plugin repo.
    env["CLAUDE_PLUGIN_ROOT"] = str(Path(real_cli).resolve().parents[1])
    lifecycle = subprocess.run(
        [
            sys.executable,
            str(real_cli),
            "run-log",
            "lifecycle-start",
            "--repo-root",
            str(repo),
            "--skill",
            "design",
            "--run-id",
            RUN_ID,
            "--log-root",
            str(design / "larch-logs"),
            "--adopt-existing",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if lifecycle.returncode != 0:
        return lifecycle
    return subprocess.run(
        [
            sys.executable,
            str(real_cli),
            "design",
            "log-publish",
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--reason",
            reason,
            "--outcome",
            outcome,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _cached_run(repo: Path, bin_dir: Path) -> Path:
    storage = storage_config.load_tool_repository_storage(repo_root=repo, environ={})
    return (
        bin_dir.parent / "cache" / "larch" / "run-logs" / "v2"
        / storage.client_repo / storage.storage_origin_id / "design" / RUN_ID
    )


def _patch_archive_publish(
    monkeypatch: pytest.MonkeyPatch,
    cache_dir: Path,
) -> None:
    staging_root = cache_dir.parent / "staging"
    run_dir = staging_root / "design" / RUN_ID
    context_file = cache_dir.parent / "context.json"

    def fake_load(**_kwargs: object) -> run_lifecycle.LifecycleStart:
        _ = run_logs.log_init(log_root=staging_root, skill="design", run_id=RUN_ID)
        return run_lifecycle.LifecycleStart(
            repo_root=cache_dir.parent,
            storage_root=ToolRepositoryStorage(StorageBase("s3", "bucket"), "consumer"),
            skill="design",
            run_id=RUN_ID,
            log_root=staging_root,
            run_dir=run_dir,
            context_file=context_file,
        )

    def fake_finish(**_kwargs: object) -> run_lifecycle.LifecycleTerminal:
        shutil.copytree(run_dir, cache_dir)
        return run_lifecycle.LifecycleTerminal(
            outcome="success",
            publication=run_log_publisher.PublicationResult(
                remote_key=f"run-logs/design/{RUN_ID}.tar.gz",
                archive_sha256="a" * 64,
                cache_dir=cache_dir,
                remote_status=run_log_publisher.RemotePublicationStatus.CREATED,
                cache_status=run_log_publisher.CachePublicationStatus.PROMOTED,
            ),
            secret_scrub_violations=0,
        )

    monkeypatch.setattr(
        design_log_publish_flow.run_lifecycle, "load_run_context", fake_load
    )
    monkeypatch.setattr(
        design_log_publish_flow.run_lifecycle, "finish_run", fake_finish
    )


def test_log_publish_dry_run_success(tmp_path: Path) -> None:
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    design = tmp_path / "design"
    design.mkdir()
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
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
            "--outcome",
            "approved",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PUBLISH_OK=true" in result.stdout
    summary = (design / "final-summary.md").read_text(encoding="utf-8")
    assert "<!-- larch:run-summary v=1 -->" in summary


def test_log_publish_captures_transcript_before_publish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plugin_root = tmp_path / "plugin"
    order: list[str] = []
    captured: dict[str, str] = {}

    def fake_capture(*, ctx: Any) -> bool:
        order.append("capture")
        captured["design_tmpdir"] = str(ctx.design_tmpdir)
        captured["plugin_root"] = str(ctx.plugin_root)
        captured["session_id"] = ctx.session_id
        captured["issue"] = ctx.issue
        captured["repo"] = ctx.repo
        captured["claude_pid"] = ctx.claude_pid
        captured["warning_step_label"] = ctx.warning_step_label
        return True

    def fake_render(**kwargs: object) -> bool:
        order.append("render")
        captured["render_outcome"] = str(kwargs["outcome"])
        return True

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str]:
        order.append("publish")
        return (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0")

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_CLAUDE_PID", "12345")
    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "capture_design_transcript",
        fake_capture,
    )
    monkeypatch.setattr(
        design_log_publish_flow, "_render_final_summary_before_copy", fake_render
    )
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--repo",
            "o/r",
            "--reason",
            "final",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert order == ["capture", "render", "publish"]
    assert captured == {
        "design_tmpdir": str(design),
        "plugin_root": str(plugin_root),
        "session_id": RUN_ID,
        "issue": "33",
        "repo": "o/r",
        "claude_pid": "12345",
        "warning_step_label": "5c",
        "render_outcome": "approved",
    }


def test_log_publish_capture_failure_skips_publish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    published = False

    def fake_capture(*, ctx: Any) -> bool:
        assert ctx.session_id == RUN_ID
        return False

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str]:
        nonlocal published
        published = True
        return (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0")

    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "capture_design_transcript",
        fake_capture,
    )
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert not published
    assert "PUBLISH_OK=false" in capsys.readouterr().out




def test_log_publish_approved_missing_invariant_assessment_records_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_invariants(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    published = False

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str]:
        nonlocal published
        published = True
        return (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0")

    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert rc == 0
    assert published
    assert (design / ".missing-invariant-assessment-warning").is_file()
    assert "invariant-assessment" in issues
    assert "architectural-invariant-assessment.md" in issues


def test_log_publish_approved_missing_invariant_assessment_does_not_follow_marker_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_invariants(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    protected = tmp_path / "protected-invariant-warning.txt"
    _ = protected.write_text("keep\n", encoding="utf-8")
    (design / ".missing-invariant-assessment-warning").symlink_to(protected)

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_publish_design_logs",
        lambda **_kwargs: (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0"),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert protected.read_text(encoding="utf-8") == "keep\n"


def test_log_publish_invariant_assessment_present_suppresses_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_invariants(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "architectural-invariant-assessment.md").write_text("clean\n", encoding="utf-8")

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_publish_design_logs",
        lambda **_kwargs: (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0"),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert not (design / ".missing-invariant-assessment-warning").exists()


def test_log_publish_empty_invariants_do_not_warn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_invariants(tmp_path, monkeypatch, text="# No invariant entries\n")
    design = tmp_path / "design"
    design.mkdir()

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_publish_design_logs",
        lambda **_kwargs: (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0"),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert not (design / ".missing-invariant-assessment-warning").exists()


def test_log_publish_approved_missing_guideline_assessment_records_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_guidelines(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    published = False

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str]:
        nonlocal published
        published = True
        return (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0")

    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert rc == 0
    assert published
    assert (design / ".missing-guideline-assessment-warning").is_file()
    assert "guideline-assessment" in issues
    assert "architectural-guideline-assessment.md" in issues


def test_log_publish_approved_missing_guideline_assessment_does_not_follow_marker_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_guidelines(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    protected = tmp_path / "protected-warning.txt"
    _ = protected.write_text("keep\n", encoding="utf-8")
    (design / ".missing-guideline-assessment-warning").symlink_to(protected)

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_publish_design_logs",
        lambda **_kwargs: (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0"),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert protected.read_text(encoding="utf-8") == "keep\n"


def test_log_publish_guideline_assessment_present_suppresses_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ = _operator_repo_with_guidelines(tmp_path, monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "architectural-guideline-assessment.md").write_text("clean\n", encoding="utf-8")

    monkeypatch.setattr(design_log_publish_flow.design_publish, "capture_design_transcript", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", lambda **_kwargs: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_publish_design_logs",
        lambda **_kwargs: (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0"),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert not (design / ".missing-guideline-assessment-warning").exists()


def test_log_publish_capture_skip_still_publishes_pause(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    reasons: list[str] = []

    def fake_capture(*, ctx: Any) -> bool:
        assert ctx.session_id == RUN_ID
        assert ctx.warning_step_label == "pause"
        return True

    def fake_render(**kwargs: object) -> bool:
        reasons.append(str(kwargs["outcome"]))
        return True

    def fake_publish(**kwargs: object) -> tuple[bool, str, str, str]:
        request = kwargs["request"]
        assert isinstance(request, design_log_publish_flow.PublishDesignLogsRequest)
        reasons.append(request.run_id)
        return (True, "run-logs/design/RUN.tar.gz", "/cache/design/RUN", "0")

    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "capture_design_transcript",
        fake_capture,
    )
    monkeypatch.setattr(
        design_log_publish_flow, "_render_final_summary_before_copy", fake_render
    )
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--reason",
            "pause",
            "--outcome",
            "paused",
        ]
    )

    assert rc == 0
    assert reasons == ["paused", RUN_ID]
    assert "PUBLISH_OK=true" in capsys.readouterr().out


def test_log_publish_creates_cloud_archive_and_cache_without_git_mutation(tmp_path: Path) -> None:
    # The design run tree is committed to a dedicated branch and PR'd; the
    # operator working tree stays clean (issue #4395), and ship is best-effort.
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=1)

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    assert f"REMOTE_KEY=run-logs/design/{RUN_ID}.tar.gz" in result.stdout
    assert "PR_NUMBER=" in result.stdout
    assert "PR_URL=" in result.stdout
    # The publish surfaces the scrub-violation count so the design tail can warn
    # the operator to rotate; a clean run reports zero (#4782).
    assert "SECRET_SCRUB_VIOLATIONS=0" in result.stdout
    # The operator working tree is never polluted, so the next /implement passes preflight.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.stdout.strip() == "", status.stdout
    cached = _cached_run(repo, bin_dir)
    assert (cached / "artifact.txt").read_text(encoding="utf-8") == "artifact\n"
    assert (cached / "manifest.json").is_file()
    summary = (cached / "final-summary.md").read_text(encoding="utf-8")
    assert "STALE-SENTINEL" not in summary
    assert "<!-- larch:run-summary v=1 -->" in summary
    assert (
        tmp_path / "remote" / "larch" / "consumer" / "run-logs"
        / "design" / f"{RUN_ID}.tar.gz"
    ).is_file()
    meta = (design / ".design-log-publish-metadata.env").read_text(encoding="utf-8")
    assert f"DESIGN_LOG_REMOTE_KEY=run-logs/design/{RUN_ID}.tar.gz" in meta


def test_log_publish_commits_enriched_final_summary_without_helper_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    monkeypatch.chdir(repo)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    _ = (design / "final-summary.md").write_text("STALE-SENTINEL\n", encoding="utf-8")
    _ = (design / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")

    captured: dict[str, design_summary.FinalSummaryRenderRequest] = {}
    upsert_calls: list[list[str]] = []
    original_render = design_summary.render_final_summary_for_request
    original_run_cli = design_summary._run_cli  # pyright: ignore[reportPrivateUsage]

    def capture_render(request: design_summary.FinalSummaryRenderRequest) -> bool:
        captured["request"] = request
        return original_render(request)

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("tracking-issue", "upsert-summary"):
            upsert_calls.append(list(args))
            return subprocess.CompletedProcess(
                ["cli.py", *args], 0, stdout="", stderr=""
            )
        return original_run_cli(*args)

    def fake_capture(**_kwargs: object) -> bool:
        return True

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    cache_dir = tmp_path / "cache-enriched"
    _patch_archive_publish(monkeypatch, cache_dir)
    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "capture_design_transcript",
        fake_capture,
    )
    monkeypatch.setattr(
        design_summary, "render_final_summary_for_request", capture_render
    )
    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)  # pyright: ignore[reportPrivateUsage]

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--repo",
            "o/r",
            "--reason",
            "final",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert captured["request"].upsert_summary_comment is False
    assert not upsert_calls
    summary = (cache_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "STALE-SENTINEL" not in summary
    assert "## /design run" in summary
    assert "<!-- larch:run-summary v=1 -->" in summary


def test_log_publish_removes_stale_final_summary_when_render_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    monkeypatch.chdir(repo)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    _ = (design / "final-summary.md").write_text("STALE-SENTINEL\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    captured: dict[str, design_summary.FinalSummaryRenderRequest] = {}
    upsert_calls: list[list[str]] = []
    original_render = design_summary.render_final_summary_for_request
    original_run_cli = design_summary._run_cli  # pyright: ignore[reportPrivateUsage]

    def capture_render(request: design_summary.FinalSummaryRenderRequest) -> bool:
        captured["request"] = request
        return original_render(request)

    def fake_render_main(_argv: list[str]) -> int:
        return 1

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("tracking-issue", "upsert-summary"):
            upsert_calls.append(list(args))
            return subprocess.CompletedProcess(
                ["cli.py", *args], 0, stdout="", stderr=""
            )
        return original_run_cli(*args)

    def fake_capture(**_kwargs: object) -> bool:
        return True

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    cache_dir = tmp_path / "cache-render-failed"
    _patch_archive_publish(monkeypatch, cache_dir)
    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "capture_design_transcript",
        fake_capture,
    )
    monkeypatch.setattr(
        design_summary, "render_final_summary_for_request", capture_render
    )
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render_main)
    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)  # pyright: ignore[reportPrivateUsage]

    rc = design_log_publish_flow.log_publish_main(
        [
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
            "--repo",
            "o/r",
            "--reason",
            "final",
            "--outcome",
            "approved",
        ]
    )

    assert rc == 0
    assert captured["request"].upsert_summary_comment is False
    assert not upsert_calls
    assert not (cache_dir / "final-summary.md").exists()
    assert not (design / "final-summary.md").exists()


def test_log_publish_reports_and_commits_scrubbed_secret(tmp_path: Path) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    raw_token = "xoxb-1234567890abcdef"
    _ = (design / "secret.txt").write_text(f"token={raw_token}\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    result = _run_publish(repo, design, bin_dir)

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    assert "SECRET_SCRUB_VIOLATIONS=1" in result.stdout
    scrubbed = (_cached_run(repo, bin_dir) / "secret.txt").read_text(encoding="utf-8")
    assert raw_token not in scrubbed
    assert "<REDACTED-TOKEN>" in scrubbed


def test_log_publish_upload_failure_keeps_tree_clean_and_durable_pending(
    tmp_path: Path,
) -> None:
    # Upload failure stays nonzero and leaves a content-pinned pending archive.
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _ = (tmp_path / "fail-upload").write_text("", encoding="utf-8")

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode != 0
    assert "PUBLISH_OK=false" in result.stdout
    assert "archive publication failed" in result.stderr
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.stdout.strip() == "", status.stdout
    storage = storage_config.load_tool_repository_storage(repo_root=repo, environ={})
    pending = (
        tmp_path / "state" / "larch" / "run-log-pending" / "v2"
        / storage.client_repo / storage.storage_origin_id / "design" / RUN_ID
    )
    assert (pending / "archive.tar.gz").is_file()
    assert (pending / "retry.json").is_file()


def test_publish_excluded_predicate() -> None:
    # Raw machine sidecars/transcripts are dropped; curated forensics are kept.
    # Guards the keep/drop boundary that restores the pre-Codex-capture committed
    # design-log shape (the ~40x .events.jsonl bloat).
    excluded = [
        "codex-primary-plan-arch-output.txt.events.jsonl",
        "codex-primary-plan-arch-output.txt.meta",
        "render-plan-codex-arch.prompt",
        "cursor-plan-requirements-output.txt",  # *-plan-*-output*.txt
        "codex-plan-generic-output.txt",
        "cursor-plan-arch-output-phase2.txt",  # -output*.txt phase variant
        "codex-primary-plan-arch-output.txt.stderr-tail",  # *-plan-*-output*.txt.*
        "claude-plan-voter-prompt.txt",  # *-prompt.txt
        "aggregator-prompt.md",  # *-prompt.md
        "step2b-codex-raw.40818.txt",
        "cursor-plan-arch-output.txt.json",  # *.txt.json
        "codex-primary-plan-arch-output.txt.tsv",  # *.txt.tsv
        "claude-vote-output.txt.token-record",
        "cursor-plan-arch-output.txt.dirty-tree",
        "cursor-plan-requirements-collector.failure.log",  # *-collector.failure.log
        "scout-plan-manifest.json.raw.cursor",  # *.raw.cursor
        "plan-review-collector.stderr",  # exact name
        "plan-review-slots.ndjson.output-files.dropped-slots",  # exact name
        "composed-plan.redacted.md",  # redacted duplicate
        "findings-ledger.tsv",  # ephemeral duplicate-suppression ledger
        "security-oos-observations.md",  # private security sidecar
    ]
    for name in excluded:
        assert design_log_publish_flow._publish_excluded(name, is_dir=False), name
    assert design_log_publish_flow._publish_excluded(
        "design-step-5b.5-diagram-failure.bounded.log",
        is_dir=False,
        top_level=True,
    )
    assert design_log_publish_flow._publish_excluded(
        "panel-prompt-sizes.tsv", is_dir=False, top_level=True
    )
    kept = [
        "plan.txt",
        "composed-plan.diff",
        "findings.md",
        "voting-tally.md",
        "accepted-plan-findings.md",
        "codex-validity-vote-output.txt",
        "codex-plan-fidelity-vote-output.txt",
        "codex-pragmatism-vote-output.txt",
        "aggregator-output.txt",  # not -plan-, not -vote-
        "codex-vote-output.txt",  # curated vote output, not *-plan-*-output*.txt
        "aggregator-validate.stderr",  # bare .stderr kept; only -collector.stderr drops
        "step2b-drafter-status.txt.failure-diag",  # composed carrier kept (#3713)
        "architecture-diagram.md",
        "manifest.json",  # not *.txt.json
        "run-params.json",
        "token-report.json",
        "scout-plan-manifest.json",
        "findings-classification.tsv",  # not *.txt.tsv
        "plan-review-slots.ndjson",
        "panel-prompt-sizes.tsv",
    ]
    for name in kept:
        assert not design_log_publish_flow._publish_excluded(name, is_dir=False), name
    # Whole-subtree exclusions are directory-scoped.
    assert design_log_publish_flow._publish_excluded("plan-autofix", is_dir=True)
    assert design_log_publish_flow._publish_excluded(".completed", is_dir=True)
    assert not design_log_publish_flow._publish_excluded("plan-review", is_dir=True)
    assert not design_log_publish_flow._publish_excluded("breadcrumbs", is_dir=True)
    assert not design_log_publish_flow._publish_excluded("plan-autofix", is_dir=False)


def test_pause_log_publish_retains_completed_sentinels(tmp_path: Path) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "step-3").write_text("", encoding="utf-8")
    _ = (completed / "step-5b").write_text("", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    result = _run_publish(repo, design, bin_dir, reason="pause", outcome="paused")

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    cached = _cached_run(repo, bin_dir)
    assert (cached / ".completed" / "step-3").is_file()
    assert (cached / ".completed" / "step-5b").is_file()


def test_final_log_publish_clears_preexisting_completed_sentinels(
    tmp_path: Path,
) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    stale_completed = repo / "larch-logs" / "design" / RUN_ID / ".completed"
    stale_completed.mkdir(parents=True)
    _ = (stale_completed / "legacy-terminal").write_text("", encoding="utf-8")
    _git("add", f"larch-logs/design/{RUN_ID}/.completed/legacy-terminal", cwd=repo)
    _git("commit", "-q", "-m", "stale completed sentinel", cwd=repo)

    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    result = _run_publish(repo, design, bin_dir)

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    cached = _cached_run(repo, bin_dir)
    assert (cached / "artifact.txt").is_file()
    assert not (cached / ".completed" / "legacy-terminal").exists()


def test_log_publish_excludes_sidecar_crud(tmp_path: Path) -> None:
    # The publish copies a curated set: raw Codex event streams, prompt/meta
    # sidecars, raw per-lane outputs, plan-autofix drafts, and .completed
    # sentinels are dropped at every tree depth, while plan.txt, findings, and the
    # curated plan-review/round-N/ subtree survive. Regression guard for the ~40x
    # committed-log bloat that landed with Codex .events.jsonl capture.
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()

    keep = {
        "plan.txt": "PLAN",
        "aggregator-output.txt": "AGG",
        "findings.md": "F",
        "run-params.json": "{}",
        "codex-validity-vote-output.txt": "V1",
        "codex-plan-fidelity-vote-output.txt": "V2",
        "codex-pragmatism-vote-output.txt": "V3",
    }
    drop = {
        "codex-primary-plan-arch-output.txt.events.jsonl": "{}",
        "codex-primary-plan-arch-output.txt.meta": "M",
        "codex-primary-plan-arch-output.txt": "RAW",  # *-plan-*-output.txt
        "render-plan-codex-arch.prompt": "P",
        "claude-plan-voter-prompt.txt": "VP",
        "step2b-codex-raw.40818.txt": "RAW2",
        "cursor-plan-arch-output.txt.json": "{}",  # *.txt.json
        "findings-ledger.tsv": "round\tfinding_id\n",
        "panel-prompt-sizes.tsv": "site\tslot\n",
        "security-oos-observations.md": "private security\n",
    }
    for name, body in {**keep, **drop}.items():
        _ = (design / name).write_text(body, encoding="utf-8")
    # Nested: plan-review/round-1/ keeps curated files, drops sidecars.
    pr_round = design / "plan-review" / "round-1"
    pr_round.mkdir(parents=True)
    _ = (pr_round / "findings.md").write_text("NF", encoding="utf-8")
    _ = (pr_round / "findings-classification.tsv").write_text(
        "id\tstatus\n", encoding="utf-8"
    )
    _ = (pr_round / "codex-vote-output.txt").write_text("VOTE", encoding="utf-8")
    _ = (pr_round / "panel-prompt-sizes.tsv").write_text(
        "site\tslot\n", encoding="utf-8"
    )
    _ = (pr_round / "codex-vote-output.txt.events.jsonl").write_text(
        "{}", encoding="utf-8"
    )
    _ = (pr_round / "findings-ledger.tsv").write_text(
        "round\tfinding_id\n", encoding="utf-8"
    )
    _ = (pr_round / "security-oos-observations.md").write_text(
        "nested private\n", encoding="utf-8"
    )
    # Whole-subtree drops.
    autofix = design / "plan-autofix"
    autofix.mkdir()
    _ = (autofix / "codex-output.txt").write_text("AF", encoding="utf-8")
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "legacy-terminal").write_text("", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr

    cached = _cached_run(repo, bin_dir)
    tree = {path.relative_to(cached).as_posix() for path in cached.rglob("*")}
    for name in keep:
        assert name in tree, f"expected kept: {name}\n{tree}"
    assert "plan-review/round-1/findings.md" in tree
    assert "plan-review/round-1/codex-vote-output.txt" in tree
    assert "plan-review/round-1/panel-prompt-sizes.tsv" in tree
    assert "manifest.json" in tree
    for name in drop:
        assert name not in tree, f"expected dropped: {name}\n{tree}"
    assert not any("codex-vote-output.txt.events.jsonl" in path for path in tree)
    assert not any(path.endswith("findings-ledger.tsv") for path in tree)
    assert not any(path.endswith("security-oos-observations.md") for path in tree)
    assert not any(path.startswith("plan-autofix/") for path in tree)
    assert not any(path.startswith(".completed/") for path in tree)
    assert not any("step2b-codex-raw" in path for path in tree)


def test_copy_tree_redacted_fail_closed_on_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "source.txt"
    _ = source.write_text(
        "crsr_1620abcdefghijklmnopqrstuvwxyz0123456789\n",
        encoding="utf-8",
    )
    dest = tmp_path / "dest.txt"

    def _never_scrubs(
        text: str,
    ) -> design_log_publish_flow.redact.ScrubLogSecretsResult:
        return design_log_publish_flow.redact.ScrubLogSecretsResult(
            scrubbed=text, findings={"cursor-api-key": 1}
        )

    monkeypatch.setattr(
        design_log_publish_flow.redact, "scrub_log_secrets", _never_scrubs
    )
    with pytest.raises(
        design_log_publish_flow.SecretScrubFailure, match="secret survived"
    ):
        _ = design_log_publish_flow._copy_tree_redacted(
            plugin_root=plugin_root, source=source, dest=dest
        )
    assert not dest.exists()


def test_copy_tree_redacted_redact_tmpdir_failure_is_secret_scrub_failure(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugin"
    cli = plugin_root / "python" / "cli.py"
    cli.parent.mkdir(parents=True)
    _ = cli.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text("plain\n", encoding="utf-8")

    with pytest.raises(
        design_log_publish_flow.SecretScrubFailure, match="redact tmpdir-paths"
    ):
        _ = design_log_publish_flow._copy_tree_redacted(
            plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt"
        )


def test_copy_tree_redacted_scrubber_exception_is_secret_scrub_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "source.txt"
    _ = source.write_text("plain\n", encoding="utf-8")

    def _boom(_text: str) -> tuple[str, dict[str, int]]:
        raise RuntimeError("scrubber unavailable")

    monkeypatch.setattr(design_log_publish_flow.redact, "scrub_log_secrets", _boom)
    with pytest.raises(
        design_log_publish_flow.SecretScrubFailure, match="secret scrubber failed"
    ):
        _ = design_log_publish_flow._copy_tree_redacted(
            plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt"
        )


def test_copy_tree_redacted_symlink_skip_is_not_secret_scrub_failure(
    tmp_path: Path,
) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    target = tmp_path / "target.txt"
    _ = target.write_text("plain\n", encoding="utf-8")
    source = tmp_path / "source-link.txt"
    source.symlink_to(target)

    ok, count = design_log_publish_flow._copy_tree_redacted(
        plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt"
    )

    assert not ok
    assert count == 0


def test_copy_tree_redacted_writes_same_scrubbed_text_used_for_count(
    tmp_path: Path,
) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "source.txt"
    raw = "token=xoxb-1234567890abcdef"
    _ = source.write_text(raw, encoding="utf-8")
    dest = tmp_path / "dest.txt"

    ok, count = design_log_publish_flow._copy_tree_redacted(  # pyright: ignore[reportPrivateUsage]
        plugin_root=plugin_root,
        source=source,
        dest=dest,
    )

    scrub_result = design_log_publish_flow.redact.scrub_log_secrets(raw)
    expected = scrub_result.scrubbed
    findings = scrub_result.findings
    if expected and not expected.endswith("\n"):
        expected += "\n"
    assert ok
    assert count == sum(findings.values()) == 1
    assert dest.read_text(encoding="utf-8") == expected


def test_log_publish_main_returns_nonzero_on_secret_scrub_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()

    def _fail(*_args: object, **_kwargs: object) -> tuple[bool, str, str, str]:
        raise design_log_publish_flow.SecretScrubFailure("scrub failed")

    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", _fail)

    rc = design_log_publish_flow.log_publish_main(
        ["--design-tmpdir", str(design), "--run-id", "RUN1", "--issue", "12"]
    )

    assert rc != 0
    out = capsys.readouterr().out
    assert "PUBLISH_OK=false" in out
    assert "SECRET_SCRUB_VIOLATIONS=0" in out


def test_publish_design_logs_classifies_archive_finalization_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("plain\n", encoding="utf-8")
    def _completed(
        argv: list[str], returncode: int, stdout: str = "", stderr: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    def _fake_run(
        argv: list[str], *, cwd: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        del cwd
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return _completed(argv, 0, str(tmp_path))
        if len(argv) >= 4 and argv[2:4] == ["run-log", "init"]:
            return _completed(argv, 0)
        return _completed(argv, 0)

    def _copy_ok(*_args: object, **_kwargs: object) -> tuple[bool, int]:
        return True, 0

    monkeypatch.setattr(design_log_publish_flow, "_run", _fake_run)
    monkeypatch.setattr(design_log_publish_flow, "_copy_tree_redacted", _copy_ok)
    context = run_lifecycle.LifecycleStart(
        repo_root=tmp_path,
        storage_root=ToolRepositoryStorage(StorageBase("s3", "bucket"), "consumer"),
        skill="design",
        run_id="RUN1",
        log_root=tmp_path / "logs",
        run_dir=tmp_path / "logs" / "design" / "RUN1",
        context_file=tmp_path / "context.json",
    )
    _ = run_logs.log_init(log_root=context.log_root, skill="design", run_id="RUN1")
    monkeypatch.setattr(
        design_log_publish_flow.run_lifecycle,
        "load_run_context",
        lambda **_kwargs: context,
    )

    def fail_publish(**_kwargs: object) -> run_lifecycle.LifecycleTerminal:
        raise run_log_publisher.PublicationError("secret survived scrubbing")

    monkeypatch.setattr(
        design_log_publish_flow.run_lifecycle, "finish_run", fail_publish
    )

    result = design_log_publish_flow._publish_design_logs(
        request=design_log_publish_flow.PublishDesignLogsRequest(
            plugin_root=tmp_path,
            design_tmpdir=design,
            run_id="RUN1",
            issue="12",
            repo="",
            lifecycle_outcome="success",
        )
    )
    assert result[0] is False


def test_publish_excluded_github_redundant_top_level_only() -> None:
    # GitHub-redundant snapshots duplicate the issue body / larch:diagrams comment
    # and are dropped at the top level only, so a curated subtree copy (e.g.
    # plan-review/round-N/panel-manifest.ndjson) is never collaterally dropped (#4782).
    redundant = [
        "issue-body.txt",
        "issue.json",
        "architecture-diagram.md",
        "architecture-diagram.candidate.md",
        "architecture-diagram.skipped",
        "architecture-diagram-generation.failure.log",
        "architecture-diagram-sanitizer.failure.log",
        "panel-manifest.ndjson",
    ]
    for name in redundant:
        assert design_log_publish_flow._publish_excluded(
            name, is_dir=False, top_level=True
        ), name
        assert not design_log_publish_flow._publish_excluded(name, is_dir=False), name
    # Universal carriers stay excluded at every depth regardless of top_level.
    carrier = "codex-primary-plan-arch-output.txt.events.jsonl"
    assert design_log_publish_flow._publish_excluded(
        carrier, is_dir=False, top_level=False
    )
    assert design_log_publish_flow._publish_excluded(
        carrier, is_dir=False, top_level=True
    )


def test_log_publish_drops_github_redundant_top_level_keeps_subtree(
    tmp_path: Path,
) -> None:
    # GitHub-redundant snapshots (issue body, issue.json, the architecture diagram
    # already upserted to larch:diagrams, the top-level panel manifest) are dropped
    # at the top level, while the curated plan-review/round-N/ copies of the same
    # basenames survive. Restores the pre-#3681 bash exclusions (#4782).
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("PLAN", encoding="utf-8")
    for name in (
        "issue-body.txt",
        "issue.json",
        "architecture-diagram.md",
        "architecture-diagram.candidate.md",
        "architecture-diagram.skipped",
        "architecture-diagram-generation.failure.log",
        "architecture-diagram-sanitizer.failure.log",
        "panel-manifest.ndjson",
    ):
        _ = (design / name).write_text("REDUNDANT", encoding="utf-8")
    pr_round = design / "plan-review" / "round-1"
    pr_round.mkdir(parents=True)
    _ = (pr_round / "panel-manifest.ndjson").write_text(
        '{"tool":"codex"}', encoding="utf-8"
    )
    _ = (pr_round / "findings-classification.tsv").write_text(
        "id\tstatus\n", encoding="utf-8"
    )
    _ = (pr_round / "architecture-diagram.md").write_text("CURATED", encoding="utf-8")
    _ = (pr_round / "architecture-diagram.candidate.md").write_text(
        "CURATED CANDIDATE", encoding="utf-8"
    )

    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr

    cached = _cached_run(repo, bin_dir)
    tree = {path.relative_to(cached).as_posix() for path in cached.rglob("*")}
    for name in (
        "issue-body.txt",
        "issue.json",
        "architecture-diagram.md",
        "architecture-diagram.candidate.md",
        "architecture-diagram.skipped",
        "architecture-diagram-generation.failure.log",
        "architecture-diagram-sanitizer.failure.log",
        "panel-manifest.ndjson",
    ):
        assert name not in tree, f"expected top-level drop: {name}\n{tree}"
    assert "plan-review/round-1/panel-manifest.ndjson" in tree
    assert "plan-review/round-1/architecture-diagram.md" in tree
    assert "plan-review/round-1/architecture-diagram.candidate.md" in tree
    assert "plan.txt" in tree


def test_log_publish_excludes_bounded_diagram_failure_sidecars(tmp_path: Path) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("PLAN", encoding="utf-8")
    _ = (design / "design-step-5b.5-diagram-failure.bounded.log").write_text(
        "site=design Step 5b.5\nreason=generation-failed\nexit-code=1\n",
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr

    cached = _cached_run(repo, bin_dir)
    tree = {path.relative_to(cached).as_posix() for path in cached.rglob("*")}
    assert "plan.txt" in tree
    assert "design-step-5b.5-diagram-failure.bounded.log" not in tree


# pyright: reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
