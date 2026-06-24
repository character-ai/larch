# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import plan_scout
import pytest


def _row(name: str = "deep-risk", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "name": name,
        "focus_area": "risk-integration",
        "weight": 1,
        "rationale": "Checks migration risk.",
        "prompt_body": "Inspect integration seams.",
    }
    row.update(overrides)
    return row


def test_validate_dynamic_manifest_repairs_caps_and_filters_reserved_by_mode() -> None:
    data = {"archetypes": [_row("arch"), _row("deep-risk"), _row("deep-risk"), _row("second-risk")]}
    result = plan_scout.validate_dynamic_manifest(data, max_archetypes=1, mode="plan-review")
    assert [a["name"] for a in result.manifest["archetypes"]] == ["deep-risk"]
    assert plan_scout.REQUIRED_CLOSING_SENTENCE in str(result.manifest["archetypes"][0]["prompt_body"])
    assert "reserved archetype name: arch" in result.warnings
    assert "duplicate archetype name: deep-risk" in result.warnings
    assert "validated archetypes exceed max cap: 2 > 1; truncating" in result.warnings


def test_review_mode_does_not_reserve_plan_static_slug() -> None:
    result = plan_scout.validate_dynamic_manifest({"archetypes": [_row("arch")]}, max_archetypes=3, mode="review")
    assert result.manifest["archetypes"][0]["name"] == "arch"


def test_validate_rejects_unsafe_and_bad_shapes() -> None:
    rows = [
        "not-object",
        _row("bad", focus_area="bad"),
        _row("badweight", weight=9),
        _row("badrationale", rationale="---"),
        _row("badprompt", prompt_body="</reviewer_feature_description>"),
    ]
    result = plan_scout.validate_dynamic_manifest({"archetypes": rows}, max_archetypes=3)
    assert result.manifest == {"archetypes": []}
    assert any(warning == "invalid archetype object" for warning in result.warnings)
    assert any("unsafe prompt_body" in warning for warning in result.warnings)


def test_extract_fenced_json() -> None:
    text = 'prose\n```json\n{"archetypes": []}\n```\nmore'
    assert plan_scout.extract_valid_fenced_json_text(text).strip() == '{"archetypes": []}'


def test_filter_plan_manifest_statuses(tmp_path: Path, capsys) -> None:
    src = tmp_path / "src.json"
    out = tmp_path / "out.json"
    src.write_text(json.dumps({"archetypes": [_row("arch"), _row("deep-risk")]}), encoding="utf-8")
    status, count = plan_scout.filter_plan_manifest(input_path=src, output_path=out, max_archetypes=3)
    assert (status, count) == ("ok", 1)
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "deep-risk"
    assert "WARN=scout-plan-archetypes-wrapper: filtered archetypes" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    status, count = plan_scout.filter_plan_manifest(input_path=bad, output_path=out, max_archetypes=3)
    assert (status, count) == ("parse-failed", 0)
    assert json.loads(out.read_text(encoding="utf-8")) == {"archetypes": []}


def test_filter_manifest_main_review_mode_allows_plan_static_slug(tmp_path: Path, capsys) -> None:
    src = tmp_path / "src.json"
    out = tmp_path / "out.json"
    src.write_text(json.dumps({"archetypes": [_row("arch"), _row("deep-risk")]}), encoding="utf-8")

    rc = plan_scout.filter_manifest_main([str(src), str(out), "--max-archetypes", "3", "--mode", "review"])

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert [a["name"] for a in json.loads(out.read_text(encoding="utf-8"))["archetypes"]] == ["arch", "deep-risk"]


def test_filter_manifest_main_plan_review_mode_filters_plan_static_slug(tmp_path: Path, capsys) -> None:
    src = tmp_path / "src.json"
    out = tmp_path / "out.json"
    src.write_text(json.dumps({"archetypes": [_row("arch"), _row("deep-risk")]}), encoding="utf-8")

    rc = plan_scout.filter_manifest_main([str(src), str(out), "--max-archetypes", "3", "--mode", "plan-review"])

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert [a["name"] for a in json.loads(out.read_text(encoding="utf-8"))["archetypes"]] == ["deep-risk"]


def test_filter_manifest_main_rejects_unknown_mode(tmp_path: Path) -> None:
    src = tmp_path / "src.json"
    out = tmp_path / "out.json"
    src.write_text(json.dumps({"archetypes": []}), encoding="utf-8")

    rc = plan_scout.filter_manifest_main([str(src), str(out), "--mode", "bad"])

    assert rc == 2


def test_dynamic_diff_mode_stages_large_diff_and_emits_warning(tmp_path: Path, monkeypatch, capsys) -> None:
    diff = tmp_path / "review.diff"
    plan = tmp_path / "plan.md"
    diff.write_text("diff --git a/big b/big\n+" + ("x" * 300_000) + "\n", encoding="utf-8")
    plan.write_text("# plan\n", encoding="utf-8")
    out = tmp_path / "manifest.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude.sh"
    claude.write_text(
        "#!/usr/bin/env bash\n"
        "while [[ $# -gt 0 ]]; do if [[ $1 == --output-file ]]; then out=$2; shift 2; else shift; fi; done\n"
        "printf '{\"archetypes\":[{\"name\":\"api-contract\",\"focus_area\":\"correctness\",\"weight\":4,\"rationale\":\"API changes are central.\",\"prompt_body\":\"Check API contract compatibility.\"}]}' >\"$out\"\n"
        "printf 'ELAPSED=1\\n'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(
        mode="diff",
        max_archetypes=4,
        output=out,
        diff_file=str(diff),
        plan_file=str(plan),
        cursor_present=False,
    )
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert "staged --diff-file" in stdout
    assert f">{plan_scout.MAX_CONTEXT_BYTES}" in stdout
    staged_diff = out.parent / "staged-context" / "diff.txt"
    assert staged_diff.is_file()
    assert staged_diff.stat().st_size > plan_scout.MAX_CONTEXT_BYTES
    prompt = (out.parent / "staged-context" / "scout-dynamic-archetypes-prompt.md").read_text(encoding="utf-8")
    assert str(staged_diff) in prompt
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "api-contract"


def test_dynamic_zero_cap_writes_empty(tmp_path: Path, capsys) -> None:
    out = tmp_path / "manifest.json"
    plan_scout.scout_dynamic_archetypes(mode="diff", max_archetypes=0, output=out, diff_file="unused")
    assert json.loads(out.read_text(encoding="utf-8")) == {"archetypes": []}
    assert "SCOUT_STATUS=empty" in capsys.readouterr().out


def test_dynamic_description_cursor_miss_then_claude_winner(tmp_path: Path, monkeypatch, capsys) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "agent launch-review"
    cursor.write_text("#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf 'no json' >\"$out\"\nprintf 'ELAPSED=1\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    claude = bin_dir / "claude.sh"
    claude.write_text("#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output-file ]]; then out=$2; shift 2; else shift; fi; done\nprintf '{\"archetypes\":[{\"name\":\"deep-risk\",\"focus_area\":\"risk-integration\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect seams.\"}]}' >\"$out\"\nprintf 'ELAPSED=2\\n'\n", encoding="utf-8")
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH", str(cursor))
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=True)
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "deep-risk"
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert "cursor description-mode tier missed scout JSON" in stdout


def test_dynamic_default_launch_review_uses_python_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    recorded: list[list[str]] = []
    archetype = {
        "archetypes": [
            {
                "name": "deep-risk",
                "focus_area": "risk-integration",
                "weight": 1,
                "rationale": "ok",
                "prompt_body": "Inspect seams.",
            }
        ]
    }

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded.append(list(cmd))
        if "--output" in cmd and "--output-file" not in cmd:
            Path(cmd[cmd.index("--output") + 1]).write_text("not json", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ELAPSED=1\n", "")
        if "--output-file" in cmd:
            Path(cmd[cmd.index("--output-file") + 1]).write_text(json.dumps(archetype), encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ELAPSED=2\n", "")
        return subprocess.CompletedProcess(cmd, 1, "", "missing launcher")

    monkeypatch.delenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH", raising=False)
    monkeypatch.setattr(plan_scout.subprocess, "run", fake_run)
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=True)
    launch_cmds = [cmd for cmd in recorded if "launch-review" in cmd]
    assert launch_cmds
    cmd = launch_cmds[0]
    assert cmd[0] == sys.executable
    assert cmd[1].endswith("/python/cli.py")
    assert cmd[2:4] == ["agent", "launch-review"]
    assert "SCOUT_STATUS=ok" in capsys.readouterr().out


def test_dynamic_clears_stale_cap_hit_before_claude_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "launch-review.py"
    cursor.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        "raw = Path(sys.argv[sys.argv.index('--output') + 1])\n"
        "raw.write_text('not json', encoding='utf-8')\n"
        "Path(str(raw) + '.cap-hit').write_text('cap hit', encoding='utf-8')\n"
        "print('STATUS=cap_hit')\n"
        "print('ELAPSED=1')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    cursor.chmod(0o755)
    claude = bin_dir / "claude.py"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "raw = Path(sys.argv[sys.argv.index('--output-file') + 1])\n"
        "raw.write_text(json.dumps({'archetypes':[{'name':'deep-risk','focus_area':'risk-integration','weight':1,'rationale':'ok','prompt_body':'Inspect seams.'}]}), encoding='utf-8')\n"
        "print('ELAPSED=2')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH", str(cursor))
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=True)
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "deep-risk"
    assert not Path(str(out) + ".raw.cap-hit").exists()


def test_dynamic_diff_mode_claude_launch_uses_read_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diff = tmp_path / "review.diff"
    diff.write_text("diff --git a/a.py b/a.py\n+print('hi')\n", encoding="utf-8")
    out = tmp_path / "manifest.json"
    argv_capture = tmp_path / "claude-argv.json"
    claude = tmp_path / "claude.py"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        f"Path({str(argv_capture)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
        "raw = Path(sys.argv[sys.argv.index('--output-file') + 1])\n"
        "raw.write_text(json.dumps({'archetypes':[{'name':'api-contract','focus_area':'correctness','weight':1,'rationale':'ok','prompt_body':'Check API compatibility.'}]}), encoding='utf-8')\n"
        "print('ELAPSED=1')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="diff", max_archetypes=3, output=out, diff_file=str(diff), cursor_present=False)
    argv = json.loads(argv_capture.read_text(encoding="utf-8"))
    assert "--read-tools" in argv
    read_tools_dir = argv[argv.index("--read-tools-add-dir") + 1]
    assert read_tools_dir == str(out.parent / "staged-context")


def test_dynamic_archetypes_salvages_fenced_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    claude = tmp_path / "claude.py"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        "raw = Path(sys.argv[sys.argv.index('--output-file') + 1])\n"
        "raw.write_text('prose\\n```json\\n{\"archetypes\":[{\"name\":\"fenced-risk\",\"focus_area\":\"risk-integration\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect fenced JSON.\"}]}\\n```\\n', encoding='utf-8')\n"
        "print('ELAPSED=1')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=False)
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "fenced-risk"


def test_dynamic_archetypes_truncates_over_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    claude = tmp_path / "claude.py"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "rows = [\n"
        " {'name':'first-risk','focus_area':'risk-integration','weight':1,'rationale':'ok','prompt_body':'Inspect first risk.'},\n"
        " {'name':'second-risk','focus_area':'correctness','weight':1,'rationale':'ok','prompt_body':'Inspect second risk.'},\n"
        "]\n"
        "raw = Path(sys.argv[sys.argv.index('--output-file') + 1])\n"
        "raw.write_text(json.dumps({'archetypes': rows}), encoding='utf-8')\n"
        "print('ELAPSED=1')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=1, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=False)
    stdout = capsys.readouterr().out
    names = [row["name"] for row in json.loads(out.read_text(encoding="utf-8"))["archetypes"]]
    assert names == ["first-risk"]
    assert "validated archetypes exceed max cap: 2 > 1; truncating" in stdout


def test_validate_accepts_integral_float_weights() -> None:
    result = plan_scout.validate_dynamic_manifest({"archetypes": [_row("deep-risk", weight=3.0)]}, max_archetypes=3, mode="review")
    assert result.manifest["archetypes"][0]["weight"] == 3


def test_dynamic_invalid_archetypes_shape_is_parse_failed(tmp_path: Path, monkeypatch, capsys) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude.sh"
    claude.write_text("#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output-file ]]; then out=$2; shift 2; else shift; fi; done\nprintf '{\"archetypes\":{}}' >\"$out\"\nprintf 'ELAPSED=1\\n'\n", encoding="utf-8")
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=False)
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=parse-failed" in stdout
    assert "invalid_archetypes_shape" in stdout


def test_plan_wrapper_preserves_parse_failed_from_filter(tmp_path: Path, monkeypatch, capsys) -> None:
    plan = tmp_path / "plan.txt"
    desc = tmp_path / "feature-description.txt"
    plan.write_text("### UPDATED: `python/foo.py`\n", encoding="utf-8")
    desc.write_text("Feature", encoding="utf-8")
    out = tmp_path / "manifest.json"
    stub = tmp_path / "scout.sh"
    stub.write_text("#!/usr/bin/env bash\nout=\"\"\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf 'not-json' >\"$out\"\nprintf 'SCOUT_STATUS=ok\\nSCOUT_OUTPUT=%s\\nSCOUT_ARCHETYPE_COUNT=0\\n' \"$out\"\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", str(stub))
    plan_scout.scout_plan_archetypes(plan_file=plan, description_file=desc, output=out, max_archetypes=3, session_env_path=str(tmp_path / "env"), codex_present=False, cursor_present=False)
    assert "SCOUT_STATUS=parse-failed" in capsys.readouterr().out


def test_plan_wrapper_preserves_ok_when_filter_removes_all(tmp_path: Path, monkeypatch, capsys) -> None:
    plan = tmp_path / "plan.txt"
    desc = tmp_path / "feature-description.txt"
    plan.write_text("### UPDATED: `python/foo.py`\n", encoding="utf-8")
    desc.write_text("Feature", encoding="utf-8")
    out = tmp_path / "manifest.json"
    stub = tmp_path / "scout.sh"
    stub.write_text("#!/usr/bin/env bash\nout=\"\"\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf '{\"archetypes\":[{\"name\":\"arch\",\"focus_area\":\"architecture\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect architecture.\"}]}' >\"$out\"\nprintf 'SCOUT_STATUS=ok\\nSCOUT_OUTPUT=%s\\nSCOUT_ARCHETYPE_COUNT=1\\n' \"$out\"\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", str(stub))
    plan_scout.scout_plan_archetypes(plan_file=plan, description_file=desc, output=out, max_archetypes=3, session_env_path=str(tmp_path / "env"), codex_present=False, cursor_present=False)
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert "SCOUT_ARCHETYPE_COUNT=0" in stdout
    assert json.loads(out.read_text(encoding="utf-8")) == {"archetypes": []}


def test_plan_wrapper_uses_inner_override_and_filters(tmp_path: Path, monkeypatch, capsys) -> None:
    plan = tmp_path / "plan.txt"
    desc = tmp_path / "feature-description.txt"
    plan.write_text("### UPDATED: `python/foo.py`\n", encoding="utf-8")
    desc.write_text("Feature", encoding="utf-8")
    out = tmp_path / "manifest.json"
    stub = tmp_path / "scout.sh"
    stub.write_text("#!/usr/bin/env bash\nout=\"\"\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf '{\"archetypes\":[{\"name\":\"arch\",\"focus_area\":\"architecture\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect architecture.\"},{\"name\":\"deep-risk\",\"focus_area\":\"risk-integration\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect seams.\"}]}' >\"$out\"\nprintf 'SCOUT_STATUS=ok\\nSCOUT_OUTPUT=%s\\nSCOUT_ARCHETYPE_COUNT=2\\n' \"$out\"\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", str(stub))
    plan_scout.scout_plan_archetypes(plan_file=plan, description_file=desc, output=out, max_archetypes=3, session_env_path=str(tmp_path / "env"), codex_present=False, cursor_present=False)
    assert [a["name"] for a in json.loads(out.read_text(encoding="utf-8"))["archetypes"]] == ["deep-risk"]
    assert "SCOUT_STATUS=ok" in capsys.readouterr().out


def test_validate_prompt_override_rejects_outside_root_symlink_and_oversize(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()
    valid = plugin_root / "prompt.txt"
    valid.write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    link = plugin_root / "link.txt"
    link.symlink_to(valid)
    big = plugin_root / "big.txt"
    big.write_bytes(b"x" * (plan_scout.MAX_CONTEXT_BYTES + 1))
    assert plan_scout.validate_prompt_override(path=str(valid), plugin_root=plugin_root) == valid
    assert plan_scout.validate_prompt_override(path=str(outside), plugin_root=plugin_root) is None
    assert plan_scout.validate_prompt_override(path=str(link), plugin_root=plugin_root) is None
    assert plan_scout.validate_prompt_override(path=str(big), plugin_root=plugin_root) is None


def test_validate_context_file_rejects_outside_allowed_roots(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    session_root = tmp_path / "session"
    plugin_root.mkdir()
    session_root.mkdir()
    allowed = session_root / "scope.txt"
    allowed.write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    roots = [plugin_root, session_root]
    assert plan_scout.validate_context_file(label="--scope-files", path=str(allowed), roots=roots) == allowed
    with pytest.raises(plan_scout.UsageError, match="outside allowed roots"):
        plan_scout.validate_context_file(label="--scope-files", path=str(outside), roots=roots)


def test_dynamic_archetypes_rejects_invalid_prompt_override(tmp_path: Path) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review", encoding="utf-8")
    override = tmp_path / "override.txt"
    override.write_text("override", encoding="utf-8")
    out = tmp_path / "manifest.json"
    with pytest.raises(plan_scout.UsageError, match="prompt-override-file rejected"):
        plan_scout.scout_dynamic_archetypes(
            mode="description",
            max_archetypes=3,
            output=out,
            scope_files=str(scope),
            description_file=str(desc),
            prompt_override_file=str(override),
        )


def test_plan_wrapper_retries_without_override_when_prompt_override_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plan = tmp_path / "plan.txt"
    desc = tmp_path / "feature-description.txt"
    plan.write_text("### UPDATED: `python/foo.py`\n", encoding="utf-8")
    desc.write_text("Feature", encoding="utf-8")
    out = tmp_path / "manifest.json"
    calls = tmp_path / "calls.count"
    calls.write_text("0", encoding="utf-8")
    stub = tmp_path / "scout.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'calls="{calls}"\n'
        'n=$(cat "$calls")\n'
        'echo $((n+1)) >"$calls"\n'
        'out=""\n'
        "has_override=false\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  if [[ $1 == --output ]]; then out=$2; shift 2\n"
        "  elif [[ $1 == --prompt-override-file ]]; then has_override=true; shift 2\n"
        "  else shift; fi\n"
        "done\n"
        "if [[ $has_override == true && $n -eq 0 ]]; then\n"
        "  printf 'FAILURE_REASON=prompt-override-invalid\\n'; exit 2\n"
        "fi\n"
        "printf '{\"archetypes\":[{\"name\":\"deep-risk\",\"focus_area\":\"risk-integration\",\"weight\":1,\"rationale\":\"ok\",\"prompt_body\":\"Inspect seams.\"}]}' >\"$out\"\n"
        "printf 'SCOUT_STATUS=ok\\n'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    monkeypatch.setenv("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", str(stub))
    plan_scout.scout_plan_archetypes(
        plan_file=plan,
        description_file=desc,
        output=out,
        max_archetypes=3,
        session_env_path=str(tmp_path / "env"),
        codex_present=False,
        cursor_present=False,
    )
    stdout = capsys.readouterr().out
    assert int(calls.read_text(encoding="utf-8").strip()) == 2
    assert "SCOUT_STATUS=ok" in stdout
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "deep-risk"


def test_dynamic_manifest_warning_with_cr_in_invalid_name_does_not_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    scope = tmp_path / "scope.txt"
    desc = tmp_path / "desc.txt"
    scope.write_text("python/foo.py\n", encoding="utf-8")
    desc.write_text("review this", encoding="utf-8")
    out = tmp_path / "manifest.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude.sh"
    payload = json.dumps(
        {
            "archetypes": [
                {"name": "bad\nname", "focus_area": "architecture", "weight": 1, "rationale": "bad", "prompt_body": "Inspect."},
                {"name": "deep-risk", "focus_area": "risk-integration", "weight": 1, "rationale": "ok", "prompt_body": "Inspect seams."},
            ],
        },
    )
    claude.write_text(
        "#!/usr/bin/env bash\n"
        "while [[ $# -gt 0 ]]; do if [[ $1 == --output-file ]]; then out=$2; shift 2; else shift; fi; done\n"
        f"printf '%s' '{payload}' >\"$out\"\n"
        "printf 'ELAPSED=1\\n'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", str(claude))
    plan_scout.scout_dynamic_archetypes(mode="description", max_archetypes=3, output=out, scope_files=str(scope), description_file=str(desc), cursor_present=False)
    stdout = capsys.readouterr().out
    assert "SCOUT_STATUS=ok" in stdout
    assert json.loads(out.read_text(encoding="utf-8"))["archetypes"][0]["name"] == "deep-risk"
