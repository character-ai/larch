# pyright: reportPrivateUsage=false
"""Tests for /design log publish flow port."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from larch.design import design_log_publish_flow
from larch.design import design_summary

RUN_ID = "ABCDEF01-2345-6789-ABCD-EF0123456789"
LOG_BRANCH = f"larch-logs/design-{RUN_ID}"


def _git(*argv: str, cwd: Path) -> None:
    _ = subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)


def _write_gh_stub(path: Path, *, pr_create_rc: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "pr" ] && [ "$2" = "create" ]; then\n'
        f"  if [ {pr_create_rc} -ne 0 ]; then echo 'gh: pr create failed' >&2; exit {pr_create_rc}; fi\n"
        "  echo 'https://github.com/o/r/pull/77'\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "merge" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _operator_repo_with_remote(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("checkout", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@example.com", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    _ = (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-q", "-m", "seed", cwd=repo)
    origin = tmp_path / "origin.git"
    _git("init", "-q", "--bare", str(origin), cwd=tmp_path)
    _git("remote", "add", "origin", str(origin), cwd=repo)
    _git("push", "-q", "-u", "origin", "main", cwd=repo)
    return repo


def _run_publish(repo: Path, design: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    real_cli = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    # The real cli is used for run-log init/commit + redact; all git writes are
    # cwd-scoped to the disposable worktree, never the operator or plugin repo.
    env["CLAUDE_PLUGIN_ROOT"] = str(Path(real_cli).resolve().parents[1])
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
            "--outcome",
            "approved",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
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
        [sys.executable, str(cli_py), "design", "log-publish", "--design-tmpdir", str(design), "--run-id", "RUN1", "--issue", "12", "--outcome", "approved", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PUBLISH_OK=true" in result.stdout



def test_log_publish_captures_transcript_before_publish(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str, str]:
        order.append("publish")
        return (True, "77", "https://github.com/o/r/pull/77", "", "0")

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_CLAUDE_PID", "12345")
    monkeypatch.setattr(design_log_publish_flow.design_publish, "_capture_design_transcript", fake_capture)
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", fake_render)
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main([
        "--design-tmpdir", str(design),
        "--run-id", RUN_ID,
        "--issue", "33",
        "--repo", "o/r",
        "--reason", "final",
        "--outcome", "approved",
    ])

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


def test_log_publish_capture_failure_skips_publish(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    published = False

    def fake_capture(*, ctx: Any) -> bool:
        assert ctx.session_id == RUN_ID
        return False

    def fake_publish(**_kwargs: object) -> tuple[bool, str, str, str, str]:
        nonlocal published
        published = True
        return (True, "77", "https://github.com/o/r/pull/77", "", "0")

    monkeypatch.setattr(design_log_publish_flow.design_publish, "_capture_design_transcript", fake_capture)
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main([
        "--design-tmpdir", str(design), "--run-id", RUN_ID, "--issue", "33", "--outcome", "approved"
    ])

    assert rc == 0
    assert not published
    assert "PUBLISH_OK=false" in capsys.readouterr().out


def test_log_publish_capture_skip_still_publishes_pause(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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

    def fake_publish(**kwargs: object) -> tuple[bool, str, str, str, str]:
        reasons.append(str(kwargs["run_id"]))
        return (True, "", "", "", "0")

    monkeypatch.setattr(design_log_publish_flow.design_publish, "_capture_design_transcript", fake_capture)
    monkeypatch.setattr(design_log_publish_flow, "_render_final_summary_before_copy", fake_render)
    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", fake_publish)

    rc = design_log_publish_flow.log_publish_main([
        "--design-tmpdir", str(design),
        "--run-id", RUN_ID,
        "--issue", "33",
        "--reason", "pause",
        "--outcome", "paused",
    ])

    assert rc == 0
    assert reasons == ["paused", RUN_ID]
    assert "PUBLISH_OK=true" in capsys.readouterr().out

def test_log_publish_commits_pushes_and_opens_pr(tmp_path: Path) -> None:
    # The design run tree is committed to a dedicated branch and PR'd; the
    # operator working tree stays clean (issue #4395), and ship is best-effort.
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    assert "PR_NUMBER=77" in result.stdout
    assert "PR_URL=https://github.com/o/r/pull/77" in result.stdout
    # The publish surfaces the scrub-violation count so the design tail can warn
    # the operator to rotate; a clean run reports zero (#4782).
    assert "SECRET_SCRUB_VIOLATIONS=0" in result.stdout
    # The operator working tree is never polluted, so the next /implement passes preflight.
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=False)
    assert status.stdout.strip() == "", status.stdout
    # The clean-success path deletes the local branch (it lives on the remote).
    branches = subprocess.run(["git", "branch", "--list", LOG_BRANCH], cwd=repo, capture_output=True, text=True, check=False)
    assert branches.stdout.strip() == ""
    # The pushed branch carries the redacted design run tree.
    origin = tmp_path / "origin.git"
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", LOG_BRANCH], cwd=origin, capture_output=True, text=True, check=False)
    assert f"larch-logs/design/{RUN_ID}/artifact.txt" in ls.stdout, ls.stdout
    assert f"larch-logs/design/{RUN_ID}/final-summary.md" in ls.stdout, ls.stdout
    assert f"larch-logs/design/{RUN_ID}/manifest.json" in ls.stdout, ls.stdout
    meta = (design / ".design-log-publish-metadata.env").read_text(encoding="utf-8")
    assert "DESIGN_LOG_PR_NUMBER=77" in meta


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
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

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
            return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")
        return original_run_cli(*args)

    def fake_capture(**_kwargs: object) -> bool:
        return True

    def fake_spawn(**_kwargs: object) -> None:
        return

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setattr(design_log_publish_flow.design_publish, "_capture_design_transcript", fake_capture)
    monkeypatch.setattr(design_log_publish_flow, "_spawn_detached_admin_merge", fake_spawn)
    monkeypatch.setattr(design_summary, "render_final_summary_for_request", capture_render)
    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)  # pyright: ignore[reportPrivateUsage]

    rc = design_log_publish_flow.log_publish_main([
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
    ])

    assert rc == 0
    assert captured["request"].upsert_summary_comment is False
    assert not upsert_calls
    origin = tmp_path / "origin.git"
    blob = subprocess.run(
        ["git", "show", f"{LOG_BRANCH}:larch-logs/design/{RUN_ID}/final-summary.md"],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    )
    assert blob.returncode == 0, blob.stderr
    assert "STALE-SENTINEL" not in blob.stdout
    assert "## /design run" in blob.stdout
    assert "<!-- larch:run-summary v=1 -->" in blob.stdout


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
            return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")
        return original_run_cli(*args)

    def fake_capture(**_kwargs: object) -> bool:
        return True

    def fake_spawn(**_kwargs: object) -> None:
        return

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setattr(design_log_publish_flow.design_publish, "_capture_design_transcript", fake_capture)
    monkeypatch.setattr(design_log_publish_flow, "_spawn_detached_admin_merge", fake_spawn)
    monkeypatch.setattr(design_summary, "render_final_summary_for_request", capture_render)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render_main)
    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)  # pyright: ignore[reportPrivateUsage]

    rc = design_log_publish_flow.log_publish_main([
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
    ])

    assert rc == 0
    assert captured["request"].upsert_summary_comment is False
    assert not upsert_calls
    origin = tmp_path / "origin.git"
    blob = subprocess.run(
        ["git", "show", f"{LOG_BRANCH}:larch-logs/design/{RUN_ID}/final-summary.md"],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    )
    assert blob.returncode != 0
    tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", LOG_BRANCH],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    assert f"larch-logs/design/{RUN_ID}/final-summary.md" not in tree
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
    origin = tmp_path / "origin.git"
    blob = subprocess.run(
        ["git", "show", f"{LOG_BRANCH}:larch-logs/design/{RUN_ID}/secret.txt"],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    )
    assert blob.returncode == 0, blob.stderr
    assert raw_token not in blob.stdout
    assert "<REDACTED-TOKEN>" in blob.stdout


def test_log_publish_pr_failure_keeps_tree_clean_and_emits_recovery(tmp_path: Path) -> None:
    # If the PR cannot be opened, the operator tree still stays clean and the
    # pushed branch is surfaced as a recovery branch (PUBLISH_OK=false).
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=1)

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=false" in result.stdout
    assert f"RECOVERY_BRANCH={LOG_BRANCH}" in result.stdout
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=False)
    assert status.stdout.strip() == "", status.stdout
    origin = tmp_path / "origin.git"
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", LOG_BRANCH], cwd=origin, capture_output=True, text=True, check=False)
    assert f"larch-logs/design/{RUN_ID}/artifact.txt" in ls.stdout, ls.stdout


def test_spawn_detached_admin_merge_routes_to_ship_design_log(monkeypatch: pytest.MonkeyPatch) -> None:
    # Bug #4524: GitHub-native --auto can never satisfy the active "Code review"
    # ruleset's required-review gate for an unreviewed automated PR, so log PRs
    # never merge. The fix routes the log PR through the existing ship design-log
    # admin-merge waiter, launched detached so /design is not blocked on CI (#4404).
    captured_argv: list[str] = []
    captured_kwargs: dict[str, object] = {}

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        captured_argv.extend(argv)
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", fake_popen)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge(cli="/p/python/cli.py", pr_number="77", repo="o/r", repo_root="/repo")

    assert captured_argv == [
        sys.executable, "/p/python/cli.py", "ship", "design-log", "--pr-number", "77", "--repo", "o/r",
    ]
    assert "--auto" not in captured_argv
    assert captured_kwargs["start_new_session"] is True
    assert captured_kwargs["cwd"] == "/repo"
    assert captured_kwargs["stdin"] == subprocess.DEVNULL
    assert captured_kwargs["stdout"] == subprocess.DEVNULL
    assert captured_kwargs["stderr"] == subprocess.DEVNULL


def test_spawn_detached_admin_merge_omits_repo_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_argv: list[str] = []

    def fake_popen(argv: list[str], **_kwargs: object) -> object:
        captured_argv.extend(argv)
        return object()

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", fake_popen)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge(cli="/p/python/cli.py", pr_number="77", repo="", repo_root="/repo")

    assert captured_argv == [sys.executable, "/p/python/cli.py", "ship", "design-log", "--pr-number", "77"]
    assert "--repo" not in captured_argv


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
    ]
    for name in excluded:
        assert design_log_publish_flow._publish_excluded(name, is_dir=False), name
    assert design_log_publish_flow._publish_excluded(
        "design-step-5b.5-diagram-failure.bounded.log",
        is_dir=False,
        top_level=True,
    )
    assert design_log_publish_flow._publish_excluded("panel-prompt-sizes.tsv", is_dir=False, top_level=True)
    kept = [
        "plan.txt",
        "composed-plan.diff",
        "findings.md",
        "voting-tally.md",
        "accepted-plan-findings.md",
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
    }
    for name, body in {**keep, **drop}.items():
        _ = (design / name).write_text(body, encoding="utf-8")
    # Nested: plan-review/round-1/ keeps curated files, drops sidecars.
    pr_round = design / "plan-review" / "round-1"
    pr_round.mkdir(parents=True)
    _ = (pr_round / "findings.md").write_text("NF", encoding="utf-8")
    _ = (pr_round / "codex-vote-output.txt").write_text("VOTE", encoding="utf-8")
    _ = (pr_round / "panel-prompt-sizes.tsv").write_text("site\tslot\n", encoding="utf-8")
    _ = (pr_round / "codex-vote-output.txt.events.jsonl").write_text("{}", encoding="utf-8")
    _ = (pr_round / "findings-ledger.tsv").write_text("round\tfinding_id\n", encoding="utf-8")
    # Whole-subtree drops.
    autofix = design / "plan-autofix"
    autofix.mkdir()
    _ = (autofix / "codex-output.txt").write_text("AF", encoding="utf-8")
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "step-3-terminal").write_text("", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr

    origin = tmp_path / "origin.git"
    ls = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", LOG_BRANCH],
        cwd=origin, capture_output=True, text=True, check=False,
    )
    tree = ls.stdout
    base = f"larch-logs/design/{RUN_ID}"
    for name in keep:
        assert f"{base}/{name}" in tree, f"expected kept: {name}\n{tree}"
    assert f"{base}/plan-review/round-1/findings.md" in tree, tree
    assert f"{base}/plan-review/round-1/codex-vote-output.txt" in tree, tree
    assert f"{base}/plan-review/round-1/panel-prompt-sizes.tsv" in tree, tree
    assert f"{base}/manifest.json" in tree, tree
    for name in drop:
        assert f"{base}/{name}" not in tree, f"expected dropped: {name}\n{tree}"
    assert "codex-vote-output.txt.events.jsonl" not in tree, tree
    assert "findings-ledger.tsv" not in tree, tree
    assert "plan-autofix" not in tree, tree
    assert "/.completed/" not in tree, tree
    assert "step2b-codex-raw" not in tree, tree


def test_scrub_violations_parses_last_numeric() -> None:
    # Mirrors the retired design-publish.sh parse: last occurrence wins, and a
    # missing or non-numeric value defaults to "0" (#4782).
    assert design_log_publish_flow._scrub_violations("<sha>\nSECRET_SCRUB_VIOLATIONS=3\n") == "3"
    assert (
        design_log_publish_flow._scrub_violations(
            "SECRET_SCRUB_VIOLATIONS=1\nSECRET_SCRUB_VIOLATIONS=5\n"
        )
        == "5"
    )
    assert design_log_publish_flow._scrub_violations("no marker here\n") == "0"
    assert design_log_publish_flow._scrub_violations("SECRET_SCRUB_VIOLATIONS=oops\n") == "0"
    assert design_log_publish_flow._scrub_violations("<sha>\nSECRET_SCRUB_VIOLATIONS=0\n") == "0"


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

    def _never_scrubs(text: str) -> tuple[str, dict[str, int]]:
        return text, {"cursor-api-key": 1}

    monkeypatch.setattr(design_log_publish_flow.redact, "scrub_log_secrets", _never_scrubs)
    with pytest.raises(design_log_publish_flow.SecretScrubFailure, match="secret survived"):
        _ = design_log_publish_flow._copy_tree_redacted(plugin_root=plugin_root, source=source, dest=dest)
    assert not dest.exists()


def test_copy_tree_redacted_redact_tmpdir_failure_is_secret_scrub_failure(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    cli = plugin_root / "python" / "cli.py"
    cli.parent.mkdir(parents=True)
    _ = cli.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text("plain\n", encoding="utf-8")

    with pytest.raises(design_log_publish_flow.SecretScrubFailure, match="redact tmpdir-paths"):
        _ = design_log_publish_flow._copy_tree_redacted(plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt")


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
    with pytest.raises(design_log_publish_flow.SecretScrubFailure, match="secret scrubber failed"):
        _ = design_log_publish_flow._copy_tree_redacted(plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt")


def test_copy_tree_redacted_symlink_skip_is_not_secret_scrub_failure(tmp_path: Path) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    target = tmp_path / "target.txt"
    _ = target.write_text("plain\n", encoding="utf-8")
    source = tmp_path / "source-link.txt"
    source.symlink_to(target)

    ok, count = design_log_publish_flow._copy_tree_redacted(plugin_root=plugin_root, source=source, dest=tmp_path / "dest.txt")

    assert not ok
    assert count == 0


def test_copy_tree_redacted_writes_same_scrubbed_text_used_for_count(tmp_path: Path) -> None:
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

    expected, findings = design_log_publish_flow.redact.scrub_log_secrets(raw)
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

    def _fail(*_args: object, **_kwargs: object) -> tuple[bool, str, str, str, str]:
        raise design_log_publish_flow.SecretScrubFailure("scrub failed")

    monkeypatch.setattr(design_log_publish_flow, "_publish_design_logs", _fail)

    rc = design_log_publish_flow.log_publish_main(
        ["--design-tmpdir", str(design), "--run-id", "RUN1", "--issue", "12"]
    )

    assert rc != 0
    out = capsys.readouterr().out
    assert "PUBLISH_OK=false" in out
    assert "SECRET_SCRUB_VIOLATIONS=0" in out


def test_publish_design_logs_classifies_run_log_commit_scrub_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("plain\n", encoding="utf-8")
    calls: list[list[str]] = []

    def _completed(argv: list[str], returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    def _fake_run(argv: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        del cwd
        calls.append(argv)
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return _completed(argv, 0, str(tmp_path))
        if argv[:3] == ["git", "worktree", "add"]:
            return _completed(argv, 0)
        if len(argv) >= 4 and argv[2:4] == ["run-log", "init"]:
            return _completed(argv, 0)
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return _completed(argv, 0, "base\n")
        if len(argv) >= 4 and argv[2:4] == ["run-log", "commit"]:
            return _completed(argv, 1, "", "secret survived scrubbing in larch-logs/design/RUN1/a.txt\n")
        return _completed(argv, 0)

    def _copy_ok(*_args: object, **_kwargs: object) -> tuple[bool, int]:
        return True, 0

    monkeypatch.setattr(design_log_publish_flow, "_run", _fake_run)
    monkeypatch.setattr(design_log_publish_flow, "_copy_tree_redacted", _copy_ok)

    with pytest.raises(design_log_publish_flow.SecretScrubFailure, match="run-log commit"):
        _ = design_log_publish_flow._publish_design_logs(
            plugin_root=tmp_path,
            design_tmpdir=design,
            run_id="RUN1",
            issue="12",
            repo="",
        )

    assert any(len(call) >= 4 and call[2:4] == ["run-log", "commit"] for call in calls)


def test_publish_excluded_github_redundant_top_level_only() -> None:
    # GitHub-redundant snapshots duplicate the issue body / larch:diagrams comment
    # and are dropped at the top level only, so a curated subtree copy (e.g.
    # plan-review/round-N/panel-manifest.ndjson) is never collaterally dropped (#4782).
    redundant = ["issue-body.txt", "issue.json", "architecture-diagram.md", "architecture-diagram.candidate.md", "architecture-diagram.skipped", "architecture-diagram-generation.failure.log", "architecture-diagram-sanitizer.failure.log", "panel-manifest.ndjson"]
    for name in redundant:
        assert design_log_publish_flow._publish_excluded(name, is_dir=False, top_level=True), name
        assert not design_log_publish_flow._publish_excluded(name, is_dir=False), name
    # Universal carriers stay excluded at every depth regardless of top_level.
    carrier = "codex-primary-plan-arch-output.txt.events.jsonl"
    assert design_log_publish_flow._publish_excluded(carrier, is_dir=False, top_level=False)
    assert design_log_publish_flow._publish_excluded(carrier, is_dir=False, top_level=True)


def test_log_publish_drops_github_redundant_top_level_keeps_subtree(tmp_path: Path) -> None:
    # GitHub-redundant snapshots (issue body, issue.json, the architecture diagram
    # already upserted to larch:diagrams, the top-level panel manifest) are dropped
    # at the top level, while the curated plan-review/round-N/ copies of the same
    # basenames survive. Restores the pre-#3681 bash exclusions (#4782).
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("PLAN", encoding="utf-8")
    for name in ("issue-body.txt", "issue.json", "architecture-diagram.md", "architecture-diagram.candidate.md", "architecture-diagram.skipped", "architecture-diagram-generation.failure.log", "architecture-diagram-sanitizer.failure.log", "panel-manifest.ndjson"):
        _ = (design / name).write_text("REDUNDANT", encoding="utf-8")
    pr_round = design / "plan-review" / "round-1"
    pr_round.mkdir(parents=True)
    _ = (pr_round / "panel-manifest.ndjson").write_text('{"tool":"codex"}', encoding="utf-8")
    _ = (pr_round / "architecture-diagram.md").write_text("CURATED", encoding="utf-8")
    _ = (pr_round / "architecture-diagram.candidate.md").write_text("CURATED CANDIDATE", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr

    origin = tmp_path / "origin.git"
    ls = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", LOG_BRANCH],
        cwd=origin, capture_output=True, text=True, check=False,
    )
    tree = ls.stdout
    base = f"larch-logs/design/{RUN_ID}"
    for name in ("issue-body.txt", "issue.json", "architecture-diagram.md", "architecture-diagram.candidate.md", "architecture-diagram.skipped", "architecture-diagram-generation.failure.log", "architecture-diagram-sanitizer.failure.log", "panel-manifest.ndjson"):
        assert f"{base}/{name}" not in tree, f"expected top-level drop: {name}\n{tree}"
    assert f"{base}/plan-review/round-1/panel-manifest.ndjson" in tree, tree
    assert f"{base}/plan-review/round-1/architecture-diagram.md" in tree, tree
    assert f"{base}/plan-review/round-1/architecture-diagram.candidate.md" in tree, tree
    assert f"{base}/plan.txt" in tree, tree


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

    origin = tmp_path / "origin.git"
    ls = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", LOG_BRANCH],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    )
    tree = ls.stdout
    base = f"larch-logs/design/{RUN_ID}"
    assert f"{base}/plan.txt" in tree, tree
    assert f"{base}/design-step-5b.5-diagram-failure.bounded.log" not in tree, tree


def test_spawn_detached_admin_merge_swallows_launch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Best-effort: a launch failure must not raise (the log PR stays open for a
    # manual/CI merge and the working tree is already clean).
    def boom(_argv: list[str], **_kwargs: object) -> object:
        raise OSError("no exec")

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", boom)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge(cli="/p/python/cli.py", pr_number="77", repo="o/r", repo_root="/repo")
