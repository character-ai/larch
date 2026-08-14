# pyright: reportUnusedCallResult=false
"""Tests for rendering.py ports."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from larch.core import config
from larch.core import proc
from larch.review import findings_ledger
from larch.core import logging_util
from larch.rendering import rendering
from larch.rendering import _rendering_helpers as helpers
from larch.review import voting
from tests.support.design_wire import plan_body, run_params_json

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = Path(__file__).resolve().parents[2]


def _write_voter_calibration_stats(*, path: Path, stats: list[voting.VoterCalibrationStat]) -> None:
    header = "tool\tyes_votes\tvalid_yes_severity_count\tmajor\tminor\tnit\tmissing_severity\thigh_rate\tcalibration_score\tuncalibrated\n"
    rows = [
        "\t".join(
            [
                stat.tool,
                str(stat.yes_votes),
                str(stat.valid_yes_severity_count),
                str(stat.major),
                str(stat.minor),
                str(stat.nit),
                str(stat.missing_severity),
                "" if stat.high_rate is None else f"{stat.high_rate:.3f}",
                "" if stat.calibration_score is None else f"{stat.calibration_score:.3f}",
                str(stat.uncalibrated).lower(),
            ]
        )
        for stat in stats
    ]
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def _reset_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    logging_util.reset_quiet_state()
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")


def _stub_rust_diff_classifier(monkeypatch: pytest.MonkeyPatch, *, mode: str = "generic") -> None:
    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        return proc.CommandResult(tuple(argv), 0, f"DIFF_MODE={mode}\n", "", 0.0)

    monkeypatch.setattr(rendering.proc, "run", fake_run)


def _patch_architectural_guidelines(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    content: str,
    *,
    invariant_status: str = "absent",
    invariant_content: str = "",
) -> None:
    def read_guidelines() -> rendering.architectural_guidelines.ArchitecturalGuidelinesResult:
        return rendering.architectural_guidelines.ArchitecturalGuidelinesResult(
            status,
            REPO_ROOT,
            REPO_ROOT / "ARCHITECTURAL_GUIDELINES.md",
            content,
        )

    def read_invariants() -> rendering.architectural_guidelines.ArchitecturalGuidelinesResult:
        return rendering.architectural_guidelines.ArchitecturalGuidelinesResult(
            invariant_status,
            REPO_ROOT,
            REPO_ROOT / "ARCHITECTURAL_INVARIANTS.md",
            invariant_content,
        )

    monkeypatch.setattr(rendering.architectural_guidelines, "read_guidelines", read_guidelines)
    monkeypatch.setattr(rendering.architectural_guidelines, "read_invariants", read_invariants)


def _lane_status_fixture(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "lanes.env"
    _ = path.write_text(body, encoding="utf-8")
    return path


def _all_ok_lane_body() -> str:
    return """\
RESEARCH_ARCH_STATUS=ok
RESEARCH_ARCH_REASON=
RESEARCH_EDGE_STATUS=ok
RESEARCH_EDGE_REASON=
RESEARCH_EXT_STATUS=ok
RESEARCH_EXT_REASON=
RESEARCH_SEC_STATUS=ok
RESEARCH_SEC_REASON=
VALIDATION_CODE_STATUS=ok
VALIDATION_CODE_REASON=
VALIDATION_CURSOR_STATUS=ok
VALIDATION_CURSOR_REASON=
VALIDATION_CODEX_STATUS=ok
VALIDATION_CODEX_REASON=
"""


def test_mermaid_from_md_rejection_reports_heading(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "doc.md"
    _ = doc.write_text(
        "## Architecture Diagram\n\n```mermaid\nflowchart LR\n  A[bad|pipe] --> B\n```\n",
        encoding="utf-8",
    )
    rc = rendering.mermaid_sanitize_main(["--input", str(doc), "--from-md"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=rejected" in out
    assert "REASON_TOKEN=pipe-in-node-label fence=1 line=2" in out
    assert "FENCE_1_HEADING=architecture" in out


def test_render_lane_status_sanitizes_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    kv = tmp_path / "lanes.env"
    _ = kv.write_text(
        "RESEARCH_ARCH_STATUS=fallback_probe_failed\nRESEARCH_ARCH_REASON=a=b | c\nVALIDATION_CODE_STATUS=ok\n",
        encoding="utf-8",
    )
    rc = rendering.render_lane_status_main(["--input", str(kv)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RESEARCH_ARCH_HEADER=Architecture: Claude-fallback (probe failed: ab c)" in out
    assert "VALIDATION_CODE_HEADER=Code: ✅" in out


def test_render_lane_status_uses_last_value_and_ignores_advisory_noise(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    kv = _lane_status_fixture(
        tmp_path,
        "# comment\nRESEARCH_ARCH_STATUS=failed\nRESEARCH_ARCH_STATUS=ok\nnot-a-kv\n",
    )

    assert rendering.render_lane_status_main(["--input", str(kv)]) == 0
    assert "RESEARCH_ARCH_HEADER=Architecture: ✅" in capsys.readouterr().out


def test_reviewer_renderer_preserves_ampersand_target(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    q = tmp_path / "q.txt"
    c = tmp_path / "c.txt"
    ins = tmp_path / "ins.txt"
    _ = q.write_text("question", encoding="utf-8")
    _ = c.write_text("context with {REVIEW_TARGET}", encoding="utf-8")
    _ = ins.write_text("Find issues", encoding="utf-8")
    rc = rendering.render_reviewer_main(
        [
            "--target",
            "R&D findings",
            "--research-question-file",
            str(q),
            "--context-file",
            str(c),
            "--in-scope-instruction-file",
            str(ins),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "R&D findings" in out
    assert "context with {REVIEW_TARGET}" in out


def test_diagrams_upsert_dry_run_merges_sections(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    section = tmp_path / "code.md"
    _ = section.write_text("## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A[Start] --> B[Done]\n```\n", encoding="utf-8")
    rc = rendering.diagrams_upsert_main(
        [
            "--issue",
            "42",
            "--code-flow-file",
            str(section),
            "--allow-external-paths",
            "--dry-run",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "<!-- larch:diagrams v1 -->" in out
    assert "## Code Flow Diagram" in out
    assert "UPSERT_STATUS=ok" in out


def test_diagrams_upsert_live_reads_and_mutates_only_through_rust(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    code = tmp_path / "code.md"
    _ = code.write_text(
        "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A[Start] --> B[Done]\n```\n",
        encoding="utf-8",
    )
    existing = (
        "<!-- larch:diagrams v1 -->\n\n"
        "## Architecture Diagram\n\n```mermaid\nflowchart TD\n  A[Root]\n```\n"
    )
    calls: list[tuple[str, str, str]] = []

    def read_marker(
        _runner: object, **kwargs: object
    ) -> rendering.rust_runtime.TrackingIssueReadOutput:
        output = Path(str(kwargs["output_file"]))
        _ = output.write_text(existing, encoding="utf-8")
        calls.append(("read", str(kwargs["issue"]), str(kwargs["repo"])))
        return rendering.rust_runtime.TrackingIssueReadOutput(
            failed=False,
            values={"FOUND": "true", "COMMENT_ID": "11"},
        )

    def upsert(
        _runner: object, **kwargs: object
    ) -> rendering.rust_runtime.TrackingIssueCommentOutput:
        content = Path(str(kwargs["content_file"])).read_text(encoding="utf-8")
        calls.append(("upsert", str(kwargs["marker"]), content))
        assert kwargs["delete_if_empty"] is True
        return rendering.rust_runtime.TrackingIssueCommentOutput(
            failed=False,
            comment_id="11",
            comment_url="https://github.com/owner/repo/issues/42#issuecomment-11",
            updated=True,
        )

    monkeypatch.setattr(rendering.rust_runtime, "tracking_issue_read_marker", read_marker)
    monkeypatch.setattr(rendering.rust_runtime, "tracking_issue_upsert_summary", upsert)

    rc = rendering.diagrams_upsert_main(
        [
            "--issue",
            "42",
            "--repo",
            "owner/repo",
            "--code-flow-file",
            str(code),
            "--allow-external-paths",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert calls[0] == ("read", "42", "owner/repo")
    assert calls[1][0:2] == ("upsert", "<!-- larch:diagrams v1 -->")
    assert "## Architecture Diagram" in calls[1][2]
    assert "## Code Flow Diagram" in calls[1][2]
    assert "COMMENT_URL=https://github.com/owner/repo/issues/42#issuecomment-11" in captured.out
    assert "UPDATED=true" in captured.out


def test_render_lane_status_all_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    rc = rendering.render_lane_status_main(["--input", str(_lane_status_fixture(tmp_path, _all_ok_lane_body()))])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == (
        "RESEARCH_ARCH_HEADER=Architecture: ✅\n"
        "RESEARCH_EDGE_HEADER=Edge cases: ✅\n"
        "RESEARCH_EXT_HEADER=External comparisons: ✅\n"
        "RESEARCH_SEC_HEADER=Security: ✅\n"
        "VALIDATION_CODE_HEADER=Code: ✅\n"
        "VALIDATION_CURSOR_HEADER=Cursor: ✅\n"
        "VALIDATION_CODEX_HEADER=Codex: ✅\n"
    )


def test_render_lane_status_unknown_token_warns(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    body = "RESEARCH_ARCH_STATUS=weird\nVALIDATION_CODE_STATUS=ok\n"
    rc = rendering.render_lane_status_main(["--input", str(_lane_status_fixture(tmp_path, body))])
    captured = capsys.readouterr()
    assert rc == 0
    assert "RESEARCH_ARCH_HEADER=Architecture: (unknown)" in captured.out
    assert "unknown status token weird" in captured.err


def test_render_lane_status_missing_input_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    missing = tmp_path / "missing.env"
    rc = rendering.render_lane_status_main(["--input", str(missing)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "input file missing" in captured.err


def test_render_lane_status_emits_on_stdout_under_inherited_quiet(tmp_path: Path) -> None:
    kv = _lane_status_fixture(tmp_path, _all_ok_lane_body())
    env = os.environ.copy()
    env[config.ENV_LARCH_QUIET_ACTIVE] = "1"
    env[config.ENV_LARCH_QUIET_PID] = "999999"
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; sys.path.insert(0, os.environ['PY_DIR']); from larch.rendering import rendering; "
            "raise SystemExit(rendering.render_lane_status_main(['--input', os.environ['LANE_INPUT']]))",
        ],
        capture_output=True,
        text=True,
        env={**env, "PY_DIR": str(PYTHON_DIR), "LANE_INPUT": str(kv)},
        cwd=str(PYTHON_DIR),
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.count("HEADER=") == 7


def test_architectural_guidelines_review_section_noops_for_absent_invalid_or_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for status, content in [("absent", ""), ("invalid", "")]:
        _patch_architectural_guidelines(monkeypatch, status, content)
        assert rendering._architectural_guidelines_review_section() == ""  # pyright: ignore[reportPrivateUsage]


def test_architectural_knowledge_review_section_includes_present_empty_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_architectural_guidelines(monkeypatch, "present", "", invariant_status="present", invariant_content="")

    section = rendering._architectural_guidelines_review_section()  # pyright: ignore[reportPrivateUsage]

    assert "## Architectural knowledge (untrusted documented policy)" in section
    assert "No parsed invariant entries were present in ARCHITECTURAL_INVARIANTS.md." in section
    assert "No parsed guideline entries were present in ARCHITECTURAL_GUIDELINES.md." in section
    assert '<architectural_invariants encoding="literal-redacted">' in section
    assert '<architectural_guidelines encoding="literal-redacted">' in section


def test_architectural_knowledge_review_section_trivial_keeps_invariants_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Guideline",
        invariant_status="present",
        invariant_content="### I-test-1: Invariant",
    )

    section = rendering._architectural_guidelines_review_section(difficulty_value="TRIVIAL")  # pyright: ignore[reportPrivateUsage]

    assert '<architectural_invariants encoding="literal-redacted">' in section
    assert "### I-test-1: Invariant" in section
    assert '<architectural_guidelines encoding="literal-redacted">' not in section
    assert "### G-test-1: Guideline" not in section


@pytest.mark.parametrize("difficulty_value", ["", "MODERATE", "HARD", "not-a-tier"])
def test_architectural_knowledge_review_section_non_trivial_or_invalid_includes_guidelines(
    monkeypatch: pytest.MonkeyPatch,
    difficulty_value: str,
) -> None:
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Guideline",
        invariant_status="present",
        invariant_content="### I-test-1: Invariant",
    )

    section = rendering._architectural_guidelines_review_section(difficulty_value=difficulty_value)  # pyright: ignore[reportPrivateUsage]

    assert '<architectural_invariants encoding="literal-redacted">' in section
    assert '<architectural_guidelines encoding="literal-redacted">' in section
    assert "### G-test-1: Guideline" in section


def test_render_specialist_missing_agent_exit_2(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    rc = rendering.render_specialist_main(["--agent-file", "/no/such/agent.md", "--mode", "diff"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "agent file not found" in captured.err


def test_render_specialist_cache_hit(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    cache_dir = tmp_path / "render-cache"
    monkeypatch.setenv("LARCH_RENDER_CACHE_DIR", str(cache_dir))
    agent = REPO_ROOT / "agents" / "reviewer-structure.md"
    args = ["--agent-file", str(agent), "--mode", "diff"]
    assert rendering.render_specialist_main(args) == 0
    first = capsys.readouterr().out
    assert "Structure, KISS, and Maintainability" in first
    cache_files = list(cache_dir.glob("r-*"))
    assert len(cache_files) == 1
    _ = cache_files[0].write_text("CACHE HIT SENTINEL\n", encoding="utf-8")
    assert rendering.render_specialist_main(args) == 0
    assert capsys.readouterr().out == "CACHE HIT SENTINEL\n"


def test_write_payload_bytes_sidecar_clamps_negative_payload_bytes(tmp_path: Path) -> None:
    sidecar = tmp_path / "payload.txt"

    rendering._write_payload_bytes_sidecar(str(sidecar), -7)  # pyright: ignore[reportPrivateUsage]

    assert sidecar.read_text(encoding="utf-8") == "0\n"


def test_write_payload_bytes_sidecar_swallows_write_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar = tmp_path / "payload.txt"

    def fail_mkstemp(*_args: object, **_kwargs: object) -> tuple[int, str]:
        raise OSError("boom")

    monkeypatch.setattr(rendering.tempfile, "mkstemp", fail_mkstemp)

    rendering._write_payload_bytes_sidecar(str(sidecar), 13)  # pyright: ignore[reportPrivateUsage]

    assert not sidecar.exists()


def test_write_payload_bytes_sidecar_removes_stale_content_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar = tmp_path / "payload.txt"
    sidecar.write_text("stale\n", encoding="utf-8")
    original_unlink = Path.unlink
    unlink_calls = 0

    def fail_unlink(self: Path, *args: object, **kwargs: object) -> None:
        nonlocal unlink_calls
        if self == sidecar and unlink_calls == 0:
            unlink_calls += 1
            raise OSError("unlink denied")
        return original_unlink(self, *args, **kwargs)

    def fail_replace(self: Path, target: Path) -> Path:
        _ = self
        _ = target
        raise OSError("replace boom")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    monkeypatch.setattr(Path, "replace", fail_replace)

    rendering._write_payload_bytes_sidecar(str(sidecar), 13)  # pyright: ignore[reportPrivateUsage]

    assert not sidecar.exists()


def test_write_payload_bytes_sidecar_swallows_unlink_permission_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar = tmp_path / "payload.txt"
    original_unlink = Path.unlink

    def fail_replace(_self: Path, _target: Path) -> Path:
        raise OSError("replace boom")

    def fail_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self == sidecar or self.name.startswith(f".{sidecar.name}."):
            raise PermissionError("unlink denied")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_unlink)

    rendering._write_payload_bytes_sidecar(str(sidecar), 13)  # pyright: ignore[reportPrivateUsage]

    assert not sidecar.exists()


def test_render_specialist_places_reviewer_body_before_dynamic_context(tmp_path: Path) -> None:
    diff_file = tmp_path / "changes.diff"
    feature_file = tmp_path / "feature.md"
    plan_file = tmp_path / "plan.md"
    _ = diff_file.write_text("diff --git a/example.py b/example.py\n", encoding="utf-8")
    _ = feature_file.write_text("UNIQUE_FEATURE_MARKER\n", encoding="utf-8")
    _ = plan_file.write_text("UNIQUE_PLAN_MARKER\n", encoding="utf-8")
    text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        argparse.Namespace(
            agent_file=str(REPO_ROOT / "agents" / "reviewer-structure.md"),
            mode="diff",
            description_text="",
            scope_files="",
            competition_notice=False,
            competition_notice_file="",
            diff_file=str(diff_file),
            diff_mode="generic",
            commit_count="1",
            plan_file=str(plan_file),
            feature_file=str(feature_file),
            findings_ledger_file="",
            session_env_path="",
        ),
    )

    body_index = text.index("You are a specialist code reviewer")
    task_index = text.index("Review all code changes on the current branch vs main.")
    feature_index = text.index("UNIQUE_FEATURE_MARKER")
    plan_index = text.index("UNIQUE_PLAN_MARKER")
    assert body_index < task_index
    assert body_index < feature_index
    assert body_index < plan_index
    assert str(diff_file) in text
    assert "<feature_description" in text
    assert "<implementation_plan" in text


def test_render_specialist_payload_sidecar_counts_inline_diff_context(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    _stub_rust_diff_classifier(monkeypatch)
    agent = _specialist_agent(tmp_path)
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    diff = tmp_path / "diff.txt"
    sidecar = tmp_path / "payload.txt"
    plan.write_text("PLAN PAYLOAD\n", encoding="utf-8")
    feature.write_text("FEATURE PAYLOAD\n", encoding="utf-8")
    diff.write_text("diff --git a/a b/a\n", encoding="utf-8")

    base_args = [
        "--agent-file",
        str(agent),
        "--mode",
        "diff",
        "--diff-file",
        str(diff),
        "--plan-file",
        str(plan),
        "--feature-file",
        str(feature),
        "--payload-bytes-output",
        str(sidecar),
    ]

    assert rendering.render_specialist_main(base_args) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(plan.read_bytes()) + len(feature.read_bytes())}\n"

    sidecar.write_text("stale\n", encoding="utf-8")
    assert rendering.render_specialist_main([*base_args, "--diff-mode", "test-only"]) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == "0\n"


@pytest.mark.parametrize(
    ("mode", "diff_mode"),
    [
        ("description", ""),
        ("diff", "generic"),
        ("diff", "docs-only"),
    ],
)
def test_render_plan_fidelity_includes_plan_context_for_all_review_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    diff_mode: str,
) -> None:
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    agent = REPO_ROOT / "agents" / "reviewer-plan-fidelity.md"
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    diff = tmp_path / "diff.txt"
    sidecar = tmp_path / "payload.txt"
    plan.write_text("PLAN FIDELITY PAYLOAD\n", encoding="utf-8")
    feature.write_text("FEATURE FIDELITY PAYLOAD\n", encoding="utf-8")
    diff.write_text("diff --git a/docs/a.md b/docs/a.md\n", encoding="utf-8")
    args = [
        "--agent-file",
        str(agent),
        "--mode",
        mode,
        "--plan-file",
        str(plan),
        "--feature-file",
        str(feature),
        "--payload-bytes-output",
        str(sidecar),
    ]
    if mode == "description":
        args.extend(["--description-text", "review plan fidelity", "--scope-files", str(tmp_path / "scope.txt")])
        (tmp_path / "scope.txt").write_text("docs/a.md\n", encoding="utf-8")
    else:
        args.extend(["--diff-file", str(diff), "--diff-mode", diff_mode])

    assert rendering.render_specialist_main(args) == 0
    out = capsys.readouterr().out
    assert "<implementation_plan" in out
    assert "<feature_description" in out
    assert "PLAN FIDELITY PAYLOAD" in out
    assert "FEATURE FIDELITY PAYLOAD" in out
    description_bytes = len(b"review plan fidelity") if mode == "description" else 0
    assert sidecar.read_text(encoding="utf-8") == f"{description_bytes + len(plan.read_bytes()) + len(feature.read_bytes())}\n"


def test_render_specialist_payload_sidecar_counts_competition_notice_only_when_rendered(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    _stub_rust_diff_classifier(monkeypatch)
    agent = _specialist_agent(tmp_path)
    diff = tmp_path / "diff.txt"
    notice = tmp_path / "notice.md"
    sidecar = tmp_path / "payload.txt"
    diff.write_text("diff --git a/a b/a\n", encoding="utf-8")
    notice.write_text("NOTICE PAYLOAD ☕\n", encoding="utf-8")

    base_args = [
        "--agent-file",
        str(agent),
        "--mode",
        "diff",
        "--diff-file",
        str(diff),
        "--competition-notice-file",
        str(notice),
        "--payload-bytes-output",
        str(sidecar),
    ]

    assert rendering.render_specialist_main([*base_args, "--competition-notice"]) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(notice.read_bytes())}\n"

    sidecar.write_text("stale\n", encoding="utf-8")
    assert rendering.render_specialist_main(base_args) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == "0\n"


def test_render_voter_calibration_feedback_contributes_payload_bytes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ballot = tmp_path / "ballot.md"
    stats = tmp_path / "stats.tsv"
    sidecar = tmp_path / "payload.txt"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    _write_voter_calibration_stats(
        path=stats,
        stats=[
            voting.VoterCalibrationStat(
                tool="codex",
                yes_votes=3,
                valid_yes_severity_count=2,
                major=1,
                minor=1,
                nit=0,
                missing_severity=0,
                high_rate=0.5,
                calibration_score=0.25,
                uncalibrated=False,
            )
        ],
    )

    rc = rendering.render_voter_main(
        [
            "--ballot-file",
            str(ballot),
            "--panel-role",
            "judge",
            "--id-grammar",
            "finding-oos",
            "--verification-context",
            "code",
            "--calibration-stats-file",
            str(stats),
            "--voter-tool",
            "codex",
            "--payload-bytes-output",
            str(sidecar),
        ],
    )

    out = capsys.readouterr().out
    assert rc == 0
    expected = rendering._voter_calibration_feedback_block(stats_file=str(stats), voter_tool="codex")  # pyright: ignore[reportPrivateUsage]
    assert expected in out
    assert sidecar.read_text(encoding="utf-8") == f"{len(expected.encode('utf-8'))}\n"


def test_render_specialist_cache_setup_failure_falls_back_uncached(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    blocker = tmp_path / "cache-blocker"
    _ = blocker.write_text("not a directory\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_RENDER_CACHE_DIR", str(blocker / "render-cache"))
    agent = REPO_ROOT / "agents" / "reviewer-structure.md"
    rc = rendering.render_specialist_main(["--agent-file", str(agent), "--mode", "diff"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Structure, KISS, and Maintainability" in out



def test_render_ordinary_specialist_omits_architectural_knowledge(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Keep seams",
        invariant_status="present",
        invariant_content="### I-test-1: Keep hard seams",
    )

    rc = rendering.render_specialist_main(
        ["--agent-file", str(REPO_ROOT / "agents" / "reviewer-correctness.md"), "--mode", "diff"],
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "## Architectural knowledge (untrusted documented policy)" not in out
    assert "### I-test-1: Keep hard seams" not in out
    assert "### G-test-1: Keep seams" not in out






def test_render_specialist_injects_findings_ledger_and_cache_keys_content(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    cache_dir = tmp_path / "cache"
    ledger_root = tmp_path / "review"
    findings_ledger.write_round(
        ledger_root,
        1,
        [{"finding_id": "FINDING_1", "title": "Prior duplicate", "outcome": "rejected"}],
    )
    monkeypatch.setenv("LARCH_RENDER_CACHE_DIR", str(cache_dir))
    agent = REPO_ROOT / "agents" / "reviewer-structure.md"
    args = [
        "--agent-file",
        str(agent),
        "--mode",
        "diff",
        "--findings-ledger-file",
        str(ledger_root / "findings-ledger.tsv"),
    ]
    assert rendering.render_specialist_main(args) == 0
    first = capsys.readouterr().out
    assert "Prior-round findings ledger" in first
    assert "duplicates a `rejected`, `neutral`, or `oos` entry" in first
    assert len(list(cache_dir.glob("r-*"))) == 1

    findings_ledger.write_round(
        ledger_root,
        2,
        [{"finding_id": "FINDING_2", "title": "Another prior", "outcome": "oos"}],
    )
    assert rendering.render_specialist_main(args) == 0
    second = capsys.readouterr().out
    assert "Another prior" in second
    assert len(list(cache_dir.glob("r-*"))) == 2


def test_render_specialist_default_ledger_path_from_implement_tmpdir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    findings_ledger.write_round(
        tmp_path,
        1,
        [{"finding_id": "FINDING_1", "title": "Default path duplicate", "outcome": "rejected"}],
    )
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = rendering.render_specialist_main(
        ["--agent-file", str(REPO_ROOT / "agents" / "reviewer-structure.md"), "--mode", "diff"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Default path duplicate" in out


def test_mermaid_rejects_pipe_in_node_label(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "bad.mmd"
    _ = doc.write_text("flowchart TD\n  A[foo|bar]\n", encoding="utf-8")
    rc = rendering.mermaid_sanitize_main(["--input", str(doc)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=rejected" in out
    assert "REASON_TOKEN=pipe-in-node-label fence=1 line=2" in out


def test_mermaid_warning_log_uses_reason_token_codec(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "bad.mmd"
    _ = doc.write_text("sequenceDiagram\nparticipant A as bad<br/>$\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(rendering.subprocess, "run", fake_run)

    rc = rendering.mermaid_sanitize_main(
        ["--input", str(doc), "--warnings-log", str(tmp_path / "warnings.md"), "--warnings-step", "5"]
    )

    assert rc == 1
    assert "STATUS=rejected" in capsys.readouterr().out
    assert calls[0][-1].endswith("br-in-participant-alias dollar-in-participant-alias")


def test_mermaid_accepts_quoted_pipe_label(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "ok.mmd"
    _ = doc.write_text('flowchart TD\n  A["foo|bar"]\n', encoding="utf-8")
    rc = rendering.mermaid_sanitize_main(["--input", str(doc)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STATUS=ok" in out


def test_mermaid_rejects_unclosed_frontmatter(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "frontmatter.mmd"
    _ = doc.write_text("---\ntitle: example\nflowchart TD\n  A[foo|bar]\n", encoding="utf-8")
    rc = rendering.mermaid_sanitize_main(["--input", str(doc)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=rejected" in out
    assert "REASON_TOKEN=unclosed-frontmatter" in out


def test_render_plan_review_rejects_empty_feature_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    feature = design_tmpdir / "feature.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = feature.write_text("", encoding="utf-8")
    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--feature-file",
            str(feature),
        ],
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "64 KiB" in captured.err


def test_render_plan_review_inlines_strunk_and_white_readability(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = (design_tmpdir / "run-params.json").write_text(
        run_params_json(),
        encoding="utf-8",
    )
    style = tmp_path / "readability-style.md"
    _ = style.write_text(
        "# Fixture Readability Style\n\nWrite with Strunk & White discipline.\n"
        "Precedence: code references > meaning > brevity.\n"
        "Literal token example: `<READABILITY_STYLE>`.\n",
        encoding="utf-8",
    )
    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--readability-style-file",
            str(style),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Strunk & White" in out
    assert "code references > meaning > brevity" in out
    assert "<READABILITY_STYLE>" in out


def test_render_plan_review_cursor_inlines_plan_content(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #5518: Cursor launches with --workspace <repo> and (per the launcher parity rule) no
    # --add-dir grant, so it cannot read the plan file under DESIGN_TMPDIR. The Cursor
    # plan-review prompt must inline the plan content instead of pointing at the unreadable
    # file path, or Cursor returns a canned sentinel without reviewing anything.
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="UNIQUE_PLAN_MARKER_5518 do the thing."), encoding="utf-8")
    _ = (design_tmpdir / "run-params.json").write_text(
        run_params_json(),
        encoding="utf-8",
    )
    rc = rendering.render_plan_review_main(
        ["--archetype", "arch", "--vendor", "cursor", "--plan-file", str(plan), "--design-tmpdir", str(design_tmpdir)],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "UNIQUE_PLAN_MARKER_5518 do the thing." in out
    assert "<larch_plan_under_review>" in out
    assert "Review the implementation plan file at" not in out


def test_render_plan_review_codex_references_plan_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #5518: Codex keeps the plan-file path reference (its sandbox grants the read); the plan
    # body is NOT inlined for Codex.
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="UNIQUE_PLAN_MARKER_5518 do the thing."), encoding="utf-8")
    _ = (design_tmpdir / "run-params.json").write_text(
        run_params_json(),
        encoding="utf-8",
    )
    rc = rendering.render_plan_review_main(
        ["--archetype", "arch", "--vendor", "codex", "--plan-file", str(plan), "--design-tmpdir", str(design_tmpdir)],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Review the implementation plan file at" in out
    assert str(plan) in out
    assert "UNIQUE_PLAN_MARKER_5518 do the thing." not in out
    assert "<larch_plan_under_review>" not in out


def test_render_plan_review_tsv_contract_hardening(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #4994: hardened TSV contract prose must stay in the rendered prompt so CI
    # catches accidental removal of schema_version=1 or focus_area allowlist text.
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = (design_tmpdir / "run-params.json").write_text(
        run_params_json(),
        encoding="utf-8",
    )
    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "literal constant 1 (the schema_version) on EVERY row" in out
    assert "NOT a per-row counter" in out
    assert (
        "focus_area exactly one of code-quality, risk-integration, correctness, architecture, security"
        in out
    )
    assert "no other value such as completeness" in out
    assert "Report at most 3 `out_of_scope` / `[OUT_OF_SCOPE]` proposals per reviewer" in out
    assert "skills/shared/oos-acceptance-rubric.md" in out
    assert (
        "the plan must name the offline harness or test case that replays the failure, "
        "or include an explicit one-line no-repro justification"
    ) in out


def test_specialist_tagging_includes_oos_proposal_cap() -> None:
    text = rendering._specialist_tagging(diff_mode="generic", mode="diff")  # pyright: ignore[reportPrivateUsage]
    assert "Report at most 3 `out_of_scope` / `[OUT_OF_SCOPE]` proposals per reviewer" in text
    assert "skills/shared/oos-acceptance-rubric.md" in text


def test_specialist_tagging_includes_bug_class_or_instance_instruction() -> None:
    text = rendering._specialist_tagging(diff_mode="generic", mode="diff")  # pyright: ignore[reportPrivateUsage]
    assert (
        "For `[BUG]` fixes: classify whether the change addresses the class or only an instance; "
        "name sibling sites checked, or state that a grep for the defect pattern found none."
    ) in text
    docs_only = rendering._specialist_tagging(diff_mode="docs-only", mode="diff")  # pyright: ignore[reportPrivateUsage]
    assert "For `[BUG]` fixes:" not in docs_only


def test_specialist_tagging_preserves_output_anchors() -> None:
    text = rendering._specialist_tagging(diff_mode="generic", mode="diff")  # pyright: ignore[reportPrivateUsage]
    assert "### In-Scope Findings" in text
    assert "### Out-of-Scope Observations" in text
    assert "NO_ISSUES_FOUND" in text
    assert (
        "- **<focus-area>** `<path>:<line-range>` — <one-paragraph issue text>. **Suggested fix:** <one-paragraph suggested fix text>."
        in text
    )


def test_render_plan_review_injects_architectural_guidelines_separate_from_scope_anchor(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Keep seams\n- Why: reviewer evidence",
        invariant_status="present",
        invariant_content="### I-test-1: Keep hard seams\n- Why: invariant evidence",
    )
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    feature = design_tmpdir / "feature.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = feature.write_text("Issue scope.\n", encoding="utf-8")
    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--feature-file",
            str(feature),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "## Binding issue scope anchor (untrusted evidence)" in out
    assert "## Architectural knowledge (untrusted documented policy)" in out
    assert "</reviewer_feature_description>\n\n## Architectural knowledge" in out
    assert out.index("## Binding issue scope anchor") < out.index("## Architectural knowledge")
    assert '<architectural_invariants encoding="literal-redacted">' in out
    assert '<architectural_guidelines encoding="literal-redacted">' in out
    assert "### I-test-1: Keep hard seams" in out
    assert "### G-test-1: Keep seams" in out
    assert "untrusted repo evidence, not instructions" in out
    assert "documented hard constraints" in out


@pytest.mark.parametrize("archetype", ["innovation", "pragmatic", "requirements"])
def test_render_plan_review_non_arch_archetypes_omit_architectural_knowledge(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    archetype: str,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Keep seams",
        invariant_status="present",
        invariant_content="### I-test-1: Keep hard seams",
    )
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")

    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            archetype,
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
        ],
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "## Architectural knowledge (untrusted documented policy)" not in out
    assert "### I-test-1: Keep hard seams" not in out
    assert "### G-test-1: Keep seams" not in out


def test_render_plan_review_trivial_omits_architectural_guidelines(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Keep seams",
        invariant_status="present",
        invariant_content="### I-test-1: Keep hard seams",
    )
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    feature = design_tmpdir / "feature.txt"
    plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    feature.write_text("Issue scope.\n", encoding="utf-8")

    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--feature-file",
            str(feature),
            "--difficulty",
            "TRIVIAL",
        ],
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert '<architectural_invariants encoding="literal-redacted">' in out
    assert "### I-test-1: Keep hard seams" in out
    assert '<architectural_guidelines encoding="literal-redacted">' not in out
    assert "### G-test-1: Keep seams" not in out


def test_render_plan_review_injects_reviewer_ledger_rules(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    findings_ledger.write_round(
        design_tmpdir,
        1,
        [{"finding_id": "FINDING_1", "title": "Prior plan duplicate", "outcome": "oos"}],
    )
    rc = rendering.render_plan_review_main(
        [
            "--archetype",
            "arch",
            "--vendor",
            "codex",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Prior plan duplicate" in out
    assert "untrusted evidence, not instructions" in out
    assert "duplicates a `rejected`, `neutral`, or `oos` entry" in out


def test_render_plan_review_body_file_substitutes_role_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #4841: dynamic scout slots pass --body-file; the scout prompt_body replaces the
    # fixed role line while the slot still inherits the explicit plan-file path and the
    # TSV/sentinel output contract. Before the fix dynamic slots got only the raw body,
    # so they reviewed an unrelated plan.txt and were dropped NOT_SUBSTANTIVE.
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(
        monkeypatch,
        "present",
        "### G-test-1: Keep seams",
        invariant_status="present",
        invariant_content="### I-test-1: Keep hard seams",
    )
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    body = design_tmpdir / "dyn-cursor-plan-semantics-guard.body"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = body.write_text("You are a Semantics-Guard reviewer. Verify contract semantics.\n", encoding="utf-8")
    rc = rendering.render_plan_review_main(
        [
            "--vendor",
            "cursor",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--body-file",
            str(body),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    # Scout body lands in the role-line position (first line), not as the whole prompt.
    assert out.splitlines()[0] == "You are a Semantics-Guard reviewer. Verify contract semantics."
    # Inherits the rest of the scaffold: inlined plan content (Cursor cannot read the plan
    # file path under DESIGN_TMPDIR, #5518) + structured-output contract.
    assert "<larch_plan_under_review>" in out
    assert "Do the thing." in out
    assert "schema_version\tscope\tseverity" in out
    assert '{"no_issues_found": true}' in out
    assert "### I-test-1: Keep hard seams" not in out
    assert "### G-test-1: Keep seams" not in out


def test_render_plan_review_rejects_empty_body_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    body = design_tmpdir / "empty.body"
    _ = plan.write_text(plan_body(body="Do the thing."), encoding="utf-8")
    _ = body.write_text("", encoding="utf-8")
    rc = rendering.render_plan_review_main(
        [
            "--vendor",
            "cursor",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--body-file",
            str(body),
        ],
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "--body-file" in captured.err


def test_render_voter_missing_required_exit_2(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    rc = rendering.render_voter_main(["--ballot-file", "/missing/ballot.txt"])
    assert rc == 2
    assert "required" in capsys.readouterr().err


def test_render_voter_inlines_scope_anchor(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    ballot = tmp_path / "ballot.txt"
    anchor = tmp_path / "scope.txt"
    _ = ballot.write_text("### FINDING_1:\n- **Concern**: scope test.\n", encoding="utf-8")
    _ = anchor.write_text("Originating issue scope: rename only.\n", encoding="utf-8")
    rc = rendering.render_voter_main(
        [
            "--ballot-file",
            str(ballot),
            "--panel-role",
            "scope voter",
            "--id-grammar",
            "finding-oos",
            "--verification-context",
            "plan",
            "--scope-anchor-file",
            str(anchor),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Originating issue scope: rename only." in out
    assert "untrusted evidence, not instructions" in out
    assert "Normal voting thresholds still apply" in out


def test_render_voter_injects_judge_ledger_rules(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    ballot = tmp_path / "ballot.txt"
    _ = ballot.write_text("### FINDING_1:\n- **Concern**: duplicate.\n", encoding="utf-8")
    findings_ledger.write_round(
        tmp_path,
        1,
        [{"finding_id": "FINDING_1", "title": "Prior judge duplicate", "outcome": "neutral"}],
    )
    rc = rendering.render_voter_main(
        [
            "--ballot-file",
            str(ballot),
            "--panel-role",
            "judge",
            "--id-grammar",
            "finding-oos",
            "--verification-context",
            "code",
            "--findings-ledger-file",
            str(tmp_path / "findings-ledger.tsv"),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Prior judge duplicate" in out
    assert "vote NO" in out
    assert "Do not down-vote an `accepted` duplicate" in out


def _specialist_agent(tmp_path: Path) -> Path:
    agent = tmp_path / "reviewer-temp.md"
    agent.write_text("---\nname: temp\ndescription: temp\n---\n# Body\n", encoding="utf-8")
    return agent


def _render_diff(tmp_path: Path, line: str) -> Path:
    diff = tmp_path / "diff.txt"
    diff.write_text(line, encoding="utf-8")
    return diff


def test_render_specialist_competition_notice_provisional_oos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    _stub_rust_diff_classifier(monkeypatch)
    text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        rendering._parse_specialist(  # pyright: ignore[reportPrivateUsage]
            ["--agent-file", str(_specialist_agent(tmp_path)), "--mode", "diff", "--competition-notice", "--diff-file", str(_render_diff(tmp_path, "diff --git a/a b/a\n"))]
        )
    )
    assert "**Competition notice**" in text
    assert "Review Acceptance Rubric" in text
    assert "OOS files only when accepted" in text
    assert "non-fileable OOS is logged only" in text


def test_render_specialist_uses_rust_docs_diff_classifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        calls.append(argv)
        return proc.CommandResult(tuple(argv), 0, "DIFF_MODE=docs-only\n", "", 0.0)

    monkeypatch.setattr(rendering.proc, "run", fake_run)
    text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        rendering._parse_specialist(  # pyright: ignore[reportPrivateUsage]
            ["--agent-file", str(_specialist_agent(tmp_path)), "--mode", "diff", "--diff-file", str(_render_diff(tmp_path, "diff --git a/docs/a.md b/docs/a.md\n"))]
        )
    )
    assert "Review this docs-only diff" in text
    assert calls[0][1:3] == ["agent", "classify-diff"]


def test_render_specialist_rejects_a_failed_rust_diff_classifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)

    def failed_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        return proc.CommandResult(tuple(argv), 1, "", "manifest malformed", 0.0)

    monkeypatch.setattr(rendering.proc, "run", failed_run)
    with pytest.raises(rendering.RenderError, match="diff classification failed"):
        _ = rendering._classify_diff_mode(str(_render_diff(tmp_path, "diff --git a/docs/a.md b/docs/a.md\n")))  # pyright: ignore[reportPrivateUsage]


def test_render_specialist_uses_rust_test_and_generated_classifiers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        diff = Path(argv[-1]).read_text(encoding="utf-8")
        mode = "test-only" if "scripts/test-a.sh" in diff else "generated-only"
        return proc.CommandResult(tuple(argv), 0, f"DIFF_MODE={mode}\n", "", 0.0)

    monkeypatch.setattr(rendering.proc, "run", fake_run)
    agent = _specialist_agent(tmp_path)
    test_text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        rendering._parse_specialist(  # pyright: ignore[reportPrivateUsage]
            ["--agent-file", str(agent), "--mode", "diff", "--diff-file", str(_render_diff(tmp_path, "diff --git a/scripts/test-a.sh b/scripts/test-a.sh\n"))]
        )
    )
    generated_text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        rendering._parse_specialist(  # pyright: ignore[reportPrivateUsage]
            ["--agent-file", str(agent), "--mode", "diff", "--diff-file", str(_render_diff(tmp_path, "diff --git a/agents/generated.md b/agents/generated.md\n"))]
        )
    )
    assert "Review this test-only diff" in test_text
    assert "Review this generated-only diff" in generated_text


def test_render_specialist_diff_mode_override_skips_classifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    def fail_classifier(*_args: object, **_kwargs: object) -> proc.CommandResult:
        raise AssertionError("override should skip classifier")

    monkeypatch.setattr(rendering.proc, "run", fail_classifier)
    text = rendering._render_specialist_text(  # pyright: ignore[reportPrivateUsage]
        rendering._parse_specialist(  # pyright: ignore[reportPrivateUsage]
            ["--agent-file", str(_specialist_agent(tmp_path)), "--mode", "diff", "--diff-file", str(_render_diff(tmp_path, "diff --git a/docs/a.md b/docs/a.md\n")), "--diff-mode", "test-only"]
        )
    )
    assert "Review this test-only diff" in text


def test_scope_anchor_validate_design_and_render(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    anchor = tmp_path / "anchor.txt"
    anchor.write_text("Scope <only> & token\n", encoding="utf-8")
    rc = rendering.scope_anchor_validate_main(["--mode", "design", "--design-tmpdir", str(tmp_path), "--path", str(anchor)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == str(anchor)
    rc = rendering.render_scope_anchor_main(["--design-tmpdir", str(tmp_path), "--scope-anchor-file", str(anchor)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Plan-review scope anchor" in out
    assert "Scope &lt;only&gt; &amp; token" in out


def test_scope_anchor_validate_rejects_unreadable_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    design = tmp_path / "design"
    design.mkdir()
    anchor = design / "anchor.txt"
    anchor.write_text("scope", encoding="utf-8")
    anchor.chmod(0o000)
    try:
        rc = rendering.scope_anchor_validate_main(["--mode", "design", "--design-tmpdir", str(design), "--path", str(anchor)])
        assert rc == 1
    finally:
        anchor.chmod(0o644)


def test_scope_anchor_validate_rejects_outside_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    design = tmp_path / "design"
    outside = tmp_path / "outside.txt"
    design.mkdir()
    outside.write_text("scope", encoding="utf-8")
    rc = rendering.scope_anchor_validate_main(["--mode", "design", "--design-tmpdir", str(design), "--path", str(outside)])
    assert rc == 1


def test_scope_anchor_common_shape_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "anchor.txt"
    link = tmp_path / "anchor-link.txt"
    target.write_text("scope", encoding="utf-8")
    link.symlink_to(target)
    assert not rendering._scope_anchor_common_shape_ok(link)  # pyright: ignore[reportPrivateUsage]


def test_scope_anchor_common_shape_rejects_zero_byte_file(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor.txt"
    anchor.write_text("", encoding="utf-8")
    assert not rendering._scope_anchor_common_shape_ok(anchor)  # pyright: ignore[reportPrivateUsage]


def test_scope_anchor_common_shape_rejects_oversize_file(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor.txt"
    anchor.write_bytes(b"x" * (rendering._SCOPE_ANCHOR_MAX_BYTES + 1))  # pyright: ignore[reportPrivateUsage]
    assert not rendering._scope_anchor_common_shape_ok(anchor)  # pyright: ignore[reportPrivateUsage]


def test_scope_anchor_common_shape_rejects_crlf_path(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor.txt"
    anchor.write_text("scope", encoding="utf-8")
    assert not rendering._scope_anchor_common_shape_ok(Path(str(anchor) + "\n"))  # pyright: ignore[reportPrivateUsage]
    assert not rendering._scope_anchor_common_shape_ok(Path(str(anchor) + "\r"))  # pyright: ignore[reportPrivateUsage]


def test_scope_anchor_validate_review_accepts_tmp_allowlist(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    review = tmp_path / "review"
    review.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("scope", encoding="utf-8")
    rc = rendering.scope_anchor_validate_main(["--mode", "review", "--review-tmpdir", str(review), "--path", str(outside)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == str(outside)


def test_scope_anchor_relay_and_handoff_precedence(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    parsed = tmp_path / "parsed.txt"
    loop = tmp_path / "loop.txt"
    parsed.write_text("parsed", encoding="utf-8")
    loop.write_text("loop", encoding="utf-8")
    rc = rendering.scope_anchor_design_handoff_main([
        "--design-tmpdir", str(tmp_path),
        "--tally-plan-review-status", "ok",
        "--loop-status", "complete",
        "--candidate", str(parsed),
        "--candidate", str(loop),
    ])
    assert rc == 0
    assert capsys.readouterr().out == str(parsed)
    rc = rendering.scope_anchor_design_handoff_main([
        "--design-tmpdir", str(tmp_path),
        "--tally-plan-review-status", "tally-error",
        "--loop-status", "complete",
        "--candidate", str(parsed),
    ])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_scope_anchor_retally_prefers_parsed(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    parsed = tmp_path / "parsed.txt"
    retally = tmp_path / "retally.txt"
    parsed.write_text("parsed", encoding="utf-8")
    retally.write_text("retally", encoding="utf-8")
    rc = rendering.scope_anchor_retally_handoff_main([
        "--design-tmpdir", str(tmp_path),
        "--tally-plan-review-status", "main-agent-vote-required",
        "--loop-status", "main-agent-vote-required",
        "--parsed-input", str(parsed),
        "--retally-input-anchor", str(retally),
    ])
    assert rc == 0
    assert capsys.readouterr().out == str(parsed)


def _render_voter_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
    id_grammar: str = "finding-oos",
) -> str:
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    rc = rendering.render_voter_main([
        "--ballot-file", str(ballot),
        "--panel-role", "test voter",
        "--id-grammar", id_grammar,
        "--verification-context", "code",
        *extra,
    ])
    assert rc == 0
    return capsys.readouterr().out


def test_render_voter_no_archetype_matches_default_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = _render_voter_text(tmp_path, capsys)
    second = _render_voter_text(tmp_path, capsys)
    assert first == second
    assert "Archetype lens" not in first


def test_render_voter_includes_panel_severity_rubric(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _render_voter_text(tmp_path, capsys)
    assert "Panel severity rubric" in text
    assert "major|minor|nit" in text


def test_oos_proposal_instruction_mentions_legitimacy_standard() -> None:
    text = rendering.oos_proposal_instruction()
    assert "highest-legitimacy concrete items" in text
    assert "legitimacy standard at proposal time" in text


def test_checked_in_reviewer_prompt_surfaces_use_legitimacy_cap() -> None:
    surfaces = [
        REPO_ROOT / "skills" / "shared" / "reviewer-templates.md",
        REPO_ROOT / "agents" / "code-reviewer.md",
        *sorted((REPO_ROOT / "agents").glob("reviewer-*.md")),
        *sorted((REPO_ROOT / "agents" / "pre-rendered").glob("reviewer-*-body.txt")),
    ]

    assert surfaces
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        assert "highest-legitimacy concrete items" in text, str(path)
        assert "highest-materiality" not in text, str(path)


def test_checked_in_reviewer_prompt_surfaces_include_current_change_duplication_gate() -> None:
    surfaces = [
        REPO_ROOT / "skills" / "shared" / "reviewer-templates.md",
        REPO_ROOT / "agents" / "code-reviewer.md",
        *sorted((REPO_ROOT / "agents").glob("reviewer-*.md")),
        *sorted((REPO_ROOT / "agents" / "pre-rendered").glob("reviewer-*-body.txt")),
    ]

    assert surfaces
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        assert "independent implementation of behavior already owned in-repo" in text, str(path)
        assert "Pre-existing duplication" in text or "pre-existing duplication" in text, str(path)


def test_render_voter_oos_rules_mention_genuine_concrete_non_duplicate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = _render_voter_text(tmp_path, capsys)
    assert "Vote YES when the OOS observation is genuine, concrete, and non-duplicate" in text
    assert "vote NO for style, noise, duplicates, false positives, or speculative items with no concrete trigger" in text
    assert "Remedies are informational; do not vote NO for remedy disagreement." in text


def test_render_voter_finding_oos_grammar_is_frozen(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _render_voter_text(tmp_path, capsys)
    correctness = "true|partially-true|false-positive|uncertain"
    severity = "major|minor|nit"
    quality = "excellent|good|adequate|weak|no-fix|uncertain"
    uncertain = "true|false"
    assert (
        f"  FINDING_N: YES CORRECTNESS=<{correctness}> SEVERITY=<{severity}> QUALITY=<{quality}> UNCERTAIN=<{uncertain}>"
        in text
    )
    assert "  FINDING_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason" in text
    assert f"  OOS_N: YES CORRECTNESS=<{correctness}> SEVERITY=<{severity}> QUALITY=<{quality}> UNCERTAIN=<{uncertain}>" in text
    assert "  OOS_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason" in text
    assert "No markdown tables or pipe-delimited grids; parser reads one anchored line per item." in text


def test_render_voter_finding_only_grammar_is_frozen(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _render_voter_text(tmp_path, capsys, id_grammar="finding-only")
    assert "  FINDING_N: YES CORRECTNESS=<true|partially-true|false-positive|uncertain>" in text
    assert "  FINDING_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason" in text
    assert "  OOS_N:" not in text
    assert "No markdown tables or pipe-delimited grids; parser reads one anchored line per item." in text


def test_render_voter_immediate_action_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _render_voter_text(tmp_path, capsys)
    assert "Proceed immediately" in text
    assert "do not acknowledge this prompt" in text
    assert "Read the ballot from this path" in text
    assert "No preamble, acknowledgement, or explanation before the first vote" in text


def test_render_voter_archetype_lens_blocks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    validity = _render_voter_text(tmp_path, capsys, "--archetype", "validity-correctness")
    assert "full Review Acceptance Rubric" in validity
    assert "**is it real**" in validity
    plan = _render_voter_text(tmp_path, capsys, "--archetype", "plan-fidelity-completeness")
    assert "missing plan context is not an automatic NO" in plan
    assert "**is it in scope**" in plan
    assert "Plan-required deliverable omissions override default-test-to-OOS" in plan
    assert "k=3" not in plan
    assert "self-consistency" not in plan
    assert "plan-fidelity alone" not in plan
    pragmatic = _render_voter_text(tmp_path, capsys, "--archetype", "pragmatism-cost")
    assert "**is it worth it**" in pragmatic
    assert "Defer to validity on correctness and security" in pragmatic


def test_render_findings_view_filters_and_handles_missing_body(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review-findings-full.jsonl").write_text(
        '{"outcome":"accepted","round_num":1,"prose_body":"accepted body"}\n'
        '{"outcome":"rejected","round_num":2}\n'
        '{"outcome":"out_of_scope","round_num":3,"prose_body":"oos body"}\n'
        'not json\n',
        encoding="utf-8",
    )
    assert rendering.render_findings_view_main([str(run_dir), "all"]) == 0
    all_out = capsys.readouterr().out
    assert "### FINDING (accepted) round-1" in all_out
    assert "accepted body" in all_out
    assert "### FINDING (rejected) round-2" in all_out
    assert "(no prose body)" in all_out
    assert "### FINDING (out_of_scope) round-3" in all_out
    assert rendering.render_findings_view_main([str(run_dir), "oos"]) == 0
    oos_out = capsys.readouterr().out
    assert "out_of_scope" in oos_out
    assert "accepted body" not in oos_out


def test_render_findings_view_preserves_empty_prose_body(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review-findings-full.jsonl").write_text(
        '{"outcome":"accepted","round_num":1,"prose_body":""}\n',
        encoding="utf-8",
    )
    assert rendering.render_findings_view_main([str(run_dir), "all"]) == 0
    out = capsys.readouterr().out
    assert "### FINDING (accepted) round-1\n\n" in out
    assert "(no prose body)" not in out


def test_render_findings_view_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert rendering.render_findings_view_main([str(tmp_path), "all"]) == 1
    assert "not found" in capsys.readouterr().err
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review-findings-full.jsonl").write_text("", encoding="utf-8")
    assert rendering.render_findings_view_main([str(run_dir), "bad"]) == 1
    assert "unknown view" in capsys.readouterr().err


def test_render_voter_calibration_block_is_tool_specific(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stats = tmp_path / "stats.tsv"
    _write_voter_calibration_stats(
        path=stats,
        stats=[
            voting.VoterCalibrationStat(
                tool="codex",
                yes_votes=3,
                valid_yes_severity_count=2,
                major=2,
                minor=0,
                nit=0,
                missing_severity=1,
                high_rate=1.0,
                calibration_score=0.0,
                uncalibrated=True,
            ),
            voting.VoterCalibrationStat(
                tool="cursor",
                yes_votes=1,
                valid_yes_severity_count=1,
                major=0,
                minor=1,
                nit=0,
                missing_severity=0,
                high_rate=0.0,
                calibration_score=1.0,
                uncalibrated=False,
            ),
        ],
    )
    text = _render_voter_text(tmp_path, capsys, "--calibration-stats-file", str(stats), "--voter-tool", "codex")
    assert "**Your recent calibration:**" in text
    assert "100.0% major across 2 valid YES severities" in text
    assert "Reserve major for issues that match the severity rubric above" in text
    assert text.index("**Panel severity rubric:**") < text.index("**Your recent calibration:**")
    assert "body_severity" not in text


def test_render_voter_stats_without_tool_preserves_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stats = tmp_path / "stats.tsv"
    _write_voter_calibration_stats(
        path=stats,
        stats=[
            voting.VoterCalibrationStat(
                tool="codex",
                yes_votes=1,
                valid_yes_severity_count=1,
                major=1,
                minor=0,
                nit=0,
                missing_severity=0,
                high_rate=1.0,
                calibration_score=0.0,
                uncalibrated=True,
            )
        ],
    )
    assert _render_voter_text(tmp_path, capsys, "--calibration-stats-file", str(stats)) == _render_voter_text(tmp_path, capsys)


def test_render_voter_missing_stats_file_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    baseline = _render_voter_text(tmp_path, capsys)
    text = _render_voter_text(tmp_path, capsys, "--calibration-stats-file", str(tmp_path / "missing.tsv"))
    assert text == baseline


def test_render_voter_malformed_stats_omits_calibration_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stats = tmp_path / "bad.tsv"
    stats.write_text("not-a-valid-header\n", encoding="utf-8")
    text = _render_voter_text(tmp_path, capsys, "--calibration-stats-file", str(stats), "--voter-tool", "codex")
    assert "**Your recent calibration:**" not in text


def test_render_voter_no_matching_tool_omits_calibration_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stats = tmp_path / "stats.tsv"
    _write_voter_calibration_stats(
        path=stats,
        stats=[
            voting.VoterCalibrationStat(
                tool="codex",
                yes_votes=1,
                valid_yes_severity_count=1,
                major=1,
                minor=0,
                nit=0,
                missing_severity=0,
                high_rate=1.0,
                calibration_score=0.0,
                uncalibrated=True,
            )
        ],
    )
    text = _render_voter_text(tmp_path, capsys, "--calibration-stats-file", str(stats), "--voter-tool", "cursor")
    assert "**Your recent calibration:**" not in text


def test_render_specialist_payload_sidecar_counts_description_and_cache_hit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    cache_dir = tmp_path / "render-cache"
    monkeypatch.setenv("LARCH_RENDER_CACHE_DIR", str(cache_dir))
    agent = REPO_ROOT / "agents" / "reviewer-structure.md"
    sidecar = tmp_path / "payload.txt"
    args = [
        "--agent-file", str(agent),
        "--mode", "description",
        "--description-text", "payload description",
        "--scope-files", str(tmp_path / "scope.txt"),
        "--payload-bytes-output", str(sidecar),
    ]
    (tmp_path / "scope.txt").write_text("python/foo.py\n", encoding="utf-8")

    assert rendering.render_specialist_main(args) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(b'payload description')}\n"
    sidecar.write_text("stale\n", encoding="utf-8")
    assert rendering.render_specialist_main(args) == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(b'payload description')}\n"


def test_render_plan_review_payload_sidecar_counts_cursor_plan_and_feature(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    plan.write_text("PLAN PAYLOAD\n", encoding="utf-8")
    feature.write_text("FEATURE PAYLOAD\n", encoding="utf-8")
    sidecar = tmp_path / "payload.txt"

    rc = rendering.render_plan_review_main([
        "--archetype", "arch",
        "--vendor", "cursor",
        "--plan-file", str(plan),
        "--design-tmpdir", str(tmp_path),
        "--feature-file", str(feature),
        "--payload-bytes-output", str(sidecar),
    ])

    assert rc == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(plan.read_bytes()) + len(feature.read_bytes())}\n"


def test_render_plan_review_body_file_payload_sidecar_counts_body_feature_and_plan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_quiet(monkeypatch)
    _patch_architectural_guidelines(monkeypatch, "absent", "")
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    plan = design_tmpdir / "plan.txt"
    feature = design_tmpdir / "feature.txt"
    body = design_tmpdir / "body.txt"
    sidecar = tmp_path / "payload.txt"
    _ = plan.write_text("PLAN PAYLOAD\n", encoding="utf-8")
    _ = feature.write_text("FEATURE PAYLOAD\n", encoding="utf-8")
    _ = body.write_text("ROLE LINE\n", encoding="utf-8")

    rc = rendering.render_plan_review_main(
        [
            "--body-file",
            str(body),
            "--body-file-payload",
            "--archetype",
            "alpha",
            "--vendor",
            "cursor",
            "--plan-file",
            str(plan),
            "--design-tmpdir",
            str(design_tmpdir),
            "--feature-file",
            str(feature),
            "--payload-bytes-output",
            str(sidecar),
        ],
    )

    assert rc == 0
    _ = capsys.readouterr()
    assert sidecar.read_text(encoding="utf-8") == f"{len(body.read_bytes()) + len(feature.read_bytes()) + len(plan.read_bytes())}\n"


def test_render_voter_payload_sidecar_counts_scope_anchor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    anchor = tmp_path / "anchor.md"
    anchor.write_text("ANCHOR PAYLOAD\n", encoding="utf-8")
    sidecar = tmp_path / "payload.txt"

    _ = _render_voter_text(
        tmp_path,
        capsys,
        "--verification-context", "plan",
        "--scope-anchor-file", str(anchor),
        "--payload-bytes-output", str(sidecar),
    )

    assert sidecar.read_text(encoding="utf-8") == f"{len(anchor.read_bytes())}\n"


def test_rendering_helpers_extract_and_replace(tmp_path: Path) -> None:
    template = tmp_path / "template.md"
    _ = template.write_text(
        "## Reviewer: Demo\n"
        "<!-- BEGIN GENERATED_BODY -->\n"
        "```\n"
        "### In-Scope Findings\n"
        "- {OUTPUT_INSTRUCTION}\n"
        "### Out-of-Scope Observations\n"
        "- {OUTPUT_INSTRUCTION}\n"
        "```\n"
        "<!-- END GENERATED_BODY -->\n",
        encoding="utf-8",
    )
    body = helpers.extract_generated_body(template, heading="## Reviewer: Demo")
    replaced = helpers.replace_output_instruction(body, inscope=["keep this"], oos=["note that"])
    assert "### In-Scope Findings" in replaced
    assert "- keep this" in replaced
    assert "- note that" in replaced
    assert "{OUTPUT_INSTRUCTION}" not in replaced


def test_rendering_helpers_frontmatter_and_checksum(tmp_path: Path) -> None:
    path = tmp_path / "agent.md"
    _ = path.write_text("---\nname: demo\n---\nBody line\n", encoding="utf-8")
    assert helpers.frontmatter_body(path) == "Body line"
    digest = helpers.sha256_path(path)
    assert len(digest) == 64
    assert all(ch in "0123456789abcdef" for ch in digest)


def test_rendering_helper_imports_are_cycle_free() -> None:
    """Load helpers and their caller in fresh interpreters without eager cycles."""
    snippets = (
        "from larch.rendering import _rendering_helpers as h; "
        "assert h.RenderError is not None; print('helpers-ok')",
        "from larch.rendering import rendering as r; "
        "from larch.rendering import _rendering_helpers as h; "
        "assert r.RenderError is h.RenderError; print('rendering-ok')",
    )
    for snippet in snippets:
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(PYTHON_DIR)!r}); {snippet}"],
            capture_output=True,
            text=True,
            cwd=str(PYTHON_DIR),
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("-ok")
# pyright: reportArgumentType=false
