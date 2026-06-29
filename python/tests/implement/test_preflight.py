"""Tests for implement preflight Python port."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from larch.implement import preflight


def _write(handle: object, text: str) -> None:
    if hasattr(handle, "write"):
        _ = handle.write(text)  # type: ignore[attr-defined]


def _fake_completed(argv: list[str], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout="", stderr="")


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
        if argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[DESIGNED] Work", "body": "body"}))
            return _fake_completed(argv)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 12\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
            return _fake_completed(argv)
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "12", "--repo", "o/r", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    keys = [line.split("=", 1)[0] for line in out.splitlines() if "=" in line]
    assert keys == [
        "ADMISSION_RESULT",
        "RESUME",
        "TITLE",
        "BLOCK_PRESENT",
        "PLAN_PATH",
        "ISSUE_JSON_PATH",
        "BYPASS_COUNT",
    ]
    assert "ADMISSION_RESULT=pass" in out
    assert "RESUME=true" in out
    assert "BYPASS_COUNT=0" in out
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
        if argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Work", "body": "body"}))
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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[IMPLEMENTING] Title", "body": "Do the thing"}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[IMPLEMENTING] Title", "body": "Do the thing"}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text(
                "Illustrative example: rounds_completed: 0\n\n"
                "review_status: complete\n"
                "rounds_completed: 2\n"
                "diff_lines: 12\n",
                encoding="utf-8",
            )
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text(
                "review_status: complete\nrounds_completed: nope\ndiff_lines: 8\n",
                encoding="utf-8",
            )
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "malformed plan review metadata" in out
    assert "rounds_completed=nope" in out


def test_preflight_refuses_zero_review_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

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
        if argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[IMPLEMENTING] Foo", "body": ""}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[IMPLEMENTING] ", "body": ""}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "[DESIGNED]   ", "body": ""}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "Emergency body"}))
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\nMALFORMED=start-without-end\n")
            return _fake_completed(argv, 1)
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: panel-init-failed\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

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
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: panel-skipped\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--force", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "review_status=panel-skipped" in capsys.readouterr().out


def test_preflight_retries_gh_issue_view_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gh_calls = 0

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal gh_calls
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
            return _fake_completed(argv)
        if argv[:3] == ["gh", "issue", "view"]:
            gh_calls += 1
            if gh_calls == 1:
                return _fake_completed(argv, 1)
            _write(handle=stdout, text=json.dumps({"title": "Title", "body": "body"}))
            return _fake_completed(argv)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 8\n", encoding="utf-8")
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
            return _fake_completed(argv)
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    assert gh_calls == 2


def test_preflight_malformed_issue_json_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(handle=stdout, text="ADMISSION_RESULT=pass\n")
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(handle=stdout, text="{not json")
        elif "plan-block" in argv:
            _write(handle=stdout, text="BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "42", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "gh issue view failed" in out
    assert "PLAN_PATH=" not in out
