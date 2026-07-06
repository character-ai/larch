from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from larch.core import config
from larch.report import tokens
from larch.review import plan_review_panel
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


def _argval(argv: list[str], flag: str) -> str:
    for i, tok in enumerate(argv):
        if tok == flag and i + 1 < len(argv):
            return argv[i + 1]
    return ""


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


def _dispatch_design_panel_for_tier(
    tmp_path: Path,
    tier: str,
    *,
    round_num: int = 1,
    prune_round_num: int | None = None,
    escalated_round: bool = False,
) -> tuple[subprocess.CompletedProcess[str], Path, list[dict[str, object]], list[str]]:
    suffix = f"{tier.lower()}-round-{round_num}"
    if escalated_round:
        suffix += "-escalated"
    design = tmp_path / f"design-{suffix}"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    args_out = design / "waterfall.args"
    stub = _write_waterfall_stub(tmp_path)
    args = [
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
        "--tier",
        tier,
        "--escalated-round",
        "true" if escalated_round else "false",
    ]
    if prune_round_num is not None:
        args.extend(["--prune-round-num", str(prune_round_num)])
    proc = run_cli(
        *args,
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(design / "wf.log"),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
            "WATERFALL_STUB_ARGS_OUT": str(args_out),
        },
    )
    rows = _manifest_rows(design / "plan-review-slots.ndjson") if (design / "plan-review-slots.ndjson").is_file() else []
    waterfall_args = args_out.read_text(encoding="utf-8").split() if args_out.is_file() else []
    return proc, design, rows, waterfall_args


def _assert_design_pair_shape(rows: list[dict[str, object]], *, codex_role: str) -> None:
    assert len(rows) == 8
    by_focus: dict[str, set[str]] = {}
    for row in rows:
        focus = str(row.get("focus_area") or "")
        tool = str(row.get("tool") or "")
        by_focus.setdefault(focus, set()).add(tool)
    assert by_focus == {
        "arch": {"codex", "cursor"},
        "innovation": {"codex", "cursor"},
        "pragmatic": {"codex", "cursor"},
        "requirements": {"codex", "cursor"},
    }
    codex_rows = [row for row in rows if row.get("tool") == "codex"]
    cursor_rows = [row for row in rows if row.get("tool") == "cursor"]
    assert len(codex_rows) == 4
    assert len(cursor_rows) == 4
    assert all(row.get("model_role") == codex_role for row in codex_rows)
    assert all(row.get("slot") != "codex-plan-generic" for row in rows)


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
    assert len([line for line in manifest_lines if line.strip()]) == 8
    wf_args = log.read_text(encoding="utf-8")
    assert "--panel-artifact-dir" in wf_args
    assert str(design / "plan-review" / "round-1") in wf_args
    static_prompt = (design / "render-plan-cursor-arch.prompt").read_text(encoding="utf-8")
    assert "verify the current plan does not already include the proposed fix" in static_prompt


def test_panel_dispatch_trivial_uses_pairs_and_review_codex_role(tmp_path: Path) -> None:
    proc, _design, rows, waterfall_args = _dispatch_design_panel_for_tier(tmp_path, "TRIVIAL")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    _assert_design_pair_shape(rows, codex_role="review")
    assert _argval(waterfall_args, "--model-role") == "review"


def test_panel_dispatch_moderate_uses_pairs_and_review_codex_role(tmp_path: Path) -> None:
    proc, _design, rows, waterfall_args = _dispatch_design_panel_for_tier(tmp_path, "MODERATE")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    _assert_design_pair_shape(rows, codex_role="review")
    assert _argval(waterfall_args, "--model-role") == "review"


def test_panel_dispatch_hard_uses_pairs_and_default_codex_role(tmp_path: Path) -> None:
    proc, _design, rows, waterfall_args = _dispatch_design_panel_for_tier(tmp_path, "HARD")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert len(rows) == 8
    by_focus: dict[str, set[str]] = {}
    for row in rows:
        by_focus.setdefault(str(row.get("focus_area") or ""), set()).add(str(row.get("tool") or ""))
    assert by_focus == {
        "arch": {"codex", "cursor"},
        "innovation": {"codex", "cursor"},
        "pragmatic": {"codex", "cursor"},
        "requirements": {"codex", "cursor"},
    }
    codex_rows = [row for row in rows if row.get("tool") == "codex"]
    roles_by_focus = {str(row["focus_area"]): str(row.get("model_role")) for row in codex_rows}
    assert roles_by_focus == {
        "arch": "review",
        "innovation": "review",
        "pragmatic": "default",
        "requirements": "default",
    }
    assert len({str(row["focus_area"]) for row in codex_rows}) == len(codex_rows)
    assert _argval(waterfall_args, "--model-role") == "default"


def test_panel_dispatch_omits_generic_codex_all_rounds(tmp_path: Path) -> None:
    for round_num in (1, 2, 3):
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
        assert present is False


def test_panel_dispatch_omits_generic_codex_when_codex_absent(tmp_path: Path) -> None:
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
        assert not any(str(row.get("output", "")).endswith("codex-plan-generic-output.txt") for row in rows)
        assert not any(row.get("tool") == "codex" for row in rows)

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
    log_text = log.read_text(encoding="utf-8")
    assert "--site design Step 3" in log_text
    assert "--model-role review" in log_text
    assert "--no-fallback" in log_text


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
                        _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
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

    parse_calls: list[dict[str, object]] = []

    def _stub_parse_rate(**kwargs: object) -> str:
        parse_calls.append(dict(kwargs))
        return "OK"

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", _stub_parse_rate)
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    waterfall = next(a for a in records if tuple(a[2:4]) == ("agent", "dispatch-waterfall"))
    assert waterfall[waterfall.index("--site") + 1] == "design Step 3"
    assert waterfall[waterfall.index("--model-role") + 1] == "vote"
    voter_renders = [a for a in records if tuple(a[2:4]) == ("render", "voter")]
    assert voter_renders
    assert all(a[a.index("--findings-ledger-file") + 1] == str(design / "findings-ledger.tsv") for a in voter_renders)
    assert [(str(call["slot"]), str(call["voter_tool"])) for call in parse_calls] == [
        ("1", "codex-validity"),
        ("2", "codex-plan-fidelity"),
        ("3", "codex-pragmatism"),
    ]


def test_voter_dispatch_marks_failed_when_done_sidecar_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "done-sidecar-failure"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess
    parse_calls: list[dict[str, object]] = []

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
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
                        done_rc = "1\n" if row.get("slot") == "voter-2" else "0\n"
                        _ = Path(out + ".done").write_text(done_rc, encoding="utf-8")
                        outs.append((out, str(row.get("tool", "cursor"))))
            stdout = "ALL_OUTPUT_FILES=" + " ".join(o for o, _ in outs) + "\nALL_OUTPUT_TOOLS=" + " ".join(t for _, t in outs) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="2\n", stderr="")
        return cp(a, 0, stdout="", stderr="")

    def _stub_parse_rate(**kwargs: object) -> str:
        parse_calls.append(dict(kwargs))
        return "OK"

    def _fake_larch_proc_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
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
                        done_rc = "1\n" if row.get("slot") == "voter-2" else "0\n"
                        _ = Path(out + ".done").write_text(done_rc, encoding="utf-8")
                        outs.append((out, str(row.get("tool", "cursor"))))
            stdout = "ALL_OUTPUT_FILES=" + " ".join(o for o, _ in outs) + "\nALL_OUTPUT_TOOLS=" + " ".join(t for _, t in outs) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="2\n", stderr="")
        if verb == ("voting", "voter-status-block"):
            pos = a[4:]
            stdout = (
                f"VOTER_1_PATH={pos[0]}\nVOTER_1_TOOL={pos[1]}\nVOTER_1_STATUS={pos[2]}\n"
                f"VOTER_1_PARSE_RATE_STATUS={pos[3]}\n"
                f"VOTER_2_PATH={pos[4]}\nVOTER_2_TOOL={pos[5]}\nVOTER_2_STATUS={pos[6]}\n"
                f"VOTER_2_PARSE_RATE_STATUS={pos[7]}\n"
                f"VOTER_3_PATH={pos[8]}\nVOTER_3_TOOL={pos[9]}\nVOTER_3_STATUS={pos[10]}\n"
                f"VOTER_3_PARSE_RATE_STATUS={pos[11]}\n"
                f"VOTER_PATHS_FILE={pos[12]}\n"
            )
            return cp(a, 0, stdout=stdout, stderr="")
        return cp(a, 0, stdout="", stderr="")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.larch_proc, "run", _fake_larch_proc_run)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", _stub_parse_rate)
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "VOTER_2_STATUS=failed" in stdout
    assert "VOTER_2_PARSE_RATE_STATUS=SKIPPED" in stdout
    assert [str(call["slot"]) for call in parse_calls] == ["1", "3"]


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        (1, "OK\n"),
        (0, "unexpected\n"),
    ],
)
def test_parse_rate_retry_returns_not_substantive_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
) -> None:
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        return cp(a, returncode, stdout=stdout, stderr="bad parse\n")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    design = tmp_path / "design"
    design.mkdir()
    ballot = design / "ballot.txt"
    ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    voter_file = design / "vote.txt"
    voter_file.write_text("vote\n", encoding="utf-8")
    prompt_file = design / "prompt.txt"
    prompt_file.write_text("prompt\n", encoding="utf-8")

    assert (
        plan_review_panel._parse_rate_retry(  # pyright: ignore[reportPrivateUsage]
            design=design,
            ballot=ballot,
            slot="2",
            voter_file=voter_file,
            voter_tool="codex-plan-fidelity",
            prompt_file=prompt_file,
        )
        == "NOT_SUBSTANTIVE"
    )


def test_fresh_calibration_stats_file_returns_none_when_feedback_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design-feedback-off"
    design.mkdir()
    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "0")
    assert plan_review_panel._fresh_calibration_stats_file(design=design) is None  # pyright: ignore[reportPrivateUsage]


def test_dispatch_voters_calibration_wiring_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    design = tmp_path / "design-cal"
    design.mkdir()
    _ = (design / "source-env.sh").write_text(f"REPO_ROOT={consumer}\n", encoding="utf-8")
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    run_calls: list[list[str]] = []
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        run_calls.append(a)
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("voter-calibration", "snapshot"):
            out = a[a.index("--out") + 1]
            _ = Path(out).write_text("tool\tyes_votes\n", encoding="utf-8")
            return cp(a, 0, stdout="", stderr="")
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
                        _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
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

    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "1")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    snapshot_calls = [a for a in run_calls if len(a) >= 4 and tuple(a[2:4]) == ("voter-calibration", "snapshot")]
    assert len(snapshot_calls) == 1
    assert snapshot_calls[0][snapshot_calls[0].index("--log-root") + 1] == str((consumer / "larch-logs").resolve())
    render_calls = [a for a in run_calls if len(a) >= 4 and tuple(a[2:4]) == ("render", "voter")]
    voter_tools = {
        (call[call.index("--voter-tool") + 1], Path(call[call.index("--calibration-stats-file") + 1]).name)
        for call in render_calls
        if "--voter-tool" in call and "--calibration-stats-file" in call
    }
    assert ("claude", "voter-calibration-stats.tsv") in voter_tools
    assert ("codex", "voter-calibration-stats.tsv") in voter_tools
    assert ("cursor", "voter-calibration-stats.tsv") in voter_tools
    rows = _manifest_rows(design / "plan-voter-slots.ndjson")
    for slot_name, expected_tools in (
        ("voter-1", {"codex", "cursor", "claude"}),
        ("voter-2", {"codex", "cursor", "claude"}),
        ("voter-3", {"codex", "cursor", "claude"}),
    ):
        row = next(r for r in rows if r.get("slot") == slot_name)
        prompt_files = row.get("prompt_files")
        assert isinstance(prompt_files, dict)
        assert set(prompt_files) == expected_tools  # type: ignore[arg-type]
    waterfall = next(a for a in run_calls if len(a) >= 4 and tuple(a[2:4]) == ("agent", "dispatch-waterfall"))
    # Plan voters now waterfall through their cross-vendor + Claude tiers (issue #5817).
    assert "--no-fallback" not in waterfall
    assert "--claude-read-tools-add-dir" in waterfall
    assert waterfall[waterfall.index("--claude-read-tools-add-dir") + 1] == str(design)
    for basename in (
        "codex-validity-plan-voter-prompt-codex.txt",
        "codex-validity-plan-voter-prompt-cursor.txt",
        "codex-validity-plan-voter-prompt-claude.txt",
        "codex-plan-fidelity-plan-voter-prompt-codex.txt",
        "codex-plan-fidelity-plan-voter-prompt-cursor.txt",
        "codex-plan-fidelity-plan-voter-prompt-claude.txt",
        "codex-pragmatism-plan-voter-prompt-codex.txt",
        "codex-pragmatism-plan-voter-prompt-cursor.txt",
        "codex-pragmatism-plan-voter-prompt-claude.txt",
    ):
        assert (design / basename).is_file()


def test_dispatch_voters_enqueues_both_slots_when_codex_down(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # issue #5817: with Codex down but Cursor up, voter-2 (Codex-primary) is no
    # longer dropped -- both slots are enqueued and the waterfall (no
    # --no-fallback) carries the cursor middle tier so voter-2 can run on Cursor.
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    design = tmp_path / "design-codex-down"
    design.mkdir()
    _ = (design / "source-env.sh").write_text(f"REPO_ROOT={consumer}\n", encoding="utf-8")
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            assert "--no-fallback" not in a
            outs: list[str] = []
            for i, tok in enumerate(a):
                if tok == "--slots-file" and i + 1 < len(a) and Path(a[i + 1]).is_file():
                    for line in Path(a[i + 1]).read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        out = str(json.loads(line)["output"])
                        _ = Path(out).write_text("vote\n", encoding="utf-8")
                        _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
                        outs.append(out)
            stdout = "ALL_OUTPUT_FILES=" + " ".join(outs) + "\nALL_OUTPUT_TOOLS=" + " ".join("cursor" for _ in outs) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="3\n", stderr="")
        return cp(a, 0, stdout="", stderr="")

    class _FakePopen:
        def __init__(self, argv: object, **_kwargs: object) -> None:
            a = [str(x) for x in argv]  # type: ignore[union-attr]
            for i, tok in enumerate(a):
                if tok == "--output" and i + 1 < len(a):
                    _ = Path(a[i + 1]).write_text("vote\n", encoding="utf-8")
                    _ = Path(a[i + 1] + ".done").write_text("0\n", encoding="utf-8")
            self.returncode = 0

        def wait(self) -> int:
            return 0

    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "0")
    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "false",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    rows = _manifest_rows(design / "plan-voter-slots.ndjson")
    assert {r.get("slot") for r in rows} == {"voter-1", "voter-2", "voter-3"}
    voter2 = next(r for r in rows if r.get("slot") == "voter-2")
    prompt_files = voter2.get("prompt_files")
    assert isinstance(prompt_files, dict)
    assert "cursor" in prompt_files  # cross-vendor middle tier present


def test_dispatch_voters_skips_stale_snapshot_after_snapshot_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design-snap-fail"
    design.mkdir()
    _ = (design / "source-env.sh").write_text(f"REPO_ROOT={tmp_path / 'consumer'}\n", encoding="utf-8")
    stale = design / "voter-calibration-stats.tsv"
    _ = stale.write_text("stale\n", encoding="utf-8")
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess
    render_with_stats: list[bool] = []

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("voter-calibration", "snapshot"):
            return cp(a, 1, stdout="", stderr="snapshot failed\n")
        if verb == ("render", "voter"):
            render_with_stats.append("--calibration-stats-file" in a)
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            return cp(a, 0, stdout="DISPATCH_OK=true\n", stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="1\n", stderr="")
        return cp(a, 0, stdout="", stderr="")

    class _FakePopen:
        def __init__(self, *_a: object, **_k: object) -> None:
            self.returncode = 0

        def wait(self) -> int:
            return 0

    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "1")
    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--round-num", "1",
    ])
    assert rc == 0
    assert not any(render_with_stats)


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
    assert len([line for line in manifest_lines if line.strip()]) == 12
    manifest_text = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8")
    assert "dyn-cursor-plan-alpha" in manifest_text
    assert "dyn-codex-plan-beta" in manifest_text
    rows = _manifest_rows(design / "plan-review-slots.ndjson")
    assert all(row.get("model_role") == "review" for row in rows if row.get("tool") == "codex")


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
    # ...but it is no longer the ENTIRE prompt — the scaffold now wraps it. For Cursor the
    # plan content is inlined (it cannot read the plan file under DESIGN_TMPDIR, #5518).
    assert "<larch_plan_under_review>" in rendered
    assert "Plan body." in rendered
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


def test_dynamic_slot_rows_thread_payload_bytes_from_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design-dynamic-payload"
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
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "plan-review"):
            sidecar = Path(a[a.index("--payload-bytes-output") + 1])
            sidecar.write_text("27\n", encoding="utf-8")
            return cp(a, 0, stdout="rendered dynamic prompt\n", stderr="")
        return cp(a, 0, stdout="", stderr="")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)

    rows, failures = plan_review_panel._dynamic_slot_rows(  # pyright: ignore[reportPrivateUsage]
        design=design,
        round_dir=round_dir,
        dynamic=[("cursor", "dyn-cursor-plan-alpha", "correctness", "Check dynamic rendering.")],
        plan_file=str(design / "plan.txt"),
        feature_file=str(design / "feature-description.txt"),
    )

    assert not failures
    assert rows[0]["payload_bytes"] == 27
    assert (round_dir / "dyn-cursor-plan-alpha.prompt").read_text(encoding="utf-8") == "rendered dynamic prompt\n"


def test_plan_review_rows_ignore_stale_payload_sidecars_on_fallback_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design-fallback"
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
    slot_defaults = (
        config.SlotDefault(slot="cursor-plan-arch", tool="cursor", output="cursor-plan-arch.txt", focus_area="architecture", archetype="arch"),
        config.SlotDefault(slot="codex-plan-generic", tool="codex", output="codex-plan-generic.txt", focus_area="", archetype="generic"),
    )
    monkeypatch.setattr(
        plan_review_panel.external_defaults,
        "slot_defaults",
        lambda role_id, env=None: slot_defaults if role_id == "design.plan_review_panel" else (),  # noqa: ARG005
    )
    monkeypatch.setattr(
        plan_review_panel.external_defaults,
        "panel_dispatch_policy",
        lambda role_id: config.PanelDispatchPolicy(generic_codex_rounds=frozenset({1})) if role_id == "design.plan_review_panel" else config.PanelDispatchPolicy(),
    )
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "plan-review"):
            sidecar = Path(a[a.index("--payload-bytes-output") + 1])
            sidecar.write_text("99\n", encoding="utf-8")
            return cp(a, 0, stdout="", stderr="")
        return cp(a, 0, stdout="", stderr="")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)

    rows = plan_review_panel._static_slot_rows(  # pyright: ignore[reportPrivateUsage]
        design=design,
        round_dir=round_dir,
        round_num=1,
        codex_present="true",
        cursor_present="true",
        plan_file=str(design / "plan.txt"),
        feature_file=str(design / "feature-description.txt"),
    )
    generic = plan_review_panel._generic_plan_codex_row(  # pyright: ignore[reportPrivateUsage]
        design=design,
        round_dir=round_dir,
        round_num=1,
        plan_file=str(design / "plan.txt"),
        feature_file=str(design / "feature-description.txt"),
    )

    assert rows[0]["prompt_file"] == str(design / "render-plan-cursor-arch.prompt")
    assert (design / "render-plan-cursor-arch.prompt").read_text(encoding="utf-8") == "Review the design plan with a architecture lens."
    assert "payload_bytes" not in rows[0]
    assert generic is not None
    assert generic["prompt_file"] == str(round_dir / "render-plan-codex-generic.prompt")
    assert (round_dir / "render-plan-codex-generic.prompt").read_text(encoding="utf-8") == "Review the design plan with a code-quality lens."
    assert "payload_bytes" not in generic


def test_filter_pruned_round_two_prunes_unproductive_rows(tmp_path: Path) -> None:
    design = tmp_path / "design-r2-prune"
    design.mkdir()
    manifest = design / "plan-review-slots.ndjson"
    rows = [
        {"tool": "cursor", "slot": "cursor-plan-arch"},
        {"tool": "codex", "slot": "codex-plan-arch"},
    ]
    _ = manifest.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )
    ledger_lines = ["round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"]
    ledger_lines.extend(f"1\t{row['tool']}\t{row['slot']}\t{row['slot']}\t0\t0\t0" for row in rows)
    _ = (design / "reviewer-prune-ledger.tsv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    out, kv = plan_review_panel._filter_pruned(  # pyright: ignore[reportPrivateUsage]
        design=design, manifest=manifest, prune_round_num=2
    )
    assert out == manifest
    assert kv["PANEL_PRUNED_EMPTY"] == "true"
    assert kv["PRUNED_COUNT"] == "2"
    assert (design / "plan-review-slots.pre-prune.ndjson").exists()


def test_panel_dispatch_prunes_round_two_empty_panel(tmp_path: Path) -> None:
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
    ]
    ledger_lines = ["round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"]
    ledger_lines.extend(f"1\t{tool}\t{slot}\t{slot}\t0\t0\t0" for tool, slot in rows)
    _ = (design / "reviewer-prune-ledger.tsv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--round-num",
        "2",
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


def test_panel_dispatch_hard_escalated_round_bypasses_prune(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design-hard-escalated-prune"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    rows = [
        ("cursor", "cursor-plan-arch"),
        ("codex", "codex-plan-arch"),
        ("cursor", "cursor-plan-innovation"),
        ("codex", "codex-plan-innovation"),
        ("cursor", "cursor-plan-pragmatic"),
        ("codex", "codex-plan-pragmatic"),
        ("cursor", "cursor-plan-requirements"),
        ("codex", "codex-plan-requirements"),
    ]
    ledger_lines = ["round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"]
    ledger_lines.extend(f"2\t{tool}\t{slot}\t{slot}\t0\t0\t0" for tool, slot in rows)
    _ = (design / "reviewer-prune-ledger.tsv").write_text("\n".join(ledger_lines) + "\n", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    seen_prune_rounds: list[int] = []
    original_filter = plan_review_panel._filter_pruned  # pyright: ignore[reportPrivateUsage]

    def _record_filter_pruned(*, design: Path, manifest: Path, prune_round_num: int) -> tuple[Path, dict[str, str]]:
        seen_prune_rounds.append(prune_round_num)
        return original_filter(design=design, manifest=manifest, prune_round_num=prune_round_num)

    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("DISPATCH_PLAN_REVIEW_WATERFALL_SH", str(stub))
    monkeypatch.setenv("WATERFALL_STUB_LOG", str(design / "wf.log"))
    monkeypatch.setenv("WATERFALL_STUB_PATHS_OUT", str(design / "paths.out"))
    monkeypatch.setattr(plan_review_panel, "_filter_pruned", _record_filter_pruned)
    rc = plan_review_panel.dispatch_panel([
        "--design-tmpdir",
        str(design),
        "--round-num",
        "3",
        "--prune-round-num",
        "3",
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--tier",
        "HARD",
        "--escalated-round",
        "true",
    ])

    stdout = capsys.readouterr().out
    assert rc == 0
    assert seen_prune_rounds == [0]
    assert _manifest_rows(design / "plan-review-slots.ndjson")
    assert "PANEL_PRUNED_EMPTY=false" in stdout
    assert not (design / "plan-review-slots.pre-prune.ndjson").exists()


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
        "--round-num",
        "1",
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
        "--round-num",
        "1",
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
        "VOTER_1_RETRIED",
    ]
    assert _stdout_key_order(proc.stdout) == expected


def test_voter_dispatch_claude_failure_codex_cursor_succeed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Full-panel dispatch is OK when Claude voter fails but Codex and Cursor succeed (issue #5637)."""
    design = tmp_path / "degraded-full-panel"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            outs: list[str] = []
            tools: list[str] = []
            for i, tok in enumerate(a):
                if tok == "--slots-file" and i + 1 < len(a) and Path(a[i + 1]).is_file():
                    for line in Path(a[i + 1]).read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        output = str(row["output"])
                        _ = Path(output).write_text("vote\n", encoding="utf-8")
                        _ = Path(output + ".done").write_text("0\n", encoding="utf-8")
                        outs.append(output)
                        tools.append(str(row.get("tool", "codex")))
            stdout = "ALL_OUTPUT_FILES=" + " ".join(outs) + "\nALL_OUTPUT_TOOLS=" + " ".join(tools) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="2\n", stderr="")
        if verb == ("voting", "degraded-warning"):
            return cp(a, 0, stdout="DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 2/3 effective judges produced substantive vote output.**\n", stderr="")
        if verb == ("voting", "voter-status-block"):
            pos = a[4:]
            v1p, v1t, v1s, v1r = pos[0], pos[1], pos[2], pos[3]
            v2p, v2t, v2s, v2r = pos[4], pos[5], pos[6], pos[7]
            v3p, v3t, v3s, v3r = pos[8], pos[9], pos[10], pos[11]
            pf = pos[12]
            out = (
                f"VOTER_1_PATH={v1p}\nVOTER_1_TOOL={v1t}\nVOTER_1_STATUS={v1s}\nVOTER_1_PARSE_RATE_STATUS={v1r}\n"
                f"VOTER_2_PATH={v2p}\nVOTER_2_TOOL={v2t}\nVOTER_2_STATUS={v2s}\nVOTER_2_PARSE_RATE_STATUS={v2r}\n"
                f"VOTER_3_PATH={v3p}\nVOTER_3_TOOL={v3t}\nVOTER_3_STATUS={v3s}\nVOTER_3_PARSE_RATE_STATUS={v3r}\n"
                f"VOTER_PATHS_FILE={pf}\n"
            )
            return cp(a, 0, stdout=out, stderr="")
        return cp(a, 0, stdout="", stderr="")

    class _FakePopen:
        def __init__(self, *_a: object, **_k: object) -> None:
            self.returncode = 1

        def wait(self) -> int:
            return 1

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "VOTER_1_STATUS=launched" in stdout
    # The externals-present path no longer launches a standalone Claude voter;
    # slot retry is handled by the shared waterfall.
    assert "VOTER_1_RETRIED=false" in stdout
    assert "VOTER_1_TOOL=codex-validity" in stdout
    assert "VOTER_2_TOOL=codex-plan-fidelity" in stdout
    assert "VOTER_3_TOOL=codex-pragmatism" in stdout
    assert "DEGRADED_PANEL_WARNING=" in stdout
    assert "DEGRADED_PANEL=1" in stdout
    assert "DISPATCH_OK=true" in stdout
    paths_content = (design / "plan-review-voter-paths.txt").read_text(encoding="utf-8")
    voter_lines = [ln for ln in paths_content.splitlines() if ln.strip()]
    assert len(voter_lines) == 3


def test_voter_dispatch_claude_retry_recovers_full_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A Claude voter timeout (exit 124) is retried once; a successful retry restores the vote (#5677)."""
    design = tmp_path / "retry-recovers-full-panel"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "launch-claude-review"):
            # The retry attempt writes a substantive vote and exits 0.
            out = _argval(a, "--output")
            if out:
                _ = Path(out).write_text("vote\n", encoding="utf-8")
                _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
            return cp(a, 0, stdout="", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            outs: list[str] = []
            tools: list[str] = []
            for i, tok in enumerate(a):
                if tok == "--slots-file" and i + 1 < len(a) and Path(a[i + 1]).is_file():
                    for line in Path(a[i + 1]).read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        output = str(row["output"])
                        _ = Path(output).write_text("vote\n", encoding="utf-8")
                        _ = Path(output + ".done").write_text("0\n", encoding="utf-8")
                        outs.append(output)
                        tools.append(str(row.get("tool", "codex")))
            stdout = "ALL_OUTPUT_FILES=" + " ".join(outs) + "\nALL_OUTPUT_TOOLS=" + " ".join(tools) + "\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        if verb == ("voting", "effective-judges"):
            return cp(a, 0, stdout="3\n", stderr="")
        if verb == ("voting", "voter-status-block"):
            pos = a[4:]
            v1p, v1t, v1s, v1r = pos[0], pos[1], pos[2], pos[3]
            v2p, v2t, v2s, v2r = pos[4], pos[5], pos[6], pos[7]
            v3p, v3t, v3s, v3r = pos[8], pos[9], pos[10], pos[11]
            pf = pos[12]
            out = (
                f"VOTER_1_PATH={v1p}\nVOTER_1_TOOL={v1t}\nVOTER_1_STATUS={v1s}\nVOTER_1_PARSE_RATE_STATUS={v1r}\n"
                f"VOTER_2_PATH={v2p}\nVOTER_2_TOOL={v2t}\nVOTER_2_STATUS={v2s}\nVOTER_2_PARSE_RATE_STATUS={v2r}\n"
                f"VOTER_3_PATH={v3p}\nVOTER_3_TOOL={v3t}\nVOTER_3_STATUS={v3s}\nVOTER_3_PARSE_RATE_STATUS={v3r}\n"
                f"VOTER_PATHS_FILE={pf}\n"
            )
            return cp(a, 0, stdout=out, stderr="")
        return cp(a, 0, stdout="", stderr="")

    class _FakePopen:
        def __init__(self, *_a: object, **_k: object) -> None:
            self.returncode = plan_review_panel.config.EXIT_TIMEOUT

        def wait(self) -> int:
            return plan_review_panel.config.EXIT_TIMEOUT

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "VOTER_1_RETRIED=false" in stdout
    assert "VOTER_1_STATUS=launched" in stdout
    assert "DISPATCH_OK=true" in stdout


def test_voter_dispatch_both_down_retry_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With both externals down, a failed sole Claude voter is retried once; a successful retry keeps the judge (#5677)."""
    design = tmp_path / "retry-both-down"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    cp = plan_review_panel.subprocess.CompletedProcess
    launches: dict[str, int] = {"n": 0}

    def _fake_run(argv: object, **_kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "launch-claude-review"):
            launches["n"] += 1
            out = _argval(a, "--output")
            if launches["n"] >= 2 and out:
                _ = Path(out).write_text("vote\n", encoding="utf-8")
                _ = Path(out + ".done").write_text("0\n", encoding="utf-8")
                return cp(a, 0, stdout="", stderr="")
            return cp(a, plan_review_panel.config.EXIT_TIMEOUT, stdout="", stderr="")
        if verb == ("voting", "voter-status-block"):
            pos = a[4:]
            return cp(
                a,
                0,
                stdout=(
                    f"VOTER_1_PATH={pos[0]}\nVOTER_1_TOOL={pos[1]}\nVOTER_1_STATUS={pos[2]}\n"
                    f"VOTER_1_PARSE_RATE_STATUS={pos[3]}\nVOTER_2_PATH={pos[4]}\nVOTER_3_PATH={pos[8]}\n"
                    f"VOTER_PATHS_FILE={pos[12]}\nVOTER_2_TOOL={pos[5]}\nVOTER_3_TOOL={pos[9]}\n"
                    f"VOTER_2_STATUS={pos[6]}\nVOTER_3_STATUS={pos[10]}\n"
                    f"VOTER_2_PARSE_RATE_STATUS={pos[7]}\nVOTER_3_PARSE_RATE_STATUS={pos[11]}\n"
                ),
                stderr="",
            )
        return cp(a, 0, stdout="", stderr="")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--round-num", "1",
    ])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert launches["n"] == 2
    assert "VOTER_1_RETRIED=true" in stdout
    assert "VOTER_1_STATUS=launched" in stdout
    assert "DISPATCH_OK=true" in stdout


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
    source = (ROOT / "python" / "larch" / "review" / "plan_review_panel.py").read_text(encoding="utf-8")
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
    from larch.agents import agent_waterfall  # noqa: PLC0415

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


def _append_panel_rows_from_waterfall_env(*, artifact_dir: str, slots_file: str, env: dict[str, str]) -> list[str]:
    saved = dict(os.environ)
    try:
        os.environ.update(env)
        outputs: list[str] = []
        phase = (env.get("LARCH_PANEL_PHASE") or "").lower()
        site = (env.get("LARCH_PANEL_SITE") or "").lower()
        if "voter" in phase:
            default_kind = "voter"
        elif "plan-review" in phase or "design" in site:
            default_kind = "plan-review"
        else:
            default_kind = "specialist"
        for line in Path(slots_file).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            out = Path(str(row["output"]))
            _ = out.write_text("finding\n", encoding="utf-8")
            outputs.append(str(out))
            tokens.append_panel_prompt_size(
                artifact_path=Path(artifact_dir) / tokens.PANEL_PROMPT_SIZE_BASENAME,
                output=out,
                tool=str(row.get("tool", "cursor")),
                prompt="plan-review prompt body",
                slot=str(row.get("slot", "")),
                slot_kind=default_kind,
            )
        return outputs
    finally:
        os.environ.clear()
        os.environ.update(saved)


def test_plan_review_panel_dispatch_materializes_panel_prompt_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design-panel-tsv"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(json.dumps({"archetypes": []}), encoding="utf-8")
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        env = cast("dict[str, str]", kwargs.get("env") or {})
        if verb == ("render", "plan-review"):
            return cp(a, 0, stdout="prompt body\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            artifact_dir = ""
            slots_file = ""
            for i, tok in enumerate(a):
                if tok == "--panel-artifact-dir" and i + 1 < len(a):
                    artifact_dir = a[i + 1]
                if tok == "--slots-file" and i + 1 < len(a):
                    slots_file = a[i + 1]
            outs = _append_panel_rows_from_waterfall_env(artifact_dir=artifact_dir, slots_file=slots_file, env=env)
            stdout = "ALL_OUTPUT_FILES=" + " ".join(outs) + "\nALL_OUTPUT_TOOLS=cursor\nDISPATCH_OK=true\n"
            return cp(a, 0, stdout=stdout, stderr="")
        return cp(a, 0, stdout="", stderr="")

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    rc = plan_review_panel.dispatch_panel([
        "--design-tmpdir", str(design),
        "--round-num", "2",
        "--codex-present", "false",
        "--cursor-present", "true",
        "--plan-file", str(design / "plan.txt"),
        "--feature-file", str(design / "feature-description.txt"),
    ])
    assert rc == 0
    tsv = round_dir / tokens.PANEL_PROMPT_SIZE_BASENAME
    assert tsv.is_file()
    assert not (design / tokens.PANEL_PROMPT_SIZE_BASENAME).exists()
    lines = [line for line in tsv.read_text(encoding="utf-8").splitlines() if line and not line.startswith("site\t")]
    assert lines
    assert all(line.split("\t")[4] == "plan-review" for line in lines)


def test_plan_review_voter_dispatch_materializes_panel_prompt_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design-voter-tsv"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    cp = plan_review_panel.subprocess.CompletedProcess

    def _fake_run(argv: object, **kwargs: object) -> object:
        a = [str(x) for x in argv]  # type: ignore[union-attr]
        verb = tuple(a[2:4]) if len(a) >= 4 else ()
        env = cast("dict[str, str]", kwargs.get("env") or {})
        if verb == ("render", "voter"):
            return cp(a, 0, stdout="prompt\nRead the ballot from this path: /x\n", stderr="")
        if verb == ("agent", "dispatch-waterfall"):
            artifact_dir = ""
            slots_file = ""
            for i, tok in enumerate(a):
                if tok == "--panel-artifact-dir" and i + 1 < len(a):
                    artifact_dir = a[i + 1]
                if tok == "--slots-file" and i + 1 < len(a):
                    slots_file = a[i + 1]
            outs = _append_panel_rows_from_waterfall_env(artifact_dir=artifact_dir, slots_file=slots_file, env=env)
            stdout = "ALL_OUTPUT_FILES=" + " ".join(outs) + "\nALL_OUTPUT_TOOLS=cursor\nDISPATCH_OK=true\n"
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

    monkeypatch.setattr(plan_review_panel.subprocess, "run", _fake_run)
    monkeypatch.setattr(plan_review_panel.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(plan_review_panel, "_parse_rate_retry", lambda **_k: "OK")  # type: ignore[arg-type]
    rc = plan_review_panel.dispatch_voters([
        "--ballot-file", str(ballot),
        "--design-tmpdir", str(design),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--round-num", "1",
    ])
    assert rc == 0
    tsv = round_dir / tokens.PANEL_PROMPT_SIZE_BASENAME
    assert tsv.is_file()
    assert not (design / tokens.PANEL_PROMPT_SIZE_BASENAME).exists()
    lines = [line for line in tsv.read_text(encoding="utf-8").splitlines() if line and not line.startswith("site\t")]
    assert lines
    assert all(line.split("\t")[4] == "voter" for line in lines)
# pyright: reportUnusedFunction=false
# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
