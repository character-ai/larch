"""Tests for implement preflight Python port."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

import preflight


def _write(handle: object, text: str) -> None:
    if hasattr(handle, "write"):
        _ = handle.write(text)  # type: ignore[attr-defined]


def _fake_completed(argv: list[str], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout="", stderr="")


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
            _write(stdout, "ADMISSION_RESULT=pass\nRESUME=true\nTITLE=[DESIGNED] Work\n")
            return _fake_completed(argv)
        if argv[:3] == ["gh", "issue", "view"]:
            _write(stdout, json.dumps({"title": "[DESIGNED] Work", "body": "body"}))
            return _fake_completed(argv)
        if "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 2\ndiff_lines: 12\n", encoding="utf-8")
            _write(stdout, "BLOCK_PRESENT=true\n")
            return _fake_completed(argv)
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "12", "--repo", "o/r", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ADMISSION_RESULT=pass" in out
    assert "RESUME=true" in out
    assert "BYPASS_COUNT=0" in out
    assert any(call[-2:] == ["--repo", "o/r"] for call in calls if "admission" in call)
    assert any(call[-2:] == ["--repo", "o/r"] for call in calls if "plan-block" in call)


def test_preflight_emergency_missing_plan_uses_raw_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(stdout, "ADMISSION_RESULT=pass\n")
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(stdout, json.dumps({"title": "[IMPLEMENTING] Title", "body": "Do the thing"}))
        elif "plan-block" in argv:
            _write(stdout, "BLOCK_PRESENT=false\n")
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--emergency", "--preflight-tmpdir", str(tmp_path)])
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
            _write(stdout, "ADMISSION_RESULT=managed-prefix\nTITLE=bad\n")
            return _fake_completed(argv, 1)
        raise AssertionError("unexpected call")

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "ADMISSION_RESULT=managed-prefix" in capsys.readouterr().out


def test_preflight_refuses_zero_review_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "admission" in argv:
            _write(stdout, "ADMISSION_RESULT=pass\n")
        elif argv[:3] == ["gh", "issue", "view"]:
            _write(stdout, json.dumps({"title": "Title", "body": "body"}))
        elif "plan-block" in argv:
            out_path = Path(argv[argv.index("--output") + 1])
            out_path.write_text("review_status: complete\nrounds_completed: 0\ndiff_lines: 8\n", encoding="utf-8")
            _write(stdout, "BLOCK_PRESENT=true\n")
        return _fake_completed(argv)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    rc = preflight.preflight_main(["--issue", "5", "--preflight-tmpdir", str(tmp_path)])
    assert rc == 2
    assert "rounds_completed=0" in capsys.readouterr().out
