# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import dirty_tree


def test_scope_marker_present_heading() -> None:
    text = "### FINDING_1: [important] [SCOPE-REDUCTION] trim scope\nbody\n"
    assert dirty_tree.has_scope_reduction_marker(text)


def test_scope_marker_ignores_inline_code() -> None:
    assert not dirty_tree.has_scope_reduction_marker("what: `[SCOPE-REDUCTION] nope`\n")


def test_scope_check_all_in_scope(tmp_path, capsys) -> None:
    plan = tmp_path / "plan.txt"
    paths = tmp_path / "paths.z"
    plan.write_text("## Files to modify\n\n### UPDATED: `python/dirty_tree.py`\n", encoding="utf-8")
    paths.write_bytes(b"python/dirty_tree.py\0")
    assert dirty_tree.scope_check_main(["--plan-file", str(plan), "--paths-file", str(paths)]) == 0
    assert capsys.readouterr().out == ""


def test_scope_check_out_of_scope(tmp_path, capsys) -> None:
    plan = tmp_path / "plan.txt"
    paths = tmp_path / "paths.z"
    plan.write_text("## Files to modify\n\n### UPDATED: `python/dirty_tree.py`\n", encoding="utf-8")
    paths.write_bytes(b"README.md\0")
    assert dirty_tree.scope_check_main(["--plan-file", str(plan), "--paths-file", str(paths)]) == 1
    assert "README.md" in capsys.readouterr().err


def test_bad_baseline_path_status_unknown() -> None:
    lines = dirty_tree.baseline(baseline_path="bad path")
    assert "STATUS=unknown" in lines
    assert "REASON=bad-baseline-path" in lines
