"""Tests for implement preflight Python port."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from larch.core.proc import CommandResult
from larch.implement import preflight
from larch.design import plan_grammar


def _write(handle: object, text: str) -> None:
    if hasattr(handle, "write"):
        _ = handle.write(text)  # type: ignore[attr-defined]


def test_read_kv_lines_uses_last_duplicate_value() -> None:
    assert preflight._read_kv_lines("ADMISSION_RESULT=old\nADMISSION_RESULT=latest\n") == {  # pyright: ignore[reportPrivateUsage]
        "ADMISSION_RESULT": "latest"
    }


def _fake_completed(argv: list[str], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout="", stderr="")


def _stub_issue_view(
    monkeypatch: pytest.MonkeyPatch,
    *,
    payload: dict[str, Any] | str,
    returncode: int = 0,
    stderr: str = "",
) -> list[list[str]]:
    """Stub wrapper-backed issue view through the proc runner seam."""
    calls: list[list[str]] = []
    stdout = payload if isinstance(payload, str) else json.dumps(payload)

    def fake_proc_run(argv: list[str] | tuple[str, ...], **_kwargs: Any) -> CommandResult:
        argv_list = list(argv)
        calls.append(argv_list)
        if argv_list[:3] == ["gh", "issue", "view"]:  # lint-gh-argv-literal: ok fixture assertion
            return CommandResult(tuple(argv_list), returncode, stdout, stderr, 0.01)
        return CommandResult(tuple(argv_list), 0, "", "", 0.01)

    monkeypatch.setattr(preflight.proc, "run", fake_proc_run)
    return calls


def _valid_success_rows(tmp_path: Path) -> list[tuple[str, str]]:
    plan = tmp_path / "plan-from-issue.txt"
    issue_json = tmp_path / "issue.json"
    plan.write_text("plan\n", encoding="utf-8")
    issue_json.write_text('{"title":"Title"}\n', encoding="utf-8")
    return [
        ("ADMISSION_RESULT", "pass"),
        ("RESUME", "false"),
        ("TITLE", "Title"),
        ("BLOCK_PRESENT", "true"),
        ("PLAN_PATH", str(plan)),
        ("ISSUE_JSON_PATH", str(issue_json)),
        ("BYPASS_COUNT", "0"),
        ("DESIGN_DIFFICULTY", ""),
        ("MAIN_CI_STATUS", "pass"),
        ("MAIN_FAILED_RUN_ID", ""),
        ("MAIN_HEALTH_HEAD_SHA", "abc123"),
        ("MAIN_HEALTH_DETAIL", "ok"),
    ]


def _duplicate_resume(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [*rows, ("RESUME", "false")]


def _missing_title(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [row for row in rows if row[0] != "TITLE"]


def _invalid_resume(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, "empty" if key == "RESUME" else value) for key, value in rows]


def _multiline_title(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, "Bad\nTitle" if key == "TITLE" else value) for key, value in rows]


def _wrong_plan_path(rows: list[tuple[str, str]], tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, str(tmp_path / "wrong-plan.txt") if key == "PLAN_PATH" else value) for key, value in rows]


def _wrong_issue_json_path(rows: list[tuple[str, str]], tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, str(tmp_path / "wrong-issue.json") if key == "ISSUE_JSON_PATH" else value) for key, value in rows]


def _missing_plan_path(rows: list[tuple[str, str]], tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, str(tmp_path / "missing-plan.txt") if key == "PLAN_PATH" else value) for key, value in rows]


def _nonnumeric_bypass_count(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, "NaN" if key == "BYPASS_COUNT" else value) for key, value in rows]


def _invalid_main_ci_status(rows: list[tuple[str, str]], _tmp_path: Path) -> list[tuple[str, str]]:
    return [(key, "unknown" if key == "MAIN_CI_STATUS" else value) for key, value in rows]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_duplicate_resume, "duplicate key RESUME"),
        (_missing_title, "missing key TITLE"),
        (_invalid_resume, "RESUME must be true or false"),
        (_multiline_title, "TITLE must be single-line"),
        (_wrong_plan_path, "PLAN_PATH must match preflight tmpdir"),
        (_wrong_issue_json_path, "ISSUE_JSON_PATH must match preflight tmpdir"),
        (_missing_plan_path, "PLAN_PATH must match preflight tmpdir"),
        (_nonnumeric_bypass_count, "BYPASS_COUNT must be numeric"),
        (_invalid_main_ci_status, "MAIN_CI_STATUS must be pass, fail, pending, error, or skip"),
    ],
)
def test_validate_success_envelope_rejects_malformed_rows(
    tmp_path: Path,
    mutate: Any,
    expected: str,
) -> None:
    rows = mutate(_valid_success_rows(tmp_path), tmp_path)
    error = preflight._validate_success_envelope(  # pyright: ignore[reportPrivateUsage]
        rows,
        preflight_tmpdir=tmp_path,
        plan_path=tmp_path / "plan-from-issue.txt",
        issue_json_path=tmp_path / "issue.json",
    )
    assert error == expected


def test_validate_success_envelope_rejects_absent_referenced_file(tmp_path: Path) -> None:
    rows = _valid_success_rows(tmp_path)
    (tmp_path / "plan-from-issue.txt").unlink()
    error = preflight._validate_success_envelope(  # pyright: ignore[reportPrivateUsage]
        rows,
        preflight_tmpdir=tmp_path,
        plan_path=tmp_path / "plan-from-issue.txt",
        issue_json_path=tmp_path / "issue.json",
    )
    assert error == "PLAN_PATH must be readable"


def test_validate_success_envelope_accepts_main_ci_skip(tmp_path: Path) -> None:
    rows = [
        (key, "skip" if key == "MAIN_CI_STATUS" else value)
        for key, value in _valid_success_rows(tmp_path)
    ]

    error = preflight._validate_success_envelope(  # pyright: ignore[reportPrivateUsage]
        rows,
        preflight_tmpdir=tmp_path,
        plan_path=tmp_path / "plan-from-issue.txt",
        issue_json_path=tmp_path / "issue.json",
    )

    assert error == ""


def test_preflight_success_emits_kv_and_forwards_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\nRESUME=true\nTITLE=[DESIGNED] Work\n")
            return _fake_completed(argv)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndifficulty: MODERATE\ndiff_lines: 12\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
            return _fake_completed(argv)
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[DESIGNED] Work", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "12", "--repo", "o/r", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    keys = [line.split("=", 1)[0] for line in out.splitlines() if "=" in line]
    assert keys == list(preflight.SUCCESS_ENVELOPE_KEYS)
    assert "ADMISSION_RESULT=pass" in out
    assert "RESUME=true" in out
    assert "BYPASS_COUNT=0" in out
    assert "MAIN_CI_STATUS=error" in out
    assert (tmp_path / "main-health.env").is_file()
    assert (tmp_path / "issue.json").read_text(encoding="utf-8") == '{"title": "[DESIGNED] Work", "body": "body"}'
    assert (tmp_path / "gh-issue-view.stderr").read_text(encoding="utf-8") == ""
    assert any(call[-2:] == ["--repo", "o/r"] for call in calls if "admission" in call)
    assert any(call[-2:] == ["--repo", "o/r"] for call in calls if "plan-block" in call)


def test_preflight_success_envelope_validation_failure_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\nRESUME=true\n")
            return _fake_completed(argv)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 12\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
            return _fake_completed(argv)
        return _fake_completed(argv)

    original_rows = preflight._success_envelope_rows  # pyright: ignore[reportPrivateUsage]

    def malformed_rows(values: dict[str, str]) -> list[tuple[str, str]]:
        rows = original_rows(values)
        return [(key, "empty" if key == "RESUME" else value) for key, value in rows]

    _stub_issue_view(monkeypatch, payload={"title": "Work", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    monkeypatch.setattr(preflight, "_success_envelope_rows", malformed_rows)  # pyright: ignore[reportPrivateUsage]
    rc = preflight.preflight_main(["--issue", "12", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "malformed success envelope" in out
    assert "PLAN_PATH=" not in out


def test_preflight_force_missing_plan_uses_raw_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[IMPLEMENTING] Title", "body": "Do the thing"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "plan-from-issue.txt").read_text(encoding="utf-8") == "Do the thing"
    out = capsys.readouterr().out
    assert "raw issue body" in out
    assert "BYPASS_COUNT=1" in out


def test_preflight_force_short_flag_missing_plan_uses_raw_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[IMPLEMENTING] Title", "body": "Do the thing"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "-f", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "plan-from-issue.txt").read_text(encoding="utf-8") == "Do the thing"
    out = capsys.readouterr().out
    assert "raw issue body" in out
    assert "BYPASS_COUNT=1" in out


def test_preflight_refuses_admission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=managed-prefix\nTITLE=bad\n")
            return _fake_completed(argv, 1)
        raise AssertionError("unexpected call")

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "ADMISSION_RESULT=managed-prefix" in capsys.readouterr().out


def test_preflight_allows_footer_rounds_completed_despite_body_prose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text(
                "Illustrative example: rounds_completed: 0\n\n"
                "review_status: complete\n"
                "rounds_completed: 2\n"
                "oversize_override: operator\n"
                "diff_lines: 12\n",
                encoding="utf-8",
            )
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert "rounds_completed=0" not in capsys.readouterr().out


def test_preflight_refuses_malformed_rounds_completed_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text(
                "review_status: complete\nrounds_completed: nope\ndiff_lines: 8\n",
                encoding="utf-8",
            )
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "malformed plan review metadata" in out
    assert "rounds_completed=nope" in out


def test_malformed_terminal_metadata_direct_cases(tmp_path: Path) -> None:
    valid = tmp_path / "valid.txt"
    valid.write_text(
        "\n".join(
            plan_grammar.compose_trailer_lines(
                {
                    "review_status": "complete",
                    "rounds_completed": 2,
                    "difficulty": "MODERATE",
                    "diff_added": 1,
                    "diff_deleted": 0,
                    "mechanical_churn": False,
                    "oversize_override": "operator",
                    "diff_lines": 12,
                }
            )
        )
        + "\n",
        encoding="utf-8",
    )
    assert preflight._malformed_terminal_metadata(plan_path=valid) == ""

    malformed = tmp_path / "malformed.txt"
    malformed.write_text(
        "review_status: complete\ndifficulty: EASY\ndiff_lines: 8\n",
        encoding="utf-8",
    )
    assert preflight._malformed_terminal_metadata(plan_path=malformed) == "difficulty: EASY"

    unrecognized = tmp_path / "unrecognized.txt"
    unrecognized.write_text(
        "review_status: complete\nconfidence: high\ndifficulty: HARD\ndiff_lines: 8\n",
        encoding="utf-8",
    )
    assert preflight._malformed_terminal_metadata(plan_path=unrecognized) == ""

    non_terminal = tmp_path / "non-terminal.txt"
    non_terminal.write_text(
        "review_status: complete\ndiff_lines: 8\nmore body\n",
        encoding="utf-8",
    )
    assert preflight._malformed_terminal_metadata(plan_path=non_terminal) == ""


def test_recognized_trailer_prefix_regex_covers_every_trailer_key() -> None:
    for key in plan_grammar.TRAILER_KEYS:
        assert preflight._RECOGNIZED_TRAILER_PREFIX_RE.match(f"{key}: value") is not None
    assert preflight._RECOGNIZED_TRAILER_PREFIX_RE.match("confidence: high") is None
    assert preflight._RECOGNIZED_TRAILER_PREFIX_RE.match("not_a_trailer: x") is None


def test_preflight_refuses_zero_review_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "rounds_completed=0" in capsys.readouterr().out


def test_preflight_force_missing_designed_prefix_bypass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=missing-designed-prefix\nTITLE=Needs design\n")
            return _fake_completed(argv, 5)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "BYPASS_COUNT=1" in out
    assert "missing [DESIGNED] prefix" in out


def test_preflight_refuses_malformed_plan_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "MALFORMED=start-without-end" in capsys.readouterr().out


def test_preflight_force_empty_body_uses_stripped_title(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[IMPLEMENTING] Foo", "body": ""})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "plan-from-issue.txt").read_text(encoding="utf-8") == "Foo"
    out = capsys.readouterr().out
    assert "using the issue title" in out
    assert "BYPASS_COUNT=1" in out


def test_preflight_force_empty_title_aborts_without_plan_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[IMPLEMENTING] ", "body": ""})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    try:
        preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
        rc = 0
    except SystemExit as exc:
        rc = int(exc.code or 0)
    assert rc == 2
    assert not (tmp_path / "plan-from-issue.txt").exists()
    assert "issue title is empty" in capsys.readouterr().out


def test_preflight_force_malformed_plan_empty_title_aborts_without_plan_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "[DESIGNED]   ", "body": ""})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    try:
        preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
        rc = 0
    except SystemExit as exc:
        rc = int(exc.code or 0)
    assert rc == 2
    assert not (tmp_path / "plan-from-issue.txt").exists()
    assert "issue title is empty" in capsys.readouterr().out


def test_preflight_force_malformed_plan_uses_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "Emergency body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "plan-from-issue.txt").read_text(encoding="utf-8") == "Emergency body"
    out = capsys.readouterr().out
    assert "BYPASS_COUNT=1" in out
    assert "malformed larch:plan block" in out


def test_preflight_refuses_panel_init_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: panel-init-failed\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "review_status=panel-init-failed" in capsys.readouterr().out


def test_preflight_refuses_panel_skipped_even_in_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: panel-skipped\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload={"title": "Title", "body": "body"})
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "review_status=panel-skipped" in capsys.readouterr().out



def test_preflight_malformed_issue_json_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    _stub_issue_view(monkeypatch, payload="{not json")
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "gh issue view failed" in out
    assert "PLAN_PATH=" not in out


def test_preflight_issue_view_failure_preserves_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "admission" in argv:
            _write(handle=kwargs.get("stdout"), text="ADMISSION_RESULT=pass\n")
        return _fake_completed(argv)

    _stub_issue_view(
        monkeypatch,
        payload='{"message":"not found"}',
        returncode=1,
        stderr="gh issue view failed\n",
    )
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    assert preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)]) == 2
    assert (tmp_path / "issue.json").read_text(encoding="utf-8") == '{"message":"not found"}'
    assert (tmp_path / "gh-issue-view.stderr").read_text(encoding="utf-8") == "gh issue view failed\n"
    assert "gh issue view failed for issue #42" in capsys.readouterr().out
