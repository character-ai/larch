"""Tests for the Step 8 architectural assessment coordinator."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from larch.core import config
from larch.implement import architectural_assessment as assessment


def _evidence(kind: str = config.ASSESSMENT_KIND_GUIDELINES) -> assessment.MaterializedEvidence:
    return assessment.MaterializedEvidence(
        kind=kind,
        head_sha="a" * 40,
        base_ref="origin/main",
        diff_path=Path("/tmp/diff"),
        diff_text="diff --git a/python/a.py b/python/a.py\n",
        diff_fingerprint="b" * 64,
        knowledge_path=Path("/tmp/knowledge"),
        knowledge_sha256="c" * 64,
        identifiers=frozenset({"G-Py-4"} if kind == config.ASSESSMENT_KIND_GUIDELINES else {"I-Stale-1"}),
    )


def test_normalize_kinds_deduplicates_and_orders() -> None:
    assert assessment.normalize_kinds(["guidelines", "invariants", "guidelines"]) == ("invariants", "guidelines")


@pytest.mark.parametrize("kinds", [[], ["other"]])
def test_normalize_kinds_rejects_invalid_requests(kinds: list[str]) -> None:
    with pytest.raises(ValueError, match=r"required|unsupported"):
        _ = assessment.normalize_kinds(kinds)


@pytest.mark.parametrize(
    ("diff_text", "expected"),
    [
        ("diff --git a/docs/a.md b/docs/a.md\n", True),
        ("diff --git a/larch-logs/run/a.txt b/larch-logs/run/a.txt\n", True),
        ("diff --git a/python/a.py b/python/a.py\n", False),
        ("diff --git a/docs/a.md b/docs/b.md\n", False),
        ("Binary files a/x and b/x differ\n", False),
        ("diff --git a/../x b/../x\n", False),
    ],
)
def test_deterministic_filter_is_conservative(diff_text: str, expected: bool) -> None:
    assert assessment.deterministic_out_of_scope(diff_text) is expected


def test_parse_combined_results_orders_and_validates_identity() -> None:
    invariant = _evidence(config.ASSESSMENT_KIND_INVARIANTS)
    guideline = _evidence()
    payload: dict[str, object] = {
        "schema_version": "1",
        "results": [
            {
                "kind": "guidelines",
                "state": "deviation",
                "assessment": "G-Py-4 applies.",
                "identifiers": ["G-Py-4"],
                "head_sha": guideline.head_sha,
                "base_ref": guideline.base_ref,
                "diff_fingerprint": guideline.diff_fingerprint,
                "knowledge_sha256": guideline.knowledge_sha256,
            },
            {
                "kind": "invariants",
                "state": "clean",
                "assessment": "No violations identified.",
                "identifiers": [],
                "head_sha": invariant.head_sha,
                "base_ref": invariant.base_ref,
                "diff_fingerprint": invariant.diff_fingerprint,
                "knowledge_sha256": invariant.knowledge_sha256,
            },
        ],
    }
    parsed = assessment._parse_results(json.dumps(payload), [guideline, invariant])  # pyright: ignore[reportPrivateUsage]
    assert [row.kind for row in parsed] == ["invariants", "guidelines"]


def test_parse_results_rejects_extra_prose_and_unknown_identifier() -> None:
    evidence = _evidence()
    payload = {
        "schema_version": "1",
        "results": [{
            "kind": "guidelines", "state": "clean", "assessment": "Clean.",
            "identifiers": ["G-Unknown-1"], "head_sha": evidence.head_sha,
            "base_ref": evidence.base_ref, "diff_fingerprint": evidence.diff_fingerprint,
            "knowledge_sha256": evidence.knowledge_sha256,
        }],
    }
    with pytest.raises(ValueError, match="exactly one JSON object"):
        _ = assessment._parse_results(json.dumps(payload) + " trailing", [evidence])  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="unknown architectural identifier"):
        _ = assessment._parse_results(json.dumps(payload), [evidence])  # pyright: ignore[reportPrivateUsage]


def test_parse_results_independently_preserves_valid_rows() -> None:
    invariant = _evidence(config.ASSESSMENT_KIND_INVARIANTS)
    guideline = _evidence()
    payload: dict[str, object] = {  # type: ignore[reportUnknownVariableType]
        "schema_version": "1",
        "results": [
            {
                "kind": "invariants", "state": "clean", "assessment": "Clean.", "identifiers": [],
                "head_sha": invariant.head_sha, "base_ref": invariant.base_ref,
                "diff_fingerprint": invariant.diff_fingerprint, "knowledge_sha256": invariant.knowledge_sha256,
            },
            {
                "kind": "guidelines", "state": "deviation", "assessment": "Missing identity.", "identifiers": [],
                "head_sha": guideline.head_sha, "base_ref": guideline.base_ref,
                "diff_fingerprint": "wrong", "knowledge_sha256": guideline.knowledge_sha256,
            },
        ],
    }
    parsed, invalid, detail = assessment._parse_results_independently(json.dumps(payload), [invariant, guideline])  # pyright: ignore[reportPrivateUsage]
    assert [result.kind for result in parsed] == ["invariants"]
    assert invalid == {"guidelines"}
    assert "identity mismatch" in detail


def test_main_usage_and_success_stdout_contract(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert assessment.main([]) == config.EXIT_USAGE
    assert capsys.readouterr().out.splitlines() == [
        "ARCHITECTURAL_ASSESSMENT_STATUS=usage-error",
        "ARCHITECTURAL_ASSESSMENT_DETAIL=at least one --kind is required",
    ]

    monkeypatch.setattr(assessment, "run", lambda **_kwargs: ("guidelines:clean",))  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    assert assessment.main(["--kind", "guidelines", "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path)]) == config.EXIT_OK
    assert capsys.readouterr().out.splitlines() == [
        "ARCHITECTURAL_ASSESSMENT_STATUS=ok",
        "ARCHITECTURAL_ASSESSMENT_RESULTS=guidelines:clean",
    ]


def test_main_preserves_bounded_reauthor_reason(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr(
        assessment,
        "run",
        lambda **_kwargs: ("guidelines:re-author-required:clean-outcome-prose-mismatch",),  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    )

    assert assessment.main(["--kind", "guidelines", "--repo-root", str(tmp_path), "--implement-tmpdir", str(tmp_path)]) == config.EXIT_OK
    assert capsys.readouterr().out.splitlines() == [
        "ARCHITECTURAL_ASSESSMENT_STATUS=re-author-required",
        "ARCHITECTURAL_ASSESSMENT_RESULTS=guidelines:re-author-required:clean-outcome-prose-mismatch",
    ]


def test_sanitize_detail_main_reads_stdin_and_emits_one_safe_line(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    token = "ghp_" + "x" * 30
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"first\n{tmp_path}\t{token}"))

    rc = assessment.sanitize_detail_main(["--implement-tmpdir", str(tmp_path)])  # pyright: ignore[reportAttributeAccessIssue]

    output = capsys.readouterr().out
    assert rc == config.EXIT_OK
    assert output.count("\n") == 1
    assert str(tmp_path) not in output
    assert token not in output
    assert output == "first <implement-tmpdir> <REDACTED-TOKEN>\n"


def test_sanitize_detail_main_caps_stdin_before_sanitizing(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    class _RecordingBuffer:
        def __init__(self) -> None:
            self.size: int | None = None

        def read(self, size: int) -> bytes:
            self.size = size
            return b"bounded diagnostic"

    class _Stdin:
        def __init__(self) -> None:
            self.buffer = _RecordingBuffer()

    stdin = _Stdin()
    monkeypatch.setattr(sys, "stdin", stdin)

    assert assessment.sanitize_detail_main(["--implement-tmpdir", str(tmp_path)]) == config.EXIT_OK  # pyright: ignore[reportAttributeAccessIssue]
    assert stdin.buffer.size == assessment._MAX_SANITIZE_DETAIL_BYTES  # pyright: ignore[reportAttributeAccessIssue, reportPrivateUsage]
    assert capsys.readouterr().out == "bounded diagnostic\n"


@pytest.mark.parametrize("kind", [config.ASSESSMENT_KIND_INVARIANTS, config.ASSESSMENT_KIND_GUIDELINES])
def test_persist_unavailable_reuses_sanitized_detail_in_receipt_and_outcome(tmp_path: Path, kind: str) -> None:
    token = "ghp_" + "x" * 30
    diagnostic = f"launcher failed\n{tmp_path}\t{token} " + "z" * 600

    assessment._persist_unavailable(  # pyright: ignore[reportPrivateUsage]
        _evidence(kind), repo_root=tmp_path, implement_tmpdir=tmp_path, detail=diagnostic
    )

    receipt = json.loads((tmp_path / f"architectural-assessment-unavailable-{kind}.json").read_text(encoding="utf-8"))
    outcome_name = (
        assessment.architectural_guidelines.INVARIANT_SHIP_OUTCOME_SIDECAR
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else assessment.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    )
    outcome = json.loads((tmp_path / outcome_name).read_text(encoding="utf-8"))
    assert receipt["detail"] == outcome["detail"]
    assert len(receipt["detail"]) == 500
    assert "\n" not in receipt["detail"]
    assert str(tmp_path) not in receipt["detail"]
    assert token not in receipt["detail"]


def test_launcher_uses_exact_read_only_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> object:
        captured["argv"] = argv
        captured.update(kwargs)
        return type("Completed", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()

    monkeypatch.setattr(assessment.subprocess, "run", fake_run)
    request = assessment.LaunchRequest(
        argv=("claude", "--print", "--model", "claude-sonnet-4-6", "--add-dir", str(tmp_path), "--allowedTools", "Read", "--permission-mode", "plan"),
        cwd=tmp_path,
        prompt="prompt",
        evidence_dir=tmp_path,
    )
    result = assessment.ClaudeLauncher().launch(request)
    assert result.returncode == 0
    assert captured["argv"] == list(request.argv)
    assert captured["cwd"] == tmp_path
    assert captured["input"] == "prompt"


class _SequenceLauncher:
    """Launcher stub returning a scripted result sequence, repeating the final entry."""

    def __init__(self, results: list[assessment.LaunchResult]) -> None:
        self._results = results
        self.calls = 0

    def launch(self, request: assessment.LaunchRequest) -> assessment.LaunchResult:
        assert request.argv
        self.calls += 1
        return self._results[min(self.calls - 1, len(self._results) - 1)]


def _launch_request(tmp_path: Path) -> assessment.LaunchRequest:
    return assessment.LaunchRequest(argv=("claude",), cwd=tmp_path, prompt="p", evidence_dir=tmp_path)


def test_launch_assessment_returns_first_nonempty_result(tmp_path: Path) -> None:
    launcher = _SequenceLauncher([assessment.LaunchResult(0, '{"schema_version":"1"}', "")])
    result = assessment._launch_assessment(launcher, _launch_request(tmp_path))  # pyright: ignore[reportPrivateUsage]
    assert launcher.calls == 1
    assert result.stdout == '{"schema_version":"1"}'


def test_launch_assessment_retries_transient_empty_stdout(tmp_path: Path) -> None:
    launcher = _SequenceLauncher([
        assessment.LaunchResult(0, "", ""),
        assessment.LaunchResult(0, "  \n", ""),
        assessment.LaunchResult(0, '{"schema_version":"1"}', ""),
    ])
    result = assessment._launch_assessment(launcher, _launch_request(tmp_path))  # pyright: ignore[reportPrivateUsage]
    assert launcher.calls == 3
    assert result.stdout == '{"schema_version":"1"}'


def test_launch_assessment_caps_empty_stdout_retries(tmp_path: Path) -> None:
    launcher = _SequenceLauncher([assessment.LaunchResult(0, "", "")])
    result = assessment._launch_assessment(launcher, _launch_request(tmp_path))  # pyright: ignore[reportPrivateUsage]
    assert launcher.calls == assessment._EMPTY_STDOUT_ATTEMPTS  # pyright: ignore[reportPrivateUsage]
    assert result.stdout == ""


def test_launch_assessment_does_not_retry_nonzero_exit(tmp_path: Path) -> None:
    launcher = _SequenceLauncher([assessment.LaunchResult(1, "", "boom")])
    result = assessment._launch_assessment(launcher, _launch_request(tmp_path))  # pyright: ignore[reportPrivateUsage]
    assert launcher.calls == 1
    assert result.returncode == 1


def test_run_persists_sanitized_stderr_after_empty_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    diff = tmp_path / "diff.txt"
    knowledge = tmp_path / "guidelines.md"
    diff.write_text("diff --git a/python/a.py b/python/a.py\n", encoding="utf-8")
    knowledge.write_text("# G-Py-4\n", encoding="utf-8")
    evidence = assessment.MaterializedEvidence(
        kind=config.ASSESSMENT_KIND_GUIDELINES,
        head_sha="a" * 40,
        base_ref="origin/main",
        diff_path=diff,
        diff_text=diff.read_text(encoding="utf-8"),
        diff_fingerprint="b" * 64,
        knowledge_path=knowledge,
        knowledge_sha256=assessment._sha256(knowledge.read_text(encoding="utf-8")),  # pyright: ignore[reportPrivateUsage]
        identifiers=frozenset({"G-Py-4"}),
    )
    token = "ghp_" + "x" * 30
    launcher = _SequenceLauncher([assessment.LaunchResult(0, "", f"auth failed {tmp_path} {token}")])
    monkeypatch.setattr(assessment, "_git_read", lambda *_args: evidence.head_sha)
    monkeypatch.setattr(assessment, "_already_handled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(assessment, "_discard_unavailable_coverage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(assessment, "_materialize_current", lambda *_args, **_kwargs: evidence)
    monkeypatch.setattr(assessment, "deterministic_out_of_scope", lambda _diff: False)

    assert assessment.run(
        kinds=[config.ASSESSMENT_KIND_GUIDELINES], repo_root=tmp_path, implement_tmpdir=tmp_path, launcher=launcher
    ) == ("guidelines:unavailable",)

    outcome_path = tmp_path / assessment.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert launcher.calls == assessment._EMPTY_STDOUT_ATTEMPTS  # pyright: ignore[reportPrivateUsage]
    assert outcome["detail"] == "auth failed <implement-tmpdir> <REDACTED-TOKEN>"


def _true_kwargs(**_kwargs: object) -> bool:
    return True


def _true_args(*_args: object, **_kwargs: object) -> bool:
    return True


def test_already_handled_refuses_unavailable_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _unavailable_meta(_tmpdir: Path) -> dict[str, str]:
        return {"BASE_REF": "origin/main", "NOTE_STATE": config.NOTE_STATE_UNAVAILABLE}

    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _unavailable_meta)
    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_note_consumable", _true_kwargs)
    monkeypatch.setattr(assessment, "_outcome_valid", _true_args)
    handled = assessment._already_handled(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_INVARIANTS, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert handled is False


def test_already_handled_accepts_valid_authored_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _authored_meta(_tmpdir: Path) -> dict[str, str]:
        return {
            "BASE_REF": "origin/main",
            "NOTE_STATE": config.NOTE_STATE_AUTHORED,
            "ASSESSMENT_KIND": config.ASSESSMENT_OUTCOME_CLEAN,
        }

    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _authored_meta)
    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_note_consumable", _true_kwargs)
    monkeypatch.setattr(assessment, "_authored_note_valid", _true_args)
    monkeypatch.setattr(assessment, "_outcome_valid", _true_args)
    handled = assessment._already_handled(  # pyright: ignore[reportPrivateUsage]
        config.ASSESSMENT_KIND_INVARIANTS, repo_root=tmp_path, implement_tmpdir=tmp_path, head_sha="a" * 40
    )
    assert handled is True


def test_discard_unavailable_coverage_invalidates_only_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []

    def _fake_invalidate(tmpdir: Path) -> None:
        invalidated.append(tmpdir)

    def _meta(state: str) -> object:
        def _read(_tmpdir: Path) -> dict[str, str]:
            return {"NOTE_STATE": state}
        return _read

    monkeypatch.setattr(assessment.architectural_guidelines, "invalidate_invariant_implement_note", _fake_invalidate)

    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _meta(config.NOTE_STATE_UNAVAILABLE))
    assessment._discard_unavailable_coverage(config.ASSESSMENT_KIND_INVARIANTS, implement_tmpdir=tmp_path)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]

    invalidated.clear()
    monkeypatch.setattr(assessment.architectural_guidelines, "invariant_durable_note_metadata", _meta(config.NOTE_STATE_AUTHORED))
    assessment._discard_unavailable_coverage(config.ASSESSMENT_KIND_INVARIANTS, implement_tmpdir=tmp_path)  # pyright: ignore[reportPrivateUsage]
    assert not invalidated


def test_discard_unavailable_coverage_uses_guideline_invalidator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalidated: list[Path] = []

    def _fake_invalidate(tmpdir: Path) -> None:
        invalidated.append(tmpdir)

    def _unavailable_meta(_tmpdir: Path) -> dict[str, str]:
        return {"NOTE_STATE": config.NOTE_STATE_UNAVAILABLE}

    monkeypatch.setattr(assessment.architectural_guidelines, "durable_note_metadata", _unavailable_meta)
    monkeypatch.setattr(assessment.architectural_guidelines, "invalidate_implement_note", _fake_invalidate)
    assessment._discard_unavailable_coverage(config.ASSESSMENT_KIND_GUIDELINES, implement_tmpdir=tmp_path)  # pyright: ignore[reportPrivateUsage]
    assert invalidated == [tmp_path]
