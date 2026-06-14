"""Tests for file_oos.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import file_oos


def test_count_non_security_counts_canonical_oos_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Description**: bug\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_multiple_blocks(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: First\n- **Description**: a\n"
        "### OOS_2: Second\n- **Description**: b\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 2


def test_count_non_security_counts_legacy_tagged_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Legacy tagged block\n"
        "- **Description**: dropped before #3550.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_legacy_trailing_tagged_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: Legacy tagged block [OUT_OF_SCOPE]\n"
        "- **Description**: tag after title matches awk parity.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_legacy_oos_shorthand_header(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OOS] Legacy shorthand block\n"
        "- **Description**: tag after title matches awk parity.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_ignores_bare_finding_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: bare in-scope finding\n- **Concern**: stays in scope.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_security_tagged_legacy_header(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Security item\n"
        "- **focus-area**: security\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_backtick_unbold_security_focus_area(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Security item\n"
        "- `focus-area`: `security-hardening`\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_unbulleted_security_focus_area(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Security item\n"
        "focus-area: security-hardening\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_structured_security_heading(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: [security] Security item\n"
        "- **Description**: private routing.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_does_not_treat_body_security_heading_as_tag(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Public item\n"
        "- **Concern**: cites a heading below.\n"
        "### Example [security] policy\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_skips_missing_files(tmp_path: Path) -> None:
    assert file_oos.count_non_security((str(tmp_path / "nonexistent.md"),)) == 0


def test_detect_carve_out_forked(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path, forked=True)
    assert status.carve_out is True
    assert status.non_security_count == 0


def test_detect_carve_out_repo_unavailable(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path, repo_unavailable=True)
    assert status.carve_out is True


def test_detect_no_oos(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path)
    assert status.non_security_count == 0
    assert status.already_filed is False
    assert status.carve_out is False


def test_detect_with_accepted_oos(tmp_path: Path) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Description**: bug\n",
        encoding="utf-8",
    )
    status = file_oos.detect(tmp_path)
    assert status.non_security_count == 1
    assert status.already_filed is False


def test_detect_idempotent_when_sentinel_present(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "Created https://github.com/example/larch/issues/99\n",
        encoding="utf-8",
    )
    status = file_oos.detect(tmp_path)
    assert status.already_filed is True


def test_detect_security_present(tmp_path: Path) -> None:
    sec = tmp_path / "security-oos-observations.md"
    _ = sec.write_text("### OOS_1: sec item\n- **focus-area**: security\n", encoding="utf-8")
    status = file_oos.detect(tmp_path)
    assert status.security_present is True


def test_read_filed_urls_empty_sentinel(tmp_path: Path) -> None:
    assert file_oos.read_filed_urls_from_sentinel(None) == []
    assert file_oos.read_filed_urls_from_sentinel(str(tmp_path / "missing.md")) == []


def test_read_filed_urls_from_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "Created https://github.com/example/larch/issues/10\n"
        "Created https://github.com/example/larch/issues/11\n",
        encoding="utf-8",
    )
    urls = file_oos.read_filed_urls_from_sentinel(str(sentinel))
    assert len(urls) == 2


def test_accepted_oos_paths_returns_canonical_paths(tmp_path: Path) -> None:
    paths = file_oos.accepted_oos_paths(tmp_path)
    assert str(tmp_path / "oos-accepted-review.md") in paths
    assert str(tmp_path / "oos-accepted-main-agent.md") in paths


def test_cli_no_oos(tmp_path: Path) -> None:
    result = file_oos.main(["--tmpdir", str(tmp_path)])
    assert result == 0


def test_cli_with_forked(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = file_oos.main(["--tmpdir", str(tmp_path), "--forked"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["carve_out"] is True


def test_design_export_oos_path_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    exported = tmp_path / "design-export" / "oos-accepted-design.md"
    exported.parent.mkdir()
    _ = exported.write_text("### OOS_1: Exported\n- **Description**: ok\n", encoding="utf-8")
    resolved = file_oos.resolve_design_oos_path(tmp_path)
    assert resolved == exported


def test_design_tmpdir_env_oos_path_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design_dir = tmp_path / "design"
    design_dir.mkdir()
    accepted = design_dir / "oos-accepted-design.md"
    _ = accepted.write_text("### OOS_1: From design tmpdir\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_dir))
    resolved = file_oos.resolve_design_oos_path(tmp_path)
    assert resolved == accepted


def test_disposition_checkpoint_fails_on_security_sidecar(tmp_path: Path) -> None:
    _ = (tmp_path / "security-oos-observations.md").write_text("# security observation\n", encoding="utf-8")

    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 2
    assert "security-routed manifest OOS" in (tmp_path / "oos-disposition-checkpoint.stderr.log").read_text(encoding="utf-8")


def test_issue_cap_rejects_malformed_batch(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    _ = bad.write_text("### Item one\n- **Description**: not oos shaped\n", encoding="utf-8")
    with pytest.raises(ValueError, match="OOS-shaped"):
        file_oos.issue_cap(bad)


def test_file_conflict_deps_emits_numeric_rows(tmp_path: Path) -> None:
    src = tmp_path / "oos.md"
    _ = src.write_text(
        "### OOS_1: First\n- touches `src/a.py:1-5`\n\n"
        "### OOS_2: Second\n- touches `src/a.py:2-6`\n",
        encoding="utf-8",
    )
    deps = file_oos.file_conflict_deps(src)
    assert deps == [(1, 2)]


def test_disposition_gate_fails_without_disposition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Missing\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")

    def _inline_zero(_range: str) -> int:
        return 0

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_zero)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
    )
    assert rc == 1


def test_disposition_gate_passes_with_strict_filed_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Filed\n- **Phase**: implement\n", encoding="utf-8")
    strict = tmp_path / "strict.md"
    _ = strict.write_text("- **Filed URL**: https://github.com/example/larch/issues/99\n", encoding="utf-8")

    def _inline_zero(_range: str) -> int:
        return 0

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_zero)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[],
        filed_url_strict_files=[strict],
        commit_range="HEAD",
    )
    assert rc == 0


def test_disposition_gate_passes_with_inline_triage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Inline\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")

    def _inline_one(_range: str) -> int:
        return 1

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_one)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
    )
    assert rc == 0


def test_disposition_gate_bypasses_in_fork_mode(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Forked\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
        fork_mode=True,
    )
    assert rc == 0


def test_materialize_manifest_oos_writes_main_agent_file(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "status": "complete",
                "oos_observations": [
                    {"title": "Retain manifest OOS", "description": "Fix docs for manifest OOS.", "phase": "implement"},
                ],
            }
        ),
        encoding="utf-8",
    )
    count = file_oos.materialize_manifest_oos(manifest, tmp_path)
    assert count == 1
    text = (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")
    assert "### OOS_1: Retain manifest OOS" in text
    assert "- **Reviewer**: External implementer" in text


def test_disposition_checkpoint_uses_origin_main_when_merge_base_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text("FORKED_TARGET=false\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-main-agent.md").write_text("### OOS_1: Missing\n- **Phase**: implement\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-review.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-design.md").write_text("", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (run_dir / "oos-issues.ndjson").write_text("", encoding="utf-8")

    class Result:
        def __init__(self, returncode: int, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(argv: list[str], **_kwargs: object) -> Result:
        if argv[:3] == ["git", "merge-base", "HEAD"]:
            return Result(1, "")
        if argv[:4] == ["git", "rev-parse", "--verify", "origin/main"]:
            return Result(0, "abc123\n")
        return Result(0, "")

    seen: dict[str, str] = {}

    def fake_gate(**kwargs: object) -> int:
        seen["commit_range"] = str(kwargs["commit_range"])
        return 0

    _ = monkeypatch.setattr(file_oos.subprocess, "run", fake_run)
    _ = monkeypatch.setattr(file_oos, "disposition_gate", fake_gate)
    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    assert seen["commit_range"] == "origin/main..HEAD"
