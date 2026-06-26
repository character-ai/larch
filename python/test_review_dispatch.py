# pyright: reportUnusedCallResult=false
"""Parity tests for python/review_dispatch.py leaf dispatch ports."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from larch.core import logging_util
import review_dispatch

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = Path(__file__).resolve().parent


def _reset_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    logging_util.reset_quiet_state()
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")


def _diff(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "diff.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)


def test_classify_diff_library_is_silent_and_fails_generic(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    calls = 0

    def fake_quiet(*, argv0: str | None = None) -> None:
        _ = argv0
        nonlocal calls
        calls += 1

    monkeypatch.setattr(logging_util, "quiet_init", fake_quiet)
    assert review_dispatch.classify_diff(str(tmp_path / "missing.diff")) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, ""))) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/docs/x.md b/docs/y.md extra\n"))) == "generic"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert calls == 0


def test_classify_diff_modes_and_repo_anchored_generators(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    generated_tsv = tmp_path / "generators.tsv"
    generated_tsv.write_text("gen\tagents/generated.md\n", encoding="utf-8")
    monkeypatch.setattr(review_dispatch, "GENERATORS_TSV", generated_tsv)
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/docs/a.md b/docs/a.md\n"))) == "docs-only"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/scripts/test-a.sh b/scripts/test-a.sh\n"))) == "test-only"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/agents/generated.md b/agents/generated.md\n"))) == "generated-only"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/docs/a.md b/scripts/test-a.sh\n"))) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a//abs b//abs\n"))) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/docs/../x.md b/docs/../x.md\n"))) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/docs/guide/chapter.md b/docs/guide/chapter.md\n"))) == "generic"
    assert review_dispatch.classify_diff(str(_diff(tmp_path, "diff --git a/pkg/tests/nested/foo.py b/pkg/tests/nested/foo.py\n"))) == "generic"


def test_classify_diff_main_validation_precedes_quiet(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    calls = 0

    def fake_quiet(*, argv0: str | None = None) -> None:
        _ = argv0
        nonlocal calls
        calls += 1

    monkeypatch.setattr(logging_util, "quiet_init", fake_quiet)
    assert review_dispatch.classify_diff_main([]) == 2
    assert calls == 0
    assert "expected exactly one diff file path" in capsys.readouterr().err
    assert review_dispatch.classify_diff_main([str(tmp_path / "missing")]) == 2
    assert calls == 0
    assert "diff file not found" in capsys.readouterr().err
    diff = _diff(tmp_path, "diff --git a/docs/a.md b/docs/a.md\n")
    assert review_dispatch.classify_diff_main([str(diff)]) == 0
    assert calls == 1
    assert capsys.readouterr().out == "DIFF_MODE=docs-only\n"


def test_wait_validation_and_stdout_grammar(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    for bad in ("0", "00", "000", "abc"):
        assert review_dispatch.wait_reviewers_main(["--timeout", bad, str(tmp_path / "x.done")]) == 1
        assert "must be a positive integer" in capsys.readouterr().err
    assert review_dispatch.wait_reviewers_main(["--timeout"]) == 1
    assert "--timeout requires a value" in capsys.readouterr().err
    assert review_dispatch.wait_reviewers_main([]) == 1
    assert "at least one sentinel" in capsys.readouterr().err
    for bad_poll in ("00", "000", "0", "1.2.3", "abc"):
        monkeypatch.setenv("WAIT_FOR_REVIEWERS_POLL_INTERVAL", bad_poll)
        assert review_dispatch.wait_reviewers_main([str(tmp_path / "x.done")]) == 1
        assert "WAIT_FOR_REVIEWERS_POLL_INTERVAL" in capsys.readouterr().err
    good_done = tmp_path / "good.done"
    good_done.write_text("0\n", encoding="utf-8")
    for good_poll in (".5", "1."):
        monkeypatch.setenv("WAIT_FOR_REVIEWERS_POLL_INTERVAL", good_poll)
        assert review_dispatch.wait_reviewers_main(["--timeout", "1", str(good_done)]) == 0
        assert "DONE 1 good: exit=0" in capsys.readouterr().out
    monkeypatch.setenv("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
    done = tmp_path / "same.done"
    done.write_text("0\n", encoding="utf-8")
    empty = tmp_path / "empty.done"
    empty.write_text("\n", encoding="utf-8")
    assert review_dispatch.wait_reviewers_main(["--timeout", "1", str(done), str(empty), str(tmp_path / "same.done.missing")]) == 0
    out = capsys.readouterr().out
    assert "DONE 1 same: exit=0" in out
    assert "DONE 2 empty: exit=unknown" in out
    assert "TIMEOUT 3 same.done.missing" in out


def test_wait_max_polls_and_suspend_refund(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    assert review_dispatch.wait_max_polls(timeout=1, poll_interval=0.5) == 2
    assert review_dispatch.wait_max_polls(timeout=1, poll_interval=2.0) == 1
    times = [0.0]
    slept: list[float] = []

    def now() -> float:
        return times[0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        times[0] += 61.0 if len(slept) == 1 else seconds

    emitted: list[str] = []
    rc = review_dispatch.wait_reviewers(
        ["missing.done"],
        timeout=1,
        poll_interval=1.0,
        clock=review_dispatch.WaitClock(now=now, sleep=sleep),
        emit_fn=emitted.append,
        diagnostic_fn=lambda _msg: None,
    )
    assert rc == 0
    assert len(slept) == 2
    assert emitted == ["TIMEOUT 1 missing"]


def test_gather_branch_context_outputs_and_excludes_larch_logs(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-b", "main").returncode == 0
    assert _git(repo, "config", "user.email", "test@example.com").returncode == 0
    assert _git(repo, "config", "user.name", "Test User").returncode == 0
    (repo / "src").mkdir()
    (repo / "src" / "feature.txt").write_text("v1\n", encoding="utf-8")
    assert _git(repo, "add", ".").returncode == 0
    assert _git(repo, "commit", "-m", "base code").returncode == 0
    assert _git(repo, "checkout", "-b", "feature").returncode == 0
    (repo / "larch-logs" / "run").mkdir(parents=True)
    (repo / "larch-logs" / "run" / "session.txt").write_text("run-log\n", encoding="utf-8")
    assert _git(repo, "add", "larch-logs").returncode == 0
    assert _git(repo, "commit", "-m", "add run log").returncode == 0
    (repo / "src" / "feature.txt").write_text("v1\nv2\n", encoding="utf-8")
    assert _git(repo, "add", "src/feature.txt").returncode == 0
    assert _git(repo, "commit", "-m", "feature change").returncode == 0
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.chdir(repo)
    assert review_dispatch.gather_branch_context_main(["--output-dir", str(out)]) == 0
    captured = capsys.readouterr().out
    assert "DIFF_FILE=" in captured
    assert "COMMIT_COUNT=1" in captured
    diff_text = (out / "diff.txt").read_text(encoding="utf-8")
    file_list_text = (out / "file-list.txt").read_text(encoding="utf-8")
    commit_log_text = (out / "commit-log.txt").read_text(encoding="utf-8")
    assert "src/feature.txt" in diff_text
    assert "src/feature.txt" in file_list_text
    assert "feature change" in commit_log_text
    assert "add run log" not in commit_log_text
    assert "larch-logs" not in diff_text
    assert "larch-logs" not in file_list_text
    assert review_dispatch.gather_branch_context_main(["--output-dir", str(tmp_path / "missing")]) == 1


def test_gather_branch_context_uses_remote_tracking_base_when_local_main_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for issue #5460: review base must be origin/main, not stale local main.

    When origin/main advances (another PR merges) and the feature branch is
    rebased onto it mid-run while local main stays behind, the inherited
    already-merged commit must not appear in the review diff/file-list/log.
    """
    _reset_quiet(monkeypatch)
    origin = tmp_path / "origin.git"
    assert _git(tmp_path, "init", "--bare", "-b", "main", str(origin)).returncode == 0
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-b", "main").returncode == 0
    assert _git(repo, "config", "user.email", "test@example.com").returncode == 0
    assert _git(repo, "config", "user.name", "Test User").returncode == 0
    assert _git(repo, "remote", "add", "origin", str(origin)).returncode == 0
    (repo / "feature.txt").write_text("v1\n", encoding="utf-8")
    assert _git(repo, "add", ".").returncode == 0
    assert _git(repo, "commit", "-m", "base A").returncode == 0
    assert _git(repo, "push", "origin", "main").returncode == 0
    base_a = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert _git(repo, "checkout", "-b", "feature").returncode == 0
    (repo / "feature.txt").write_text("v1\nfeature-edit\n", encoding="utf-8")
    assert _git(repo, "add", "feature.txt").returncode == 0
    assert _git(repo, "commit", "-m", "feature change").returncode == 0
    # Another PR advances origin/main to B (touching an unrelated file); local
    # main is then rewound to A so it is stale relative to origin/main.
    assert _git(repo, "checkout", "main").returncode == 0
    (repo / "unrelated.txt").write_text("other-pr\n", encoding="utf-8")
    assert _git(repo, "add", "unrelated.txt").returncode == 0
    assert _git(repo, "commit", "-m", "unrelated PR merged to main").returncode == 0
    base_b = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert _git(repo, "push", "origin", "main").returncode == 0
    assert _git(repo, "reset", "--hard", base_a).returncode == 0
    # Feature inherits B via a mid-run rebase onto the advanced base.
    assert _git(repo, "checkout", "feature").returncode == 0
    assert _git(repo, "rebase", base_b).returncode == 0
    # Rebase checkpoints fetch origin/main during a real run; refresh the
    # remote-tracking ref here so it reflects B (gather no longer fetches).
    assert _git(repo, "fetch", "origin", "main").returncode == 0
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.chdir(repo)
    assert review_dispatch.gather_branch_context_main(["--output-dir", str(out)]) == 0
    captured = capsys.readouterr().out
    assert "COMMIT_COUNT=1" in captured
    diff_text = (out / "diff.txt").read_text(encoding="utf-8")
    file_list_text = (out / "file-list.txt").read_text(encoding="utf-8")
    commit_log_text = (out / "commit-log.txt").read_text(encoding="utf-8")
    # The branch's own change is present.
    assert "feature.txt" in file_list_text
    assert "feature change" in commit_log_text
    # The inherited, already-merged change is excluded (the bug included it).
    assert "unrelated.txt" not in file_list_text
    assert "unrelated.txt" not in diff_text
    assert "unrelated PR merged to main" not in commit_log_text


def test_compose_collector_failure_log_sections_redaction_and_bounds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    reviewer = tmp_path / "reviewer.txt"
    reviewer.write_text("reviewer body\n", encoding="utf-8")
    (tmp_path / "reviewer.txt.diag").write_text("diag body\n", encoding="utf-8")
    secret = "sk-" + "a" * 24
    session_path = tmp_path / "larch-implement-redact123"
    (tmp_path / "reviewer.txt.launch-stderr").write_text("\n".join(f"line {i} {session_path} {secret}" for i in range(40)), encoding="utf-8")
    (tmp_path / "reviewer.txt.stderr-tail").write_text("é" * 6000, encoding="utf-8")
    output = tmp_path / "failure.log"
    assert review_dispatch.compose_collector_failure_log_main([
        "--reviewer-file", str(reviewer),
        "--structured-record", "STATUS=FAILED",
        "--output", str(output),
    ]) == 0
    text = output.read_text(encoding="utf-8")
    assert "## Structured collector record" in text
    assert "reviewer body" in text
    assert "diag body" in text
    assert secret not in text
    launch_tail = review_dispatch.render_failed_agent_stderr_tail(str(tmp_path / "reviewer.txt.launch-stderr"))
    assert str(session_path) not in launch_tail
    tail = review_dispatch.render_failed_agent_stderr_tail(str(tmp_path / "reviewer.txt.stderr-tail"))
    assert len(tail.encode("utf-8")) <= 5120
    bad_output = tmp_path / "bad.log"
    assert review_dispatch.compose_collector_failure_log_main(["--structured-record", "", "--output", str(bad_output)]) == 2
    assert not bad_output.exists()
    assert review_dispatch.compose_collector_failure_log_main(["--structured-record", "X", "--output", str(tmp_path / "missing" / "out")]) == 2
