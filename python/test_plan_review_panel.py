from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import plan_review_panel
from test_support import ROOT, run_cli

if TYPE_CHECKING:
    import pytest


def _stdout_key_order(stdout: str) -> list[str]:
    keys: list[str] = []
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key = line.split("=", 1)[0]
        if key != "WARN":
            keys.append(key)
    return keys


def _manifest_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_generic_plan_codex_row(rows: list[dict[str, object]]) -> dict[str, object]:
    row = next(row for row in rows if str(row.get("output", "")).endswith("codex-plan-generic-output.txt"))
    assert row["slot"] == "codex-plan-generic"
    assert row["tool"] == "codex"
    assert str(row["prompt_file"]).endswith("render-plan-codex-generic.prompt")
    assert "agent" not in row
    assert row["model_role"] == "default"
    return row


def _write_waterfall_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "waterfall-stub.sh"
    _ = stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${WATERFALL_STUB_ARGS_OUT:-}" ]]; then
  printf '%s\n' "$*" >"${WATERFALL_STUB_ARGS_OUT}"
fi
slots=""
mode=""
[[ -n "${WATERFALL_STUB_LOG:-}" ]] && printf '%s\n' "$*" >>"${WATERFALL_STUB_LOG}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${2:?}"; shift 2 ;;
    --mode) mode="${2:?}"; shift 2 ;;
    --plan-file|--feature-file) shift 2 ;;
    --codex-present|--cursor-present|--timeout|--model-role|--site|--require-first-line-pattern) shift 2 ;;
    --no-fallback|--straggler-cutoff|--skip-invalid-slots) shift 1 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" ]] || exit 2
# Mirror agent_waterfall.py's accepted set so a regressed dispatcher mode (issue
# #4747: the unsupported "plan-review") is rejected here exactly as the real
# waterfall would, instead of being silently accepted.
case "$mode" in
  diff|description) ;;
  *) printf 'dispatch-with-waterfall.sh: --mode must be diff or description\\n' >&2; exit 2 ;;
esac
if [[ -n "${WATERFALL_STUB_MODE_OUT:-}" ]]; then
  printf '%s' "$mode" >"${WATERFALL_STUB_MODE_OUT}"
fi
n=$(grep -c . "$slots" || echo 0)
printf 'DISPATCH_OK=true\\n'
printf 'FALLBACK_COUNT=0\\n'
printf 'PHASE2_RELAUNCH_COUNT=0\\n'
printf 'COMBINED_FALLBACK_COUNT=0\\n'
printf 'STATIC_DISPATCH_OK=true\\n'
printf 'DYNAMIC_DISPATCH_OK=true\\n'
_outpath="$(dirname "${WATERFALL_STUB_LOG:?}")/a.txt"
: >"$_outpath"
if [[ -n "${WATERFALL_STUB_PATHS_OUT:-}" ]]; then
  : >"${WATERFALL_STUB_PATHS_OUT}"
  _i=0
  while IFS= read -r _row || [[ -n "$_row" ]]; do
    [[ -n "$_row" ]] || continue
    _i=$((_i + 1))
    ((_i <= n)) && printf '%s\\n' "$_outpath" >>"${WATERFALL_STUB_PATHS_OUT}"
  done <"$slots"
fi
printf 'ALL_OUTPUT_FILES=%s\\n' "$_outpath"
printf 'ALL_OUTPUT_TOOLS=cursor\\n'
printf 'ALL_OUTPUT_FILES_PATH=%s\\n' "${WATERFALL_STUB_PATHS_OUT:-$_outpath}"
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def _write_python3_agent_stub(tmp_path: Path) -> Path:
    stub_dir = tmp_path / "python3-stub-bin"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    _ = stub.write_text(
        f"""#!{sys.executable}
import os
import sys
from pathlib import Path

real_python = os.environ["PLAN_REVIEW_PANEL_REAL_PYTHON"]
args = sys.argv[1:]
if len(args) >= 3 and args[1:3] == ["agent", "launch-claude-review"]:
    output = ""
    idx = 3
    while idx < len(args):
        if args[idx] in ("--output", "--output-file") and idx + 1 < len(args):
            output = args[idx + 1]
            idx += 2
        elif args[idx] in (
            "--prompt-file",
            "--mode",
            "--role",
            "--read-tools-add-dir",
            "--timeout",
            "--timing-task-kind",
        ):
            idx += 2
        else:
            idx += 1
    if not output:
        raise SystemExit(2)
    Path(output).write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n",
        encoding="utf-8",
    )
    Path(output + ".done").write_text("0\\n", encoding="utf-8")
    raise SystemExit(0)
os.execv(real_python, [real_python, *args])
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub_dir


def _write_render_failure_plugin(tmp_path: Path) -> Path:
    plugin_root = tmp_path / "render-failure-plugin"
    cli = plugin_root / "python" / "cli.py"
    cli.parent.mkdir(parents=True)
    _ = cli.write_text(
        f"""#!{sys.executable}
import sys

args = sys.argv[1:]
if args[:2] == ["render", "plan-review"]:
    if "--body-file" in args:
        sys.stderr.write("dynamic render failed\\nsecond line\\n")
        raise SystemExit(9)
    print("STATIC_RENDERED_PROMPT")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    cli.chmod(0o755)
    return plugin_root


def test_panel_dispatch_usage_failure() -> None:
    proc = run_cli("plan-review", "panel-dispatch")
    assert proc.returncode == 2
    assert proc.stderr


def test_voter_dispatch_usage_failure() -> None:
    proc = run_cli("plan-review", "voter-dispatch")
    assert proc.returncode == 2
    assert proc.stderr


def test_plan_review_cli_registry_contains_panel_verbs() -> None:
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "plan-review panel-dispatch" in proc.stdout
    assert "plan-review voter-dispatch" in proc.stdout


def test_panel_dispatch_static_slot_matrix(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps({"archetypes": []}),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DYNAMIC_SLOT_COUNT=0" in proc.stdout
    assert "PANEL_PATHS_FILE=" in proc.stdout
    manifest_lines = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8").splitlines()
    assert len([line for line in manifest_lines if line.strip()]) == 9
    static_prompt = (design / "render-plan-cursor-arch.prompt").read_text(encoding="utf-8")
    assert "verify the current plan does not already include the proposed fix" in static_prompt


def test_panel_dispatch_generic_codex_round_gate(tmp_path: Path) -> None:
    # generic_codex_rounds={1,2} per config: generalist present in rounds 1-2, absent in round 3.
    for round_num, expected in ((1, True), (2, True), (3, False)):
        design = tmp_path / f"design-round-{round_num}"
        design.mkdir()
        _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
        _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
        _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
        log = design / "wf.log"
        _ = log.write_text("", encoding="utf-8")
        stub = _write_waterfall_stub(tmp_path)
        proc = run_cli(
            "plan-review",
            "panel-dispatch",
            "--design-tmpdir",
            str(design),
            "--round-num",
            str(round_num),
            "--codex-present",
            "true",
            "--cursor-present",
            "true",
            "--plan-file",
            str(design / "plan.txt"),
            "--feature-file",
            str(design / "feature-description.txt"),
            "--timeout",
            "60",
            env={
                "LARCH_QUIET_DISABLE": "1",
                "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
                "WATERFALL_STUB_LOG": str(log),
                "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
            },
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        rows = _manifest_rows(design / "plan-review-slots.ndjson")
        present = any(str(row.get("output", "")).endswith("codex-plan-generic-output.txt") for row in rows)
        assert present is expected
        if expected:
            _ = _assert_generic_plan_codex_row(rows)


def test_panel_dispatch_generic_codex_unconditional_when_codex_absent(tmp_path: Path) -> None:
    # Upstream: generic codex is added unconditionally for rounds in generic_codex_rounds={1,2},
    # even when codex is absent; only specialist codex slots are gated on codex availability.
    def _run(round_num: int) -> list[dict[str, object]]:
        design = tmp_path / f"design-codex-absent-round-{round_num}"
        design.mkdir()
        _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
        _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
        _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
        log = design / "wf.log"
        _ = log.write_text("", encoding="utf-8")
        stub = _write_waterfall_stub(tmp_path)
        proc = run_cli(
            "plan-review",
            "panel-dispatch",
            "--design-tmpdir",
            str(design),
            "--round-num",
            str(round_num),
            "--codex-present",
            "false",
            "--cursor-present",
            "true",
            "--plan-file",
            str(design / "plan.txt"),
            "--feature-file",
            str(design / "feature-description.txt"),
            "--timeout",
            "60",
            env={
                "LARCH_QUIET_DISABLE": "1",
                "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
                "WATERFALL_STUB_LOG": str(log),
                "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
            },
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return _manifest_rows(design / "plan-review-slots.ndjson")

    for round_num in (1, 2):
        rows = _run(round_num)
        # Generic is present (unconditionally for rounds in {1,2}); specialist codex absent.
        assert any(str(row.get("output", "")).endswith("codex-plan-generic-output.txt") for row in rows)
        assert not any(str(row.get("slot", "")).startswith("codex-plan-") and row.get("slot") != "codex-plan-generic" for row in rows)

    rows3 = _run(3)
    assert not any(str(row.get("output", "")).endswith("codex-plan-generic-output.txt") for row in rows3)
    assert not any(row.get("tool") == "codex" for row in rows3)


def test_panel_dispatch_threads_design_step3_site(tmp_path: Path) -> None:
    design = tmp_path / "design-panel-site"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "--site design Step 3" in log.read_text(encoding="utf-8")
    assert "--model-role review" in log.read_text(encoding="utf-8")


def test_voter_dispatch_threads_design_step3_site_into_inline_waterfall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "voter-site"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    records: list[list[str]] = []
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        records.append(a)
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            outs: list[tuple[str, str]] = []
            for i, tok in enumerate(a):
                if tok == "--slots-file" and i + 1 < len(a) and Path(a[i + 1]).is_file():
                    for line in Path(a[i + 1]).read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        out = str(row["output"])
                        _ = Path(out).write_text("vote\n", encoding="utf-8")
                        outs.append((out, str(row.get("tool", "cursor"))))
            stdout = "ALL_OUTPUT_FILES=" + " ".join(o for o, _ in outs) + "\nALL_OUTPUT_TOOLS=" + " ".join(t for _, t in outs) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="3\n", stderr="")
        return cp(a, 0, stdout="", stderr="")

    class _FakePopen:
        def __init__(self, argv: object, **_kwargs: object) -> None:
            a = [str(x) for x in argv]  # type: ignore[union-attr]
            out = ""
            for i, tok in enumerate(a):
                if tok == "--output" and i + 1 < len(a):
                    out = a[i + 1]
            if out:
                _ = Path(out).write_text("vote\n", encoding="utf-8")
                _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
            self.returncode = 0

        def wait(self) -> int:
            return 0

    def _stub_parse_rate(*_a: object, **_k: object) -> str:
        return "OK"

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", _stub_parse_rate)
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
    ])
    assert rc == 0
    waterfall = next(a for a in records if tuple(a[2:4]) == ("agent", "dispatch-waterfall"))
    assert waterfall[waterfall.index("--site") + 1] == "design Step 3"
    assert waterfall[waterfall.index("--model-role") + 1] == "vote"
    voter_renders = [a for a in records if tuple(a[2:4]) == ("render", "voter")]
    assert voter_renders
    assert all(a[a.index("--findings-ledger-file") + 1] == str(design / "findings-ledger.tsv") for a in voter_renders)


def test_panel_dispatch_dynamic_scout_rows(tmp_path: Path) -> None:
    design = tmp_path / "design-dynamic"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "Check contracts.",
                    },
                    {
                        "name": "beta",
                        "focus_area": "architecture",
                        "weight": 2,
                        "rationale": "r2",
                        "prompt_body": "Check layering.",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DYNAMIC_SLOT_COUNT=4" in proc.stdout
    manifest_lines = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8").splitlines()
    assert len([line for line in manifest_lines if line.strip()]) == 13
    manifest_text = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8")
    assert "dyn-cursor-plan-alpha" in manifest_text
    assert "dyn-codex-plan-beta" in manifest_text


def test_panel_dispatch_dynamic_rows_render_full_scaffold(tmp_path: Path) -> None:
    # #4841: a rendered dynamic slot prompt must carry the full render plan-review
    # scaffold (explicit plan-file path + TSV/sentinel output contract), not just the raw
    # scout prompt_body. Before the fix the rendered dynamic .prompt was a single
    # sentence, so reviewers reviewed an unrelated committed plan.txt and were dropped
    # NOT_SUBSTANTIVE.
    design = tmp_path / "design-dynamic-scaffold"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "You are a contract-guard reviewer. Check contracts.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rendered = (design / "plan-review" / "round-1" / "dyn-cursor-plan-alpha.prompt").read_text(encoding="utf-8")
    # Scout body is present...
    assert "You are a contract-guard reviewer. Check contracts." in rendered
    # ...but it is no longer the ENTIRE prompt — the scaffold now wraps it.
    assert "Review the implementation plan file at " in rendered
    assert str((design / "plan.txt").resolve()) in rendered
    assert "verify the current plan does not already include the proposed fix" in rendered
    assert "schema_version\tscope\tseverity" in rendered
    assert '{"no_issues_found": true}' in rendered


def test_panel_dispatch_dynamic_render_failures_warn_and_keep_fallback_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = _write_render_failure_plugin(tmp_path)
    design = tmp_path / "design-dynamic-render-failure"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "Check dynamic rendering.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))

    rows, failures = plan_review_panel._dynamic_slot_rows(  # pyright: ignore[reportPrivateUsage]
        design=design,
        round_dir=round_dir,
        dynamic=[("cursor", "dyn-cursor-plan-alpha", "correctness", "Check dynamic rendering.")],
        plan_file=str(design / "plan.txt"),
        feature_file=str(design / "feature-description.txt"),
    )

    assert failures == [("dyn-cursor-plan-alpha", "cursor", 9)]
    assert rows[0]["slot"] == "dyn-cursor-plan-alpha"
    assert (round_dir / "dyn-cursor-plan-alpha.prompt").read_text(encoding="utf-8") == (
        "Review the design plan with a correctness lens."
    )
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "### Warnings" in issues
    assert "dyn-cursor-plan-alpha" in issues
    assert "dynamic render failed second line" in issues

    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DYNAMIC_RENDER_PANEL_WARNING=**⚠ Degraded plan-review panel: 2 dynamic render failure(s)" in proc.stdout
    manifest_text = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8")
    assert "dyn-cursor-plan-alpha" in manifest_text
    assert "dyn-codex-plan-alpha" in manifest_text
    assert (design / "render-plan-cursor-arch.prompt").read_text(encoding="utf-8") == "STATIC_RENDERED_PROMPT\n"
    assert (round_dir / "dyn-cursor-plan-alpha.prompt").read_text(encoding="utf-8") == (
        "Review the design plan with a correctness lens."
    )


def test_panel_dispatch_prunes_round_three_empty_panel(tmp_path: Path) -> None:
    design = tmp_path / "design-pruned"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    rows = [
        ("cursor", "cursor-plan-arch"),
        ("cursor", "cursor-plan-innovation"),
        ("cursor", "cursor-plan-pragmatic"),
        ("cursor", "cursor-plan-requirements"),
        ("codex", "codex-plan-arch"),
        ("codex", "codex-plan-innovation"),
        ("codex", "codex-plan-pragmatic"),
        ("codex", "codex-plan-requirements"),
        ("codex", "codex-plan-generic"),
    ]
    ledger_lines = ["round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"]
    for round_num in (1, 2):
        ledger_lines.extend(f"{round_num}\t{tool}\t{slot}\t{slot}\t0\t0\t0" for tool, slot in rows)
    _ = (design / "reviewer-prune-ledger.tsv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--round-num",
        "3",
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PANEL_PRUNED_EMPTY=true" in proc.stdout
    assert (design / "plan-review-slots.pre-prune.ndjson").is_file()
    assert not (design / "plan-review-slots.ndjson").read_text(encoding="utf-8").strip()


def test_voter_dispatch_absent_externals_falls_back_to_claude(tmp_path: Path) -> None:
    design = tmp_path / "absent"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "voter-dispatch",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "PATH": f"{_write_python3_agent_stub(tmp_path)}:{os.environ.get('PATH', '')}",
            "PLAN_REVIEW_PANEL_REAL_PYTHON": sys.executable,
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "VOTER_1_STATUS=launched" in proc.stdout
    assert "VOTER_1_TOOL=claude" in proc.stdout
    assert "VOTER_2_STATUS=failed" in proc.stdout
    assert "VOTER_3_STATUS=failed" in proc.stdout
    assert "DISPATCH_OK=true" in proc.stdout
    assert "VOTER_PATHS_FILE=" in proc.stdout


def test_voter_dispatch_stdout_key_order(tmp_path: Path) -> None:
    design = tmp_path / "healthy"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "voter-dispatch",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "PATH": f"{_write_python3_agent_stub(tmp_path)}:{os.environ.get('PATH', '')}",
            "PLAN_REVIEW_PANEL_REAL_PYTHON": sys.executable,
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    expected = [
        "DEGRADED_PANEL_WARNING",
        "VOTER_1_PATH",
        "VOTER_1_TOOL",
        "VOTER_1_STATUS",
        "VOTER_1_PARSE_RATE_STATUS",
        "VOTER_2_PATH",
        "VOTER_3_PATH",
        "VOTER_PATHS_FILE",
        "VOTER_2_TOOL",
        "VOTER_3_TOOL",
        "VOTER_2_STATUS",
        "VOTER_3_STATUS",
        "VOTER_2_PARSE_RATE_STATUS",
        "VOTER_3_PARSE_RATE_STATUS",
        "DISPATCH_OK",
    ]
    assert _stdout_key_order(proc.stdout) == expected


def test_panel_dispatch_passes_waterfall_supported_mode(tmp_path: Path) -> None:
    # Regression for issue #4747: dispatch_panel must pass a --mode the waterfall
    # accepts ({diff, description}). It previously passed the unsupported
    # "plan-review", which the waterfall rejected (exit 2) before launching any
    # reviewer, silently degrading every /design plan review to panel-failed.
    design = tmp_path / "design-mode"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    mode_out = design / "mode.seen"
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
            "WATERFALL_STUB_MODE_OUT": str(mode_out),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert mode_out.read_text(encoding="utf-8") == "description"
    assert "--skip-invalid-slots" in log.read_text(encoding="utf-8")


def test_panel_dispatch_passes_skip_invalid_slots_to_waterfall(tmp_path: Path) -> None:
    design = tmp_path / "design-skip-flag"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    args_out = design / "waterfall.args"
    stub = _write_waterfall_stub(tmp_path)

    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(design / "wf.log"),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
            "WATERFALL_STUB_ARGS_OUT": str(args_out),
        },
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "--skip-invalid-slots" in args_out.read_text(encoding="utf-8")


def test_panel_dispatch_surfaces_invalid_slot_degradation(tmp_path: Path) -> None:
    design = tmp_path / "design-invalid-warning"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    paths = design / "panel-paths.txt"
    drops = design / "panel-paths.txt.invalid-slots"
    _ = paths.write_text(str(design / "reviewer-output.txt") + "\n", encoding="utf-8")
    _ = drops.write_text(json.dumps({"line": 2, "slot": "bad-slot", "message": "invalid"}) + "\n", encoding="utf-8")
    stub = tmp_path / "waterfall-invalid-drop-stub.sh"
    _ = stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'DISPATCH_OK=true\\n'\n"
        f"printf 'ALL_OUTPUT_FILES_PATH={paths}\\n'\n"
        "printf 'ALL_OUTPUT_FILES=reviewer-output.txt\\n'\n"
        "printf 'ALL_OUTPUT_TOOLS=cursor\\n'\n"
        "printf 'INVALID_SLOT_DROP_COUNT=1\\n'\n"
        f"printf 'INVALID_SLOT_DROPS_FILE={drops}\\n'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        env={"LARCH_QUIET_DISABLE": "1", "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub)},
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PANEL_PATHS_FILE=" in proc.stdout
    assert "INVALID_SLOT_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped" in proc.stdout
    assert "bad-slot" in proc.stdout


def test_voter_dispatch_does_not_pass_skip_invalid_slots() -> None:
    source = (ROOT / "python" / "plan_review_panel.py").read_text(encoding="utf-8")
    voter_body = source.split("def dispatch_voters", 1)[1].split("def dispatch_panel_main", 1)[0]
    assert "--skip-invalid-slots" not in voter_body


def test_panel_dispatch_surfaces_waterfall_failure(tmp_path: Path) -> None:
    # Regression for issue #4747: when dispatch-waterfall exits non-zero, the panel
    # must surface the real exit code and stderr (durable failure-detail log + KV)
    # rather than discarding proc.stderr and reporting exit_code=unknown.
    design = tmp_path / "design-fail"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    failing_stub = tmp_path / "waterfall-fail-stub.sh"
    _ = failing_stub.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'dispatch-with-waterfall.sh: --mode must be diff or description\\n' >&2\n"
        "printf 'cursor token crsr_abcdefghijklmnopqrstuvwxyz\\n' >&2\n"
        "exit 7\n",
        encoding="utf-8",
    )
    failing_stub.chmod(0o755)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(failing_stub),
        },
    )
    assert proc.returncode == 7, proc.stderr + proc.stdout
    assert "PANEL_DISPATCH_EXIT_CODE=7" in proc.stdout
    kv = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in proc.stdout.splitlines() if "=" in line}
    detail_log = Path(kv["PANEL_FAILURE_DETAIL_LOG"])
    assert detail_log.is_file()
    detail_text = detail_log.read_text(encoding="utf-8")
    assert "exited 7" in detail_text
    assert "--mode must be diff or description" in detail_text
    assert "crsr_abcdefghijklmnopqrstuvwxyz" not in detail_text
    assert "crsr_abcdefghijklmnopqrstuvwxyz" not in proc.stderr
    assert "<REDACTED-TOKEN>" in detail_text
    assert "<REDACTED-TOKEN>" in proc.stderr
    assert "--mode must be diff or description" in proc.stderr


def test_panel_dispatch_dynamic_render_warning_on_waterfall_failure(
    tmp_path: Path,
) -> None:
    plugin_root = _write_render_failure_plugin(tmp_path)
    design = tmp_path / "design-dynamic-render-waterfall-fail"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "Check dynamic rendering.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    failing_stub = tmp_path / "waterfall-fail-stub.sh"
    _ = failing_stub.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'dispatch-with-waterfall.sh: waterfall failed after dynamic render degrade\\n' >&2\n"
        "exit 7\n",
        encoding="utf-8",
    )
    failing_stub.chmod(0o755)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(failing_stub),
        },
    )
    assert proc.returncode == 7, proc.stderr + proc.stdout
    assert "PANEL_DISPATCH_EXIT_CODE=7" in proc.stdout
    assert "DYNAMIC_RENDER_PANEL_WARNING=**⚠ Degraded plan-review panel: 2 dynamic render failure(s)" in proc.stdout


def test_panel_dispatch_rows_launchable_by_waterfall(tmp_path: Path) -> None:
    # Regression for issue #4765: every plan-review slot row the panel emits must be
    # accepted by the agent_waterfall consumer. The producer previously emitted an
    # inline "prompt" key and never set "prompt_file"/"agent", so _load_slots raised
    # "slot '...' must set either agent or prompt_file" on the first row and the panel
    # launched zero reviewers, silently degrading every /design plan review to
    # panel-failed. Feed a producer-built manifest (static + dynamic rows) through the
    # real slot validator and assert each row sets exactly one of agent/prompt_file
    # with a readable prompt file.
    import agent_waterfall  # noqa: PLC0415

    design = tmp_path / "design-contract"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "Check contracts.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    manifest = design / "plan-review-slots.ndjson"
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows, "panel must emit at least one slot row"
    for row in rows:
        has_agent = bool(row.get("agent"))
        has_prompt_file = bool(row.get("prompt_file"))
        assert has_agent != has_prompt_file, f"row must set exactly one of agent/prompt_file: {row}"
        if has_prompt_file:
            assert Path(str(row["prompt_file"])).is_file(), f"prompt_file must be readable: {row}"
    # The real consumer parser must accept the producer's manifest without raising.
    slots = agent_waterfall._load_slots(str(manifest))  # pyright: ignore[reportPrivateUsage]
    assert len(slots) == len(rows)
