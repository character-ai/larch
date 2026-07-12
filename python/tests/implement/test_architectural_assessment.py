"""Tests for the Step 8 architectural assessment coordinator."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from larch.core import config, external_defaults
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
    parsed, invalid = assessment._parse_results_independently(json.dumps(payload), [invariant, guideline])  # pyright: ignore[reportPrivateUsage]
    assert [result.kind for result in parsed] == ["invariants"]
    assert set(invalid) == {"guidelines"}
    assert "identity mismatch" in invalid["guidelines"]


def test_prompt_evidence_paths_must_stay_under_granted_root(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    valid = "contract\n\nREQUESTS_JSON=" + json.dumps([
        {"diff_path": str(evidence_dir / "diff"), "knowledge_path": str(evidence_dir / "knowledge")}
    ])
    assessment._validate_prompt_evidence_paths(valid, evidence_dir=evidence_dir)  # pyright: ignore[reportPrivateUsage]
    escaped = valid.replace(str(evidence_dir / "diff"), str(tmp_path / "outside"))
    with pytest.raises(ValueError, match="outside"):
        assessment._validate_prompt_evidence_paths(escaped, evidence_dir=evidence_dir)  # pyright: ignore[reportPrivateUsage]


def test_shared_launcher_sidecars_fail_closed_when_missing_or_inconsistent(tmp_path: Path) -> None:
    output = tmp_path / "result.txt"
    _ = output.with_suffix(output.suffix + ".done").write_text("0\n", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".meta").write_text(
        f"TOOL=codex\nOUTPUT_FILE={output}\n",
        encoding="utf-8",
    )
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    _ = sidecar.write_text("status ok\n", encoding="utf-8")

    assert assessment._shared_launcher_artifact_error(  # pyright: ignore[reportPrivateUsage]
        output=output, tool="codex", launcher_exit=0
    ) == ""
    _ = output.with_suffix(output.suffix + ".done").write_text("7\n", encoding="utf-8")
    assert "inconsistent" in assessment._shared_launcher_artifact_error(  # pyright: ignore[reportPrivateUsage]
        output=output, tool="codex", launcher_exit=0
    )
    sidecar.unlink()
    assert "omitted" in assessment._shared_launcher_artifact_error(  # pyright: ignore[reportPrivateUsage]
        output=output, tool="codex", launcher_exit=0
    )


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
        assessment.AssessmentLane("claude", "claude-sonnet-4-6"),
        tmp_path,
        "prompt",
        tmp_path,
        tmp_path / "result.json",
    )
    result = assessment.DirectClaudeLauncher().launch(request)
    assert result.returncode == 0
    assert captured["argv"] == [
        "claude", "--print", "--model", "claude-sonnet-4-6", "--add-dir", str(tmp_path),
        "--allowedTools", "Read", "--permission-mode", "plan",
    ]
    assert captured["cwd"] == request.evidence_dir
    assert captured["input"] == "prompt"


class _SequenceLauncher:
    """Launcher stub returning a scripted result sequence, repeating the final entry."""

    def __init__(self, results: list[assessment.LaunchResult]) -> None:
        self._results = results
        self.calls = 0
        self.requests: list[assessment.LaunchRequest] = []

    def launch(self, request: assessment.LaunchRequest) -> assessment.LaunchResult:
        self.requests.append(request)
        self.calls += 1
        result = self._results[min(self.calls - 1, len(self._results) - 1)]
        if request.lane.tool == "cursor" and result.dirty_tree_path is None:
            dirty_path = request.output_path.with_suffix(request.output_path.suffix + ".dirty-tree")
            _ = dirty_path.write_text("STATUS=clean\n", encoding="utf-8")
            return assessment.LaunchResult(result.returncode, result.stdout, result.stderr, dirty_path)
        return result


def _payload(evidences: list[assessment.MaterializedEvidence], *, states: dict[str, str] | None = None) -> str:
    outcomes = states or {}
    rows: list[dict[str, object]] = []
    for evidence in evidences:
        state = outcomes.get(evidence.kind, "clean")
        rows.append({
            "kind": evidence.kind,
            "state": state,
            "assessment": "No violations identified." if state == "clean" else "G-Py-4 applies.",
            "identifiers": [] if state == "clean" else ["G-Py-4"],
            "head_sha": evidence.head_sha,
            "base_ref": evidence.base_ref,
            "diff_fingerprint": evidence.diff_fingerprint,
            "knowledge_sha256": evidence.knowledge_sha256,
        })
    return json.dumps({"schema_version": "1", "results": rows})


def _run_evidence(tmp_path: Path, kind: str = config.ASSESSMENT_KIND_GUIDELINES) -> assessment.MaterializedEvidence:
    diff = tmp_path / f"{kind}-diff.txt"
    knowledge = tmp_path / f"{kind}-knowledge.md"
    _ = diff.write_text("diff --git a/python/a.py b/python/a.py\n", encoding="utf-8")
    _ = knowledge.write_text("### G-Py-4: Fail loudly\n" if kind == "guidelines" else "### I-Stale-1: Reject stale inputs\n", encoding="utf-8")
    base = _evidence(kind)
    return assessment.MaterializedEvidence(
        kind, base.head_sha, base.base_ref, diff, diff.read_text(encoding="utf-8"),
        base.diff_fingerprint, knowledge, assessment._sha256(knowledge.read_text(encoding="utf-8")),  # pyright: ignore[reportPrivateUsage]
        base.identifiers,
    )


def _stub_materialization(monkeypatch: pytest.MonkeyPatch, evidence_by_kind: dict[str, assessment.MaterializedEvidence]) -> None:
    monkeypatch.setattr(assessment, "_git_read", lambda *_args: next(iter(evidence_by_kind.values())).head_sha)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_already_handled", lambda *_args, **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_discard_unavailable_coverage", lambda *_args, **_kwargs: None)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_materialize_current", lambda kind, **_kwargs: evidence_by_kind[kind])  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "deterministic_out_of_scope", lambda _diff: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]


def _ignore_persisted_result(
    _result: assessment.AssessmentResult,
    *,
    repo_root: Path,
    implement_tmpdir: Path,
) -> None:
    _ = (repo_root, implement_tmpdir)


def test_waterfall_advances_once_per_lane_and_stops_after_valid_codex_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {evidence.kind: evidence})
    persisted: list[str] = []
    monkeypatch.setattr(assessment, "_persist_result", lambda result, **_kwargs: persisted.append(result.kind))  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    cursor = _SequenceLauncher([assessment.LaunchResult(0, "", "empty primary")])
    codex = _SequenceLauncher([assessment.LaunchResult(0, _payload([evidence]), "")])
    claude = _SequenceLauncher([assessment.LaunchResult(0, _payload([evidence]), "")])

    result = assessment.run(
        kinds=[evidence.kind], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={"cursor": cursor, "codex": codex, "claude": claude},
        availability={"cursor": True, "codex": True, "claude": True},
    )

    assert result == ("guidelines:clean",)
    assert (cursor.calls, codex.calls, claude.calls) == (1, 1, 0)
    assert persisted == ["guidelines"]


def test_waterfall_attempts_each_available_lane_once_in_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {evidence.kind: evidence})
    monkeypatch.setattr(assessment, "_persist_result", _ignore_persisted_result)
    order: list[str] = []

    class _OrderedLauncher:
        def __init__(self, tool: str, result: assessment.LaunchResult) -> None:
            self.tool = tool
            self.result = result

        def launch(self, request: assessment.LaunchRequest) -> assessment.LaunchResult:
            order.append(request.lane.tool)
            if self.tool == "cursor":
                dirty = request.output_path.with_suffix(request.output_path.suffix + ".dirty-tree")
                _ = dirty.write_text("STATUS=clean\n", encoding="utf-8")
                return assessment.LaunchResult(self.result.returncode, self.result.stdout, self.result.stderr, dirty)
            return self.result

    result = assessment.run(
        kinds=[evidence.kind], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={
            "cursor": _OrderedLauncher("cursor", assessment.LaunchResult(0, "", "cursor empty")),
            "codex": _OrderedLauncher("codex", assessment.LaunchResult(9, "", "codex failed")),
            "claude": _OrderedLauncher("claude", assessment.LaunchResult(0, _payload([evidence]), "")),
        },
        availability={"cursor": True, "codex": True, "claude": True},
    )

    assert result == ("guidelines:clean",)
    assert order == ["cursor", "codex", "claude"]


def test_recorded_binary_availability_outranks_path_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _ = (tmp_path / "session-env.sh").write_text(
        "CURSOR_BINARY_FOUND=true\nCODEX_BINARY_FOUND=false\nCLAUDE_BINARY_FOUND=true\n",
        encoding="utf-8",
    )
    for key in (config.ENV_CURSOR_BINARY_FOUND, config.ENV_CODEX_BINARY_FOUND, config.ENV_CLAUDE_BINARY_FOUND):
        monkeypatch.delenv(key, raising=False)
    def fake_which(binary: str) -> str | None:
        return "/bin/tool" if binary == "codex" else None

    monkeypatch.setattr(external_defaults.shutil, "which", fake_which)

    assert assessment._lane_availability(tmp_path) == {  # pyright: ignore[reportPrivateUsage]
        "cursor": True,
        "codex": False,
        "claude": True,
    }

    monkeypatch.setenv(config.ENV_CURSOR_BINARY_FOUND, "false")
    assert assessment._lane_availability(tmp_path)["cursor"] is False  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("text", ["STATUS=dirty\n", "STATUS=unknown\n", "broken\n"])
def test_cursor_dirty_tree_sidecar_must_be_trusted_clean(tmp_path: Path, text: str) -> None:
    path = tmp_path / "cursor.dirty-tree"
    _ = path.write_text(text, encoding="utf-8")
    clean, _detail = assessment._cursor_dirty_tree_clean(path, implement_tmpdir=tmp_path)  # pyright: ignore[reportPrivateUsage]
    assert clean is False


def test_per_kind_success_removes_kind_from_later_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invariant = _run_evidence(tmp_path, config.ASSESSMENT_KIND_INVARIANTS)
    guideline = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {invariant.kind: invariant, guideline.kind: guideline})
    monkeypatch.setattr(assessment, "_persist_result", _ignore_persisted_result)
    cursor_payload = json.loads(_payload([invariant, guideline]))
    cursor_payload["results"][1]["diff_fingerprint"] = "wrong"
    cursor = _SequenceLauncher([assessment.LaunchResult(0, json.dumps(cursor_payload), "")])
    codex = _SequenceLauncher([assessment.LaunchResult(0, _payload([guideline]), "")])

    result = assessment.run(
        kinds=[invariant.kind, guideline.kind], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={"cursor": cursor, "codex": codex},
        availability={"cursor": True, "codex": True, "claude": False},
    )

    assert result == ("invariants:clean", "guidelines:clean")
    assert '"kind":"invariants"' not in codex.requests[0].prompt
    assert '"kind":"guidelines"' in codex.requests[0].prompt


def test_invalid_explicit_outcome_stays_reauthor_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {evidence.kind: evidence})
    payload = json.loads(_payload([evidence]))
    payload["results"][0]["state"] = "violation"
    cursor = _SequenceLauncher([assessment.LaunchResult(0, json.dumps(payload), "")])
    codex = _SequenceLauncher([assessment.LaunchResult(0, _payload([evidence]), "")])

    result = assessment.run(
        kinds=[evidence.kind], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={"cursor": cursor, "codex": codex},
        availability={"cursor": True, "codex": True, "claude": False},
    )

    assert result == ("guidelines:re-author-required:invalid-explicit-outcome",)
    assert (cursor.calls, codex.calls) == (1, 0)


def test_full_exhaustion_persists_last_lane_diagnostic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    evidence = _run_evidence(tmp_path)
    _stub_materialization(monkeypatch, {evidence.kind: evidence})
    launchers = {
        "cursor": _SequenceLauncher([assessment.LaunchResult(1, "", "cursor diagnostic")]),
        "codex": _SequenceLauncher([assessment.LaunchResult(2, "", "codex diagnostic")]),
        "claude": _SequenceLauncher([assessment.LaunchResult(3, "", "final Claude diagnostic")]),
    }

    result = assessment.run(
        kinds=[evidence.kind], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers=launchers,
        availability={"cursor": True, "codex": True, "claude": True},
    )

    outcome = json.loads(
        (tmp_path / assessment.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8")
    )
    assert result == ("guidelines:unavailable",)
    assert outcome["detail"] == "final Claude diagnostic"


def test_run_persists_sanitized_stderr_after_empty_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    diff = tmp_path / "diff.txt"
    knowledge = tmp_path / "guidelines.md"
    _ = diff.write_text("diff --git a/python/a.py b/python/a.py\n", encoding="utf-8")
    _ = knowledge.write_text("# G-Py-4\n", encoding="utf-8")
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
    monkeypatch.setattr(assessment, "_git_read", lambda *_args: evidence.head_sha)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_already_handled", lambda *_args, **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_discard_unavailable_coverage", lambda *_args, **_kwargs: None)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_materialize_current", lambda *_args, **_kwargs: evidence)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "deterministic_out_of_scope", lambda _diff: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]

    assert assessment.run(
        kinds=[config.ASSESSMENT_KIND_GUIDELINES], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={"cursor": launcher}, availability={"cursor": True, "codex": False, "claude": False},
    ) == ("guidelines:unavailable",)

    outcome_path = tmp_path / assessment.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert launcher.calls == 1
    assert outcome["detail"] == "auth failed <implement-tmpdir> <REDACTED-TOKEN>"


def test_run_persists_sanitized_stderr_after_nonzero_launcher_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    diff = tmp_path / "diff.txt"
    knowledge = tmp_path / "guidelines.md"
    _ = diff.write_text("diff --git a/python/a.py b/python/a.py\n", encoding="utf-8")
    _ = knowledge.write_text("# G-Py-4\n", encoding="utf-8")
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
    launcher = _SequenceLauncher([assessment.LaunchResult(1, "", f"launcher failed {tmp_path} {token}")])
    monkeypatch.setattr(assessment, "_git_read", lambda *_args: evidence.head_sha)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_already_handled", lambda *_args, **_kwargs: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_discard_unavailable_coverage", lambda *_args, **_kwargs: None)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "_materialize_current", lambda *_args, **_kwargs: evidence)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    monkeypatch.setattr(assessment, "deterministic_out_of_scope", lambda _diff: False)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]

    assert assessment.run(
        kinds=[config.ASSESSMENT_KIND_GUIDELINES], repo_root=tmp_path, implement_tmpdir=tmp_path,
        launchers={"cursor": launcher}, availability={"cursor": True, "codex": False, "claude": False},
    ) == ("guidelines:unavailable",)

    outcome_path = tmp_path / assessment.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert launcher.calls == 1
    assert outcome["detail"] == "launcher failed <implement-tmpdir> <REDACTED-TOKEN>"


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
