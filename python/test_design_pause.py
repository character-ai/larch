"""Tests for /design pause save/load port."""

from __future__ import annotations

import subprocess
from pathlib import Path

import design_pause


def test_pause_save_rejects_invalid_issue(tmp_path: Path, capsys: object) -> None:
    rc = design_pause.pause_save_main(["--design-tmpdir", str(tmp_path), "--issue", "bad"])
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "PAUSE_OK=false" in out
    assert "ERROR=invalid-issue" in out


def test_pause_load_no_pause_marker(tmp_path: Path, monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(design_pause.gh, "resolve_repo", lambda *_args, **_kwargs: "owner/repo")  # type: ignore[attr-defined]
    monkeypatch.setattr(design_pause.gh, "issue_view_body", lambda *_args, **_kwargs: "plain body")  # type: ignore[attr-defined]
    rc = design_pause.pause_load_main(["--design-tmpdir", str(tmp_path), "--issue", "10", "--repo", "owner/repo"])
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=false" in out
    assert "ERROR=no-pause-marker" in out


def test_pause_save_writes_marker_on_publish_success(tmp_path: Path, monkeypatch: object, capsys: object) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-1c").write_text("", encoding="utf-8")
    _ = (design / "source-env.sh").write_text("export SESSION_ID=RUN1\nexport REPO=owner/repo\n", encoding="utf-8")
    monkeypatch.setattr(design_pause.gh, "issue_view_body", lambda *_args, **_kwargs: "issue body\n")  # type: ignore[attr-defined]

    def fake_run(cmd: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "log-publish" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="PUBLISH_OK=true\n", stderr="")
        if "named-block" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(design_pause.subprocess, "run", fake_run)  # type: ignore[attr-defined]
    rc = design_pause.pause_save_main(["--design-tmpdir", str(design), "--issue", "9", "--repo", "owner/repo"])
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "PAUSE_OK=true" in out
    assert (design / "pause-state.txt").is_file()
