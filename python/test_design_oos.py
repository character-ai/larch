"""Tests for design_oos.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import design_oos
from test_design_cli_ports import test_design_port_registry_entries_are_machine_stdout  # noqa: F401  # pylint: disable=unused-import  # pyright: ignore[reportUnusedImport]


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    return out


def test_prepare_ready_emits_expected_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    accepted.write_text(
        "### OOS_7: first\n- body\n\n"
        "### OOS_9: second\n- body\n",
        encoding="utf-8",
    )
    seen: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(args)
        if args[:2] == ("oos", "issue-cap"):
            output = Path(args[args.index("--output") + 1])
            output.write_text("### OOS_1: capped\n", encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        if args[:2] == ("oos", "file-conflict-deps"):
            output = Path(args[args.index("--output") + 1])
            output.write_text("1\t2\n", encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(design_oos, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_oos, "_count_non_security_blocks", lambda _text: 2)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])
    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    assert kv["FILE_DESIGN_OOS_DEPS_AVAILABLE"] == "true"
    assert kv["FILE_DESIGN_OOS_COMBINED"] == str(tmp_path / "oos-combined.md")
    assert kv["FILE_DESIGN_OOS_DEPS_TSV"] == str(tmp_path / "oos-intra-batch-deps.tsv")
    assert kv["FILE_DESIGN_OOS_ORDER"] == str(tmp_path / "oos-design-filing-order.txt")
    assert (tmp_path / "oos-design-filing-order.txt").read_text(encoding="utf-8") == "7\n9\n"
    assert ("oos", "issue-cap") in [call[:2] for call in seen]
    assert ("oos", "file-conflict-deps") in [call[:2] for call in seen]
    cap_call = next(call for call in seen if call[:2] == ("oos", "issue-cap"))
    assert "--input-file" in cap_call
    assert "--output" in cap_call
    assert "--design-tmpdir" not in cap_call


def test_prepare_uses_cross_session_cache_and_recovers_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    accepted.write_text("### OOS_3: title\n- desc\n", encoding="utf-8")
    cache = tmp_path / "cache.md"
    cache.write_text(
        "OOS_FILE_MAP\t3\thttps://github.com/acme/repo/issues/123\n"
        "https://github.com/acme/repo/issues/123\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(design_oos, "_cross_session_cache_path", lambda _issue: cache)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path), "--issue-number", "44"])
    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "skip-sentinel"
    assert "Filed URL" in accepted.read_text(encoding="utf-8")
    assert (tmp_path / "oos-issues-created.md").is_file()


def test_annotate_updates_accepted_and_returns_nonzero_on_reported_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    accepted.write_text(
        "### OOS_1: alpha\n- desc\n\n"
        "### OOS_2: beta\n- desc\n",
        encoding="utf-8",
    )
    (tmp_path / "oos-design-filing-order.txt").write_text("1\n2\n", encoding="utf-8")
    stdout_file = tmp_path / "oos-issue.stdout.txt"
    stdout_file.write_text(
        "ISSUE_1_URL=https://github.com/acme/repo/issues/101\n"
        "ISSUE_2_DUPLICATE_OF_URL=https://github.com/acme/repo/issues/102\n"
        "ISSUE_2_FAILED=true\n"
        "ISSUES_FAILED=1\n",
        encoding="utf-8",
    )
    cache = tmp_path / "cache.md"
    monkeypatch.setattr(design_oos, "_cross_session_cache_path", lambda _issue: cache)

    rc = design_oos.file_oos_annotate_main(["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(stdout_file), "--issue-number", "44"])
    assert rc == 1
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "annotate-complete"
    accepted_text = accepted.read_text(encoding="utf-8")
    assert "### OOS_1: alpha" in accepted_text
    assert "- **Filed URL**: https://github.com/acme/repo/issues/101" in accepted_text
    assert "### OOS_2: beta" in accepted_text
    assert "- **Filed URL**: https://github.com/acme/repo/issues/102" not in accepted_text
    sentinel_text = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    assert "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101" in sentinel_text
    assert "https://github.com/acme/repo/issues/101" in sentinel_text
    assert cache.read_text(encoding="utf-8") == sentinel_text


def test_annotate_empty_stdout_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = design_oos.file_oos_annotate_main(
        ["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(tmp_path / "missing.txt")],
    )
    assert rc == 1
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "annotate-failed-empty-stdout"
