"""Native panel and voter dispatch for /design plan review.

Topology anchor: round gated static plus dynamic.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import cast

from larch.review import findings_ledger
from larch.agents import agent_waterfall
from larch.core import external_defaults
from larch.calibration import difficulty
from larch.agents._launch_failure import resolve_model_args
from larch.review import review_pipeline
from larch.review import voting
from larch import io as larch_io
from larch.core import config
from larch.core import proc as larch_proc
from larch.core import redact
from larch.report import run_logs
from larch.report.tokens import build_panel_dispatch_env, read_panel_payload_bytes
from larch.state.session_env import validate_design_tmpdir

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCHETYPES = ("arch", "innovation", "pragmatic", "requirements")
_DISPATCH_LABEL = "plan-review voter-dispatch"
_PLAN_VOTER_PANEL_SIZE = 3
_SLOT_LABEL_MAX_LEN = 200
_GENERIC_CODEX_PLAN_REVIEW_ROLE = (
    "You are a senior reviewer for this project. Review code, plans, or conflict resolutions across "
    "code quality, risk/integration, correctness, architecture, and security."
)
# launch-claude-review is spawned via PATH `python3`, not sys.executable, to match
# the legacy dispatch-plan-voters.sh `python3 cli.py ...` contract and the panel
# test harness's python3-agent stub that short-circuits the claude launch. In
# production python3 resolves to the same interpreter the larch wrapper runs.
_AGENT_LAUNCH_PYTHON = "python3"


@dataclass(frozen=True)
class VoterPromptRenderOptions:
    scope_anchor: str = ""
    calibration_stats_file: str | None = None
    voter_tool: str | None = None
    output_path: Path | None = None


@dataclass(frozen=True)
class VoterPromptResult:
    prompt_file: Path
    payload_bytes: int = 0


@dataclass
class DispatchState:
    voter_1_path: Path
    voter_2_path: Path
    voter_3_path: Path
    voter_1_tool: str
    voter_2_tool: str
    voter_3_tool: str
    voter_1_status: str
    voter_2_status: str
    voter_3_status: str
    voter_1_parse_rate_status: str = "SKIPPED"
    voter_2_parse_rate_status: str = "SKIPPED"
    voter_3_parse_rate_status: str = "SKIPPED"


_DEFAULT_VOTER_PROMPT_RENDER_OPTIONS = VoterPromptRenderOptions()


def _voter_prompt_render_options(
    *,
    design: Path,
    scope_anchor: str,
    calibration_stats_file: str | None,
    voter_tool: str,
    basename: str,
) -> VoterPromptRenderOptions:
    return VoterPromptRenderOptions(
        scope_anchor=scope_anchor,
        calibration_stats_file=calibration_stats_file,
        voter_tool=voter_tool,
        output_path=design / basename,
    )


def _static_slot_rows(
    *,
    design: Path,
    round_dir: Path,
    round_num: int,
    codex_present: str,
    cursor_present: str,
    plan_file: str,
    feature_file: str,
    tier: str = difficulty.MODERATE,
) -> list[dict[str, object]]:
    _ = round_num
    rows: list[dict[str, object]] = []
    codex_slots = codex_present == "true"
    cli = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "render", "plan-review"]
    static_slots = [slot for slot in external_defaults.slot_defaults("design.plan_review_panel") if slot.archetype != "generic"]
    for slot in static_slots:
        if slot.tool == "codex" and not codex_slots:
            continue
        if slot.tool == "cursor" and cursor_present != "true":
            continue
        archetype = slot.archetype
        prompt_path = design / f"render-plan-{slot.tool}-{archetype}.prompt"
        payload_sidecar = prompt_path.with_name(prompt_path.name + ".payload-bytes")
        proc = subprocess.run(
            [
                *cli,
                "--archetype",
                archetype,
                "--vendor",
                slot.tool,
                "--plan-file",
                plan_file,
                "--design-tmpdir",
                str(design),
                "--feature-file",
                feature_file,
                "--findings-ledger-file",
                str(findings_ledger.ledger_path(design)),
                "--payload-bytes-output",
                str(payload_sidecar),
            ],
            cwd=str(_REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        prompt = proc.stdout if proc.returncode == 0 else ""
        row = _slot_row(
            tool=slot.tool,
            slot=slot.slot,
            focus=slot.focus_area or archetype,
            output=round_dir / slot.output,
            prompt_file=prompt_path,
            prompt=prompt,
            payload_bytes=read_panel_payload_bytes(payload_sidecar) if proc.returncode == 0 and prompt else 0,
        )
        if slot.tool == "codex":
            role = difficulty.codex_review_model_role_for_archetype(
                "design.plan_review_panel",
                slot.archetype,
                tier,
            )
            row["model_role"] = role
            row["resolved_model"] = _resolved_model_for_row(slot.tool, role)
        rows.append(row)
    generic = _generic_plan_codex_row(
        design=design,
        round_dir=round_dir,
        round_num=round_num,
        plan_file=plan_file,
        feature_file=feature_file,
        tier=tier,
    )
    if generic:
        rows.append(generic)
    return rows


def _generic_plan_codex_row(
    *,
    design: Path,
    round_dir: Path,
    round_num: int,
    plan_file: str,
    feature_file: str,
    tier: str = difficulty.MODERATE,
) -> dict[str, object] | None:
    policy = external_defaults.panel_dispatch_policy("design.plan_review_panel")
    if not policy or round_num not in policy.generic_codex_rounds:
        return None
    slot = next(row for row in external_defaults.slot_defaults("design.plan_review_panel") if row.archetype == "generic")
    body_file = round_dir / "render-plan-codex-generic.body"
    _ = body_file.write_text(_GENERIC_CODEX_PLAN_REVIEW_ROLE + "\n", encoding="utf-8")
    prompt_path = round_dir / "render-plan-codex-generic.prompt"
    payload_sidecar = prompt_path.with_name(prompt_path.name + ".payload-bytes")
    proc = subprocess.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "render",
            "plan-review",
            "--vendor",
            "codex",
            "--archetype",
            "generic",
            "--body-file",
            str(body_file),
            "--plan-file",
            plan_file,
            "--design-tmpdir",
            str(design),
            "--feature-file",
            feature_file,
            "--findings-ledger-file",
            str(findings_ledger.ledger_path(design)),
            "--payload-bytes-output",
            str(payload_sidecar),
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    prompt = proc.stdout if proc.returncode == 0 else ""
    row = _slot_row(
        tool=slot.tool,
        slot=slot.slot,
        focus=slot.focus_area or "code-quality",
        output=round_dir / slot.output,
        prompt_file=prompt_path,
        prompt=prompt,
        payload_bytes=read_panel_payload_bytes(payload_sidecar) if proc.returncode == 0 and prompt else 0,
    )
    role = difficulty.codex_review_model_role(tier)
    row["model_role"] = role
    row["resolved_model"] = _resolved_model_for_row(slot.tool, role)
    return row

def _resolved_model_for_row(tool: str, model_role: str = "") -> str:
    try:
        if model_role == "review":
            role = "review"
        elif model_role == "vote":
            role = "vote"
        elif model_role == "fix":
            role = "fix"
        else:
            role = "default"
        argv = list(resolve_model_args(tool, with_effort=(tool == "codex"), codex_role=role).argv)
    except (ValueError, KeyError):
        return "unknown"
    if tool == "cursor" and "--model" in argv:
        idx = argv.index("--model")
        return argv[idx + 1] if idx + 1 < len(argv) else "unknown"
    if tool == "codex" and "-m" in argv:
        idx = argv.index("-m")
        return argv[idx + 1] if idx + 1 < len(argv) else "unknown"
    return "unknown"

def _with_attribution(row: dict[str, object]) -> dict[str, object]:
    tool = str(row.get("tool") or "unknown")
    role = str(row.get("model_role") or "default")
    _ = row.setdefault("vendor", tool)
    _ = row.setdefault("resolved_model", _resolved_model_for_row(tool, role))
    return row

def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or _REPO_ROOT)


def _emit(*, key: str, value: object = "") -> None:
    print(f"{key}={value}")


def _validate_tmpdir(*, parser: argparse.ArgumentParser, value: str, create: bool = False) -> Path:
    path = Path(value)
    ok, message = validate_design_tmpdir(value)
    # voter-dispatch validates the path is allowed, then creates it (mirroring the
    # legacy dispatch-plan-voters.sh `mkdir -p "$DESIGN_TMPDIR"`); the prompt-render
    # smoke relies on dispatch creating the design tmpdir.
    if create and ok and not path.is_symlink():
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or not ok or path.is_symlink():
        parser.exit(2, f"{parser.prog}: {message}\n")
    return path.resolve()


def _slot_row(*, tool: str, slot: str, focus: str, output: Path, prompt_file: Path, prompt: str = "", payload_bytes: int = 0) -> dict[str, object]:
    # Write the rendered prompt (or the one-line fallback when the render was empty or
    # non-zero) to its own file and reference it via "prompt_file", matching the voter
    # manifest pattern below. agent_waterfall._load_slots accepts only "agent" or
    # "prompt_file"; an inline "prompt" key is ignored, so the consumer rejected the
    # first row and the panel launched zero reviewers (#4765).
    prompt_text = prompt or f"Review the design plan with a {focus} lens."
    _ = prompt_file.write_text(prompt_text, encoding="utf-8")
    row: dict[str, object] = {
        "tool": tool,
        "slot": slot,
        "name": slot,
        "focus_area": focus,
        "prompt_file": str(prompt_file),
        "output": str(output),
    }
    if payload_bytes > 0:
        row["payload_bytes"] = payload_bytes
    return _with_attribution(row)


def _load_dynamic_rows(design: Path) -> list[tuple[str, str, str, str]]:
    manifest = design / "scout-plan-manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    manifest_data: dict[str, object] = data  # type: ignore[assignment]
    rows: list[tuple[str, str, str, str]] = []
    archetypes = manifest_data.get("archetypes", [])
    if not isinstance(archetypes, list):
        return []
    for raw in cast("list[object]", archetypes):
        if not isinstance(raw, dict):
            continue
        archetype: dict[str, object] = raw  # type: ignore[assignment]
        name = str(archetype.get("name") or "").strip()
        focus = str(archetype.get("focus_area") or "correctness").strip() or "correctness"
        prompt = str(archetype.get("prompt_body") or "").strip()
        if not name:
            continue
        rows.append(("cursor", f"dyn-cursor-plan-{name}", focus, prompt))
        rows.append(("codex", f"dyn-codex-plan-{name}", focus, prompt))
    return rows


def _dynamic_slot_rows(
    *,
    design: Path,
    round_dir: Path,
    dynamic: list[tuple[str, str, str, str]],
    plan_file: str,
    feature_file: str,
    tier: str = difficulty.MODERATE,
) -> tuple[list[dict[str, object]], list[tuple[str, str, int]]]:
    _ = tier
    # Route dynamic scout slots through the same `render plan-review` scaffold as static
    # slots (#4841). Before the fix the raw scout prompt_body was the entire prompt, so
    # dynamic reviewers had no plan-file path (they grepped the repo and reviewed an
    # unrelated committed larch-logs/design/*/plan.txt) and no TSV/sentinel output
    # contract (their prose was dropped NOT_SUBSTANTIVE). The prompt_body is written to a
    # body-file and substituted for the fixed role line, inheriting the rest of the
    # scaffold. On a render miss `_slot_row` keeps the existing one-line fallback, exactly
    # as the static path does.
    cli = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "render", "plan-review"]
    rows: list[dict[str, object]] = []
    failures: list[tuple[str, str, int]] = []
    for tool, slot, focus, prompt in dynamic:
        body_file = round_dir / f"{slot}.body"
        _ = body_file.write_text(prompt, encoding="utf-8")
        payload_sidecar = round_dir / f"{slot}.prompt.payload-bytes"
        proc = subprocess.run(
            [
                *cli,
                "--vendor",
                tool,
                "--plan-file",
                plan_file,
                "--design-tmpdir",
                str(design),
                "--feature-file",
                feature_file,
                "--body-file",
                str(body_file),
                "--findings-ledger-file",
                str(findings_ledger.ledger_path(design)),
                "--payload-bytes-output",
                str(payload_sidecar),
                "--body-file-payload",
            ],
            cwd=str(_REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        rendered = proc.stdout if proc.returncode == 0 else ""
        if proc.returncode != 0:
            failures.append((slot, tool, proc.returncode))
            with contextlib.suppress(OSError):
                _append_dynamic_render_warning(design=design, slot=slot, tool=tool, return_code=proc.returncode, diagnostics=proc.stderr or proc.stdout or "")
        row = _slot_row(tool=tool, slot=slot, focus=focus, output=round_dir / f"{slot}.txt", prompt_file=round_dir / f"{slot}.prompt", prompt=rendered, payload_bytes=read_panel_payload_bytes(payload_sidecar) if proc.returncode == 0 and rendered else 0)
        if tool == "codex":
            role = "review"
            row["model_role"] = role
            row["resolved_model"] = _resolved_model_for_row(tool, role)
        rows.append(row)
    return rows, failures


def _write_manifest(*, rows: list[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")  # pyright: ignore[reportUnusedCallResult]


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _sanitize_slot_label(label: str) -> str:
    cleaned = re.sub(r"[\r\n\t]+", " ", str(label or "")).strip()
    return cleaned[:_SLOT_LABEL_MAX_LEN] if len(cleaned) > _SLOT_LABEL_MAX_LEN else cleaned


def _sanitize_warning_text(text: str) -> str:
    return re.sub(r"[\r\n\t]+", " ", str(text or "")).strip()


def _append_dynamic_render_warning(*, design: Path, slot: str, tool: str, return_code: int, diagnostics: str) -> None:
    detail = _sanitize_warning_text(redact.redact_secrets_only(redact.redact_tmpdir_paths(diagnostics)))
    entry = (
        f"- **Dynamic plan-review render failed for {_sanitize_slot_label(slot)} "
        f"({tool}, exit {return_code}); using fallback prompt.**"
    )
    if detail:
        entry += f" {detail}"
    run_logs.append_execution_issue(log_file=design / "execution-issues.md", category="Warnings", entry=entry)


def _dynamic_render_panel_warning(failures: list[tuple[str, str, int]]) -> str:
    if not failures:
        return ""
    names = [_sanitize_slot_label(slot) for slot, _tool, _rc in failures if _sanitize_slot_label(slot)]
    shown = names[:3]
    suffix = "" if len(names) <= len(shown) else f", +{len(names) - len(shown)} more"
    detail = f" Fallback slots: {', '.join(shown)}{suffix}." if shown else ""
    return _sanitize_warning_text(
        f"**⚠ Degraded plan-review panel: {len(failures)} dynamic render failure(s); using fallback prompts.**{detail}"
    )


def _invalid_slot_drop_summary(path: str) -> str:
    if not path:
        return ""
    drop_path = Path(path)
    try:
        lines = drop_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    labels: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        row = cast("dict[str, object]", data)
        slot = _sanitize_slot_label(str(row.get("slot") or ""))
        if slot:
            labels.append(slot)
            continue
        line_no = str(row.get("line") or "").strip()
        if line_no:
            labels.append(f"line {line_no}")
    if not labels:
        return ""
    shown = labels[:3]
    suffix = "" if len(labels) <= len(shown) else f", +{len(labels) - len(shown)} more"
    return f" Dropped: {', '.join(shown)}{suffix}."


def _degraded_invalid_slot_warning(kv: dict[str, str]) -> str:
    count = int(kv.get("INVALID_SLOT_DROP_COUNT", "0") or "0") if (kv.get("INVALID_SLOT_DROP_COUNT", "0") or "0").isdigit() else 0
    if count <= 0:
        return ""
    summary = _invalid_slot_drop_summary(kv.get("INVALID_SLOT_DROPS_FILE", ""))
    return _sanitize_warning_text(
        f"**⚠ Degraded plan-review panel: {count} invalid slot row(s) dropped; continuing with remaining reviewers.**{summary}"
    )


def _filter_pruned(*, design: Path, manifest: Path, prune_round_num: int) -> tuple[Path, dict[str, str]]:
    if review_pipeline.prune_window_evaluated(prune_round_num) != "true":
        return manifest, {"PANEL_PRUNED_EMPTY": "false", "PRUNED_COUNT": "0"}
    pre = design / "plan-review-slots.pre-prune.ndjson"
    out = design / "plan-review-slots.pruned.ndjson"
    _ = pre.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "review",
            "reviewer-prune",
            "filter",
            "--ledger",
            str(design / "reviewer-prune-ledger.tsv"),
            "--round",
            str(prune_round_num),
            "--manifest",
            str(pre),
            "--out",
            str(out),
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return manifest, {"PANEL_PRUNED_EMPTY": "false", "PRUNED_COUNT": "0", "PRUNE_FAIL_OPEN": "true"}
    kv = _parse_kv(proc.stdout)
    pruned_count = int(kv.get("PRUNED_COUNT", "0") or "0") if (kv.get("PRUNED_COUNT", "0") or "0").isdigit() else 0
    if pruned_count == 0:
        with contextlib.suppress(FileNotFoundError):
            pre.unlink()
        return manifest, kv
    out.replace(manifest)  # pyright: ignore[reportUnusedCallResult]
    return manifest, kv


def _validated_tier_args(*, parser: argparse.ArgumentParser, tier: str, escalated_round: str) -> str:
    normalized = difficulty.normalize_tier(tier)
    if not normalized:
        parser.error("--tier must be TRIVIAL, MODERATE, or HARD")
    if escalated_round not in {"true", "false"}:
        parser.error("--escalated-round must be true or false")
    return normalized


def dispatch_panel(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review panel-dispatch")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round-num", type=int, default=1)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--prune-round-num", type=int, default=0)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--codex-present", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--cursor-present", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--plan-file", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--feature-file", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--timeout", default="600")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--tier", default="MODERATE")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--escalated-round", default="false")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    design = _validate_tmpdir(parser=parser, value=ns.design_tmpdir)
    tier = _validated_tier_args(parser=parser, tier=ns.tier, escalated_round=ns.escalated_round)
    round_dir = design / "plan-review" / f"round-{ns.round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = _static_slot_rows(
        design=design, round_dir=round_dir,
        round_num=ns.round_num,
        codex_present=ns.codex_present,
        cursor_present=ns.cursor_present,
        plan_file=ns.plan_file,
        feature_file=ns.feature_file,
        tier=tier,
    )
    static_count = len(rows)
    dynamic = _load_dynamic_rows(design)
    dynamic_rows, dynamic_failures = _dynamic_slot_rows(
        design=design, round_dir=round_dir, dynamic=dynamic,
        plan_file=ns.plan_file,
        feature_file=ns.feature_file,
        tier=tier,
    )
    rows.extend(dynamic_rows)
    manifest = design / "plan-review-slots.ndjson"
    _write_manifest(rows=rows, path=manifest)
    prune_round_num = 0 if ns.escalated_round == "true" else (ns.prune_round_num or ns.round_num)
    manifest, prune_kv = _filter_pruned(design=design, manifest=manifest, prune_round_num=prune_round_num)
    dynamic_warning = _dynamic_render_panel_warning(dynamic_failures)
    if prune_kv.get("PANEL_PRUNED_EMPTY") == "true":
        if dynamic_warning:
            _emit(key="DYNAMIC_RENDER_PANEL_WARNING", value=dynamic_warning)
        _emit(key="PANEL_PRUNED_EMPTY", value="true")
        _emit(key="STATIC_SLOT_COUNT", value=static_count)
        _emit(key="DYNAMIC_SLOT_COUNT", value=len(dynamic))
        _emit(key="PANEL_PATHS_FILE", value=str(design / "plan-review-panel-paths.txt"))
        return 0
    waterfall = os.environ.get("DISPATCH_PLAN_REVIEW_WATERFALL_SH", "")
    if waterfall:
        cmd = [waterfall]
    else:
        cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "agent", "dispatch-waterfall"]
    panel_env = build_panel_dispatch_env(
        artifact_dir=round_dir,
        site="design Step 3",
        round_num=ns.round_num,
        round_dir=round_dir,
        phase="plan-review",
    )
    proc = subprocess.run(
        [
            *cmd,
            "--slots-file",
            str(manifest),
            "--panel-artifact-dir",
            str(round_dir),
            "--plan-file",
            ns.plan_file,
            "--feature-file",
            ns.feature_file,
            "--codex-present",
            ns.codex_present,
            "--cursor-present",
            ns.cursor_present,
            "--mode",
            "description",
            "--timeout",
            ns.timeout,
            "--skip-invalid-slots",
            "--site",
            "design Step 3",
            "--model-role",
            difficulty.codex_review_model_role(tier),
            "--no-fallback",
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env=panel_env,
    )
    print(proc.stdout, end="")
    if proc.returncode != 0:
        # Stop swallowing the waterfall's error (issue #4747). When dispatch-waterfall
        # exits non-zero, persist its stderr plus the real exit code to a durable log,
        # re-surface them on stderr, and emit them as KV so panel-failed is never
        # diagnostic-free. proc.stderr was previously captured and discarded, leaving
        # operators with exit_code=unknown and an empty failure_detail_log.
        failure_log = design / "plan-review-panel-failure.log"
        detail = redact.redact_secrets_only(redact.redact_tmpdir_paths(proc.stderr or ""))
        _ = failure_log.write_text(
            f"agent dispatch-waterfall exited {proc.returncode}\n{detail}",
            encoding="utf-8",
        )
        if detail:
            print(detail, end="" if detail.endswith("\n") else "\n", file=sys.stderr)
        _emit(key="PANEL_DISPATCH_EXIT_CODE", value=proc.returncode)
        _emit(key="PANEL_FAILURE_DETAIL_LOG", value=str(failure_log))
        _emit(key="STATIC_SLOT_COUNT", value=static_count)
        _emit(key="DYNAMIC_SLOT_COUNT", value=len(dynamic))
        _emit(key="PANEL_PRUNED_EMPTY", value=prune_kv.get("PANEL_PRUNED_EMPTY", "false"))
        if dynamic_warning:
            _emit(key="DYNAMIC_RENDER_PANEL_WARNING", value=dynamic_warning)
        return proc.returncode
    kv = _parse_kv(proc.stdout)
    paths_file = kv.get("ALL_OUTPUT_FILES_PATH", "") or str(design / "plan-review-panel-paths.txt")
    _emit(key="STATIC_SLOT_COUNT", value=static_count)
    _emit(key="DYNAMIC_SLOT_COUNT", value=len(dynamic))
    _emit(key="PANEL_PRUNED_EMPTY", value=prune_kv.get("PANEL_PRUNED_EMPTY", "false"))
    _emit(key="PANEL_PATHS_FILE", value=paths_file)
    degraded_warning = _degraded_invalid_slot_warning(kv)
    if degraded_warning:
        _emit(key="INVALID_SLOT_PANEL_WARNING", value=degraded_warning)
    if dynamic_warning:
        _emit(key="DYNAMIC_RENDER_PANEL_WARNING", value=dynamic_warning)
    return proc.returncode


def _feedback_enabled() -> bool:
    return os.environ.get(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "").strip() != "0"


def _fresh_calibration_stats_file(*, design: Path) -> str | None:
    target = design / "voter-calibration-stats.tsv"
    with contextlib.suppress(FileNotFoundError):
        target.unlink()
    if not _feedback_enabled():
        return None
    fd, tmp = tempfile.mkstemp(prefix=".voter-calibration-stats.", suffix=".tsv", dir=str(design))
    os.close(fd)
    tmp_path = Path(tmp)
    with contextlib.suppress(FileNotFoundError):
        tmp_path.unlink()
    try:
        log_root = voting._resolve_voter_calibration_log_root(design_tmpdir=design, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        return None
    result = larch_proc.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voter-calibration",
            "snapshot",
            "--log-root",
            str(log_root),
            "--out",
            str(tmp_path),
        ],
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size <= 0:
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        return None
    _ = tmp_path.replace(target)
    return str(target)


def _make_voter_prompt(
    *,
    design: Path,
    ballot: Path,
    tool: str,
    render_options: VoterPromptRenderOptions = _DEFAULT_VOTER_PROMPT_RENDER_OPTIONS,
) -> VoterPromptResult:
    prompt_file = render_options.output_path or design / f"{tool}-plan-voter-prompt{f'-{render_options.voter_tool}' if render_options.voter_tool else ''}.txt"
    payload_sidecar = prompt_file.with_name(prompt_file.name + ".payload-bytes")
    args = [
        sys.executable,
        str(_plugin_root() / "python" / "cli.py"),
        "render",
        "voter",
        "--ballot-file",
        str(ballot),
        "--panel-role",
        "senior engineer on a voting panel deciding which proposed plan modifications should be accepted",
        "--id-grammar",
        "finding-oos",
        "--verification-context",
        "plan",
        "--findings-ledger-file",
        str(findings_ledger.ledger_path(design)),
        "--payload-bytes-output",
        str(payload_sidecar),
    ]
    if render_options.scope_anchor:
        args.extend(["--scope-anchor-file", render_options.scope_anchor])
    if render_options.voter_tool:
        args.extend(["--voter-tool", render_options.voter_tool])
        if render_options.calibration_stats_file:
            args.extend(["--calibration-stats-file", render_options.calibration_stats_file])
    proc = subprocess.run(args, cwd=str(_REPO_ROOT), text=True, capture_output=True, check=False)
    if proc.returncode != 0 or "Read the ballot from this path" not in proc.stdout:
        raise RuntimeError(f"render voter failed for {tool}")
    _ = prompt_file.write_text(proc.stdout, encoding="utf-8")
    return VoterPromptResult(prompt_file=prompt_file, payload_bytes=read_panel_payload_bytes(payload_sidecar))


def _parse_rate_retry(*, design: Path, ballot: Path, slot: str, voter_file: Path, voter_tool: str, prompt_file: Path) -> str:
    proc = subprocess.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voting",
            "parse-rate-retry",
            "--ballot-file",
            str(ballot),
            "--id-grammar",
            "finding-oos",
            "--review-tmpdir",
            str(design),
            "--plugin-root",
            str(_plugin_root()),
            "--dispatch-label",
            _DISPATCH_LABEL,
            "--retry-prefix-kind",
            "plan",
            "--launch-mode",
            "description",
            "--slot",
            slot,
            "--voter-file",
            str(voter_file),
            "--voter-tool",
            voter_tool,
            "--prompt-file",
            str(prompt_file),
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return "NOT_SUBSTANTIVE"
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return "NOT_SUBSTANTIVE"
    status = lines[-1]
    if status not in {"OK", "NOT_SUBSTANTIVE"}:
        return "NOT_SUBSTANTIVE"
    return status


def _launch_claude_voter(*, design: Path, prompt_file: Path, output: Path, env: dict[str, str] | None = None) -> int:
    # lint-subprocess-via-runner: ok voter launch uses raw subprocess to capture the returncode for the bounded retry (#5677)
    return subprocess.run(
        [
            _AGENT_LAUNCH_PYTHON,
            str(_plugin_root() / "python" / "cli.py"),
            "agent",
            "launch-claude-review",
            "--output",
            str(output),
            "--prompt-file",
            str(prompt_file),
            "--mode",
            "description",
            "--role",
            "voter",
            "--read-tools-add-dir",
            str(design),
            "--timeout",
            "1200",
            "--timing-task-kind",
            "claude-plan-voter",
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    ).returncode


def _voter_needs_retry(*, rc: int, output: Path) -> bool:
    # The Claude plan voter emits empty output on a minority of runs (#5677):
    # exit 124 (timeout or the #5605 degraded-auth fast-fail) or a zero-byte /
    # missing output file from a "No messages returned from query" failure. Both
    # are retryable. A non-substantive-but-present vote is a content signal handled
    # downstream by the tally, not an empty-output failure, so it is not retried here.
    if rc == config.EXIT_TIMEOUT:
        return True
    return (not output.is_file()) or output.stat().st_size == 0


def _launchable_voter_tools(
    policy: config.VoterPolicyDefault,
    *,
    codex_present: bool,
    cursor_present: bool,
) -> list[str]:
    present = {"codex": codex_present, "cursor": cursor_present, "claude": True}
    tools: list[str] = []
    primary = policy.primary_tool
    if present.get(primary, False):
        tools.append(primary)
    if primary in {"codex", "cursor"}:
        alt = "cursor" if primary == "codex" else "codex"
        if present.get(alt, False):
            tools.append(alt)
        tools.append("claude")
    if primary == "claude":
        tools.append("claude")
    semantic_tools = {tool for tool, _label in policy.semantic_labels}
    return [tool for tool in dict.fromkeys(tools) if tool in semantic_tools]


def _build_plan_voter_prompt_files(
    *,
    design: Path,
    ballot: Path,
    policies: Sequence[config.VoterPolicyDefault],
    codex_present: bool,
    cursor_present: bool,
    scope_anchor: str,
    calibration_stats_file: str | None,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, int]]]:
    prompt_files: dict[str, dict[str, str]] = {}
    payload_files: dict[str, dict[str, int]] = {}
    for policy in policies:
        prompt_files[policy.slot_name] = {}
        payload_files[policy.slot_name] = {}
        for tool in _launchable_voter_tools(policy, codex_present=codex_present, cursor_present=cursor_present):
            rendered = _make_voter_prompt(
                design=design,
                ballot=ballot,
                tool=tool,
                render_options=_voter_prompt_render_options(
                    design=design,
                    scope_anchor=scope_anchor,
                    calibration_stats_file=calibration_stats_file,
                    voter_tool=tool,
                    basename=f"{policy.default_label}-plan-voter-prompt-{tool}.txt",
                ),
            )
            prompt_files[policy.slot_name][tool] = str(rendered.prompt_file)
            payload_files[policy.slot_name][tool] = rendered.payload_bytes
    return prompt_files, payload_files


def _write_plan_voter_waterfall_manifest(
    *,
    design: Path,
    policies: Sequence[config.VoterPolicyDefault],
    prompt_files: Mapping[str, Mapping[str, str]],
    payload_files: Mapping[str, Mapping[str, int]],
) -> Path:
    manifest = design / "plan-voter-slots.ndjson"
    with manifest.open("w", encoding="utf-8") as handle:
        for policy in policies:
            row = {
                "slot": policy.slot_name,
                "tool": policy.primary_tool,
                "output": str(design / policy.output_name),
                "prompt_files": dict(prompt_files.get(policy.slot_name, {})),
                "payload_files": dict(payload_files.get(policy.slot_name, {})),
            }
            _ = handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return manifest


def _semantic_label(policy: config.VoterPolicyDefault, tool: str) -> str:
    return dict(policy.semantic_labels).get(tool, policy.default_label)


def _state_from_bindings(
    *,
    design: Path,
    policies: Sequence[config.VoterPolicyDefault],
    bindings: Mapping[str, agent_waterfall.SlotOutputBinding],
    launched_policies: Sequence[config.VoterPolicyDefault],
) -> DispatchState:
    launched = {policy.slot_name for policy in launched_policies}
    policy_by_slot = {policy.slot_name: policy for policy in policies}

    def _resolve(slot_name: str) -> tuple[Path, str, str]:
        policy = policy_by_slot[slot_name]
        default_path = design / policy.output_name
        if slot_name not in launched:
            return default_path, policy.default_label, "skipped"
        binding = bindings.get(slot_name, agent_waterfall.SlotOutputBinding())
        if binding.dropped or not binding.path:
            return default_path, policy.default_label, "failed"
        return Path(binding.path), _semantic_label(policy, binding.tool or policy.primary_tool), "launched"

    path1, tool1, status1 = _resolve("voter-1")
    path2, tool2, status2 = _resolve("voter-2")
    path3, tool3, status3 = _resolve("voter-3")
    return DispatchState(
        voter_1_path=path1,
        voter_2_path=path2,
        voter_3_path=path3,
        voter_1_tool=tool1,
        voter_2_tool=tool2,
        voter_3_tool=tool3,
        voter_1_status=status1,
        voter_2_status=status2,
        voter_3_status=status3,
    )


def _file_nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _read_done_exit_code(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return ""


def _emit_final_kvs(*, state: DispatchState, voter_paths_file: Path, dispatch_ok: str) -> None:
    status_proc = larch_proc.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voting",
            "voter-status-block",
            str(state.voter_1_path),
            state.voter_1_tool,
            state.voter_1_status,
            state.voter_1_parse_rate_status,
            str(state.voter_2_path),
            state.voter_2_tool,
            state.voter_2_status,
            state.voter_2_parse_rate_status,
            str(state.voter_3_path),
            state.voter_3_tool,
            state.voter_3_status,
            state.voter_3_parse_rate_status,
            str(voter_paths_file),
        ],
        cwd=str(_REPO_ROOT),
    )
    print(status_proc.stdout, end="")
    _emit(key="DISPATCH_OK", value=dispatch_ok)


def dispatch_voters(argv: Sequence[str]) -> int:  # noqa: C901,PLR0912,PLR0915,RUF100
    parser = argparse.ArgumentParser(prog="cli.py plan-review voter-dispatch")
    parser.add_argument("--ballot-file", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--codex-available", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--cursor-available", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--scope-anchor-file", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round-num", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    design = _validate_tmpdir(parser=parser, value=ns.design_tmpdir, create=True)
    if ns.round_num <= 0:
        parser.exit(2, "cli.py plan-review voter-dispatch: --round-num must be positive\n")
    if ns.codex_available not in {"true", "false"} or ns.cursor_available not in {"true", "false"}:
        parser.exit(2, "cli.py plan-review voter-dispatch: availability flags must be true or false\n")
    round_dir = design / "plan-review" / f"round-{ns.round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    panel_env = build_panel_dispatch_env(
        artifact_dir=round_dir,
        site="design Step 3",
        round_num=ns.round_num,
        round_dir=round_dir,
        phase="plan-review-voters",
    )
    ballot = Path(ns.ballot_file)
    policies = list(external_defaults.voter_policies("design.plan_voters"))
    policies_by_slot = {policy.slot_name: policy for policy in policies}
    scope_anchor = ns.scope_anchor_file or str(design / "plan-review-scope-anchor.txt")
    if scope_anchor and not Path(scope_anchor).is_file():
        scope_anchor = ""
    calibration_stats_file = _fresh_calibration_stats_file(design=design)
    codex_present = ns.codex_available == "true"
    cursor_present = ns.cursor_available == "true"

    if not codex_present and not cursor_present:
        launched_policy = policies_by_slot["voter-1"]
        try:
            prompt_files, payload_files = _build_plan_voter_prompt_files(
                design=design,
                ballot=ballot,
                policies=[launched_policy],
                codex_present=codex_present,
                cursor_present=cursor_present,
                scope_anchor=scope_anchor,
                calibration_stats_file=calibration_stats_file,
            )
        except RuntimeError:
            return 2
        claude_prompt = Path(prompt_files[launched_policy.slot_name]["claude"])
        voter_1_path = design / launched_policy.output_name
        payload_bytes = str(payload_files[launched_policy.slot_name].get("claude", 0))
        rc = _launch_claude_voter(
            design=design,
            prompt_file=claude_prompt,
            output=voter_1_path,
            env={**panel_env, "LARCH_PANEL_SLOT": "voter-1", "LARCH_PANEL_PRIMARY_TOOL": "claude", "LARCH_PANEL_PAYLOAD_BYTES": payload_bytes},
        )
        voter_1_retried = "false"
        if _voter_needs_retry(rc=rc, output=voter_1_path):
            voter_1_retried = "true"
            rc = _launch_claude_voter(
                design=design,
                prompt_file=claude_prompt,
                output=voter_1_path,
                env={**panel_env, "LARCH_PANEL_SLOT": "voter-1", "LARCH_PANEL_PRIMARY_TOOL": "claude", "LARCH_PANEL_PAYLOAD_BYTES": payload_bytes},
            )
        voter_1_done_rc = _read_done_exit_code(voter_1_path.with_name(voter_1_path.name + ".done"))
        voter_1_status = "launched" if rc in {0, 99} and _file_nonempty(voter_1_path) and voter_1_done_rc == "0" else "failed"
        voter_1_parse = "SKIPPED" if voter_1_status == "failed" else _parse_rate_retry(
            design=design,
            ballot=ballot,
            slot="1",
            voter_file=voter_1_path,
            voter_tool="claude",
            prompt_file=claude_prompt,
        )
        if voter_1_status != "failed" and voter_1_parse == "NOT_SUBSTANTIVE":
            voter_1_status = "failed"
        paths_file = design / "plan-review-voter-paths.txt"
        kept = [str(voter_1_path)] if voter_1_status != "failed" and _file_nonempty(voter_1_path) else []
        _ = paths_file.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
        print("DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1/3 effective judges produced substantive vote output.** quota hit")
        state = DispatchState(
            voter_1_path=voter_1_path,
            voter_2_path=design / policies_by_slot["voter-2"].output_name,
            voter_3_path=design / policies_by_slot["voter-3"].output_name,
            voter_1_tool="claude",
            voter_2_tool=policies_by_slot["voter-2"].default_label,
            voter_3_tool=policies_by_slot["voter-3"].default_label,
            voter_1_status=voter_1_status,
            voter_2_status="failed",
            voter_3_status="failed",
            voter_1_parse_rate_status=voter_1_parse,
            voter_2_parse_rate_status="not-run",
            voter_3_parse_rate_status="not-run",
        )
        _emit_final_kvs(state=state, voter_paths_file=paths_file, dispatch_ok="true" if voter_1_status == "launched" else "false")
        _emit(key="VOTER_1_RETRIED", value=voter_1_retried)
        return 0

    launched_policies = policies
    try:
        prompt_files, payload_files = _build_plan_voter_prompt_files(
            design=design,
            ballot=ballot,
            policies=launched_policies,
            codex_present=codex_present,
            cursor_present=cursor_present,
            scope_anchor=scope_anchor,
            calibration_stats_file=calibration_stats_file,
        )
    except RuntimeError:
        return 2
    manifest = _write_plan_voter_waterfall_manifest(
        design=design,
        policies=launched_policies,
        prompt_files=prompt_files,
        payload_files=payload_files,
    )
    wf_args = [
        sys.executable,
        str(_plugin_root() / "python" / "cli.py"),
        "agent",
        "dispatch-waterfall",
        "--slots-file",
        str(manifest),
        "--panel-artifact-dir",
        str(round_dir),
        "--codex-present",
        ns.codex_available,
        "--cursor-present",
        ns.cursor_available,
        "--mode",
        "description",
        "--model-role",
        "vote",
        "--site",
        "design Step 3",
        "--timeout",
        "1860",
        "--claude-read-tools-add-dir",
        str(design),
    ]
    wf = larch_proc.run(
        wf_args,
        cwd=str(_REPO_ROOT),
        env=panel_env,
    )
    waterfall_output = wf.stdout
    wf_kv = _parse_kv(waterfall_output)
    bindings = agent_waterfall.bind_manifest_slot_outputs(manifest_path=manifest, wf_kv=wf_kv)
    state = _state_from_bindings(
        design=design,
        policies=policies,
        bindings=bindings,
        launched_policies=launched_policies,
    )
    voter_1_done_rc = _read_done_exit_code(state.voter_1_path.with_name(state.voter_1_path.name + ".done"))
    voter_2_done_rc = _read_done_exit_code(state.voter_2_path.with_name(state.voter_2_path.name + ".done"))
    voter_3_done_rc = _read_done_exit_code(state.voter_3_path.with_name(state.voter_3_path.name + ".done"))
    if state.voter_1_status != "skipped" and not _file_nonempty(state.voter_1_path):
        state.voter_1_status = "failed"
    if state.voter_2_status != "skipped" and not _file_nonempty(state.voter_2_path):
        state.voter_2_status = "failed"
    if state.voter_3_status != "skipped" and not _file_nonempty(state.voter_3_path):
        state.voter_3_status = "failed"
    if state.voter_1_status != "skipped" and not (_file_nonempty(state.voter_1_path) and voter_1_done_rc == "0"):
        state.voter_1_status = "failed"
    if state.voter_2_status != "skipped" and not (_file_nonempty(state.voter_2_path) and voter_2_done_rc == "0"):
        state.voter_2_status = "failed"
    if state.voter_3_status != "skipped" and not (_file_nonempty(state.voter_3_path) and voter_3_done_rc == "0"):
        state.voter_3_status = "failed"

    def _prompt_for(slot_name: str, voter_tool: str) -> Path:
        policy = policies_by_slot[slot_name]
        base_tool = voting.normalize_voter_label_to_base_tool(voter_tool) or policy.primary_tool
        prompt_map = prompt_files.get(slot_name, {})
        return Path(prompt_map.get(base_tool) or next(iter(prompt_map.values())))

    if state.voter_1_status not in {"failed", "skipped"}:
        state.voter_1_parse_rate_status = _parse_rate_retry(
            design=design,
            ballot=ballot,
            slot="1",
            voter_file=state.voter_1_path,
            voter_tool=state.voter_1_tool,
            prompt_file=_prompt_for("voter-1", state.voter_1_tool),
        )
    if state.voter_2_status not in {"failed", "skipped"}:
        state.voter_2_parse_rate_status = _parse_rate_retry(
            design=design,
            ballot=ballot,
            slot="2",
            voter_file=state.voter_2_path,
            voter_tool=state.voter_2_tool,
            prompt_file=_prompt_for("voter-2", state.voter_2_tool),
        )
    if state.voter_3_status not in {"failed", "skipped"}:
        state.voter_3_parse_rate_status = _parse_rate_retry(
            design=design,
            ballot=ballot,
            slot="3",
            voter_file=state.voter_3_path,
            voter_tool=state.voter_3_tool,
            prompt_file=_prompt_for("voter-3", state.voter_3_tool),
        )
    if state.voter_1_status != "failed" and state.voter_1_parse_rate_status == "NOT_SUBSTANTIVE":
        state.voter_1_status = "failed"
    if state.voter_2_status != "failed" and state.voter_2_parse_rate_status == "NOT_SUBSTANTIVE":
        state.voter_2_status = "failed"
    if state.voter_3_status != "failed" and state.voter_3_parse_rate_status == "NOT_SUBSTANTIVE":
        state.voter_3_status = "failed"

    effective_proc = larch_proc.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voting",
            "effective-judges",
            f"{state.voter_1_status}\t{state.voter_1_path}\t{state.voter_1_parse_rate_status}",
            f"{state.voter_2_status}\t{state.voter_2_path}\t{state.voter_2_parse_rate_status}",
            f"{state.voter_3_status}\t{state.voter_3_path}\t{state.voter_3_parse_rate_status}",
        ],
        cwd=str(_REPO_ROOT),
    )
    effective = int(effective_proc.stdout.strip() or "0") if effective_proc.returncode == 0 else 0
    if effective < _PLAN_VOTER_PANEL_SIZE:
        warn_proc = larch_proc.run(
            [
                sys.executable,
                str(_plugin_root() / "python" / "cli.py"),
                "voting",
                "degraded-warning",
                str(effective),
                str(_PLAN_VOTER_PANEL_SIZE),
                "",
            ],
            cwd=str(_REPO_ROOT),
        )
        if warn_proc.stdout.strip():
            print(warn_proc.stdout.strip())
        _emit(key="DEGRADED_PANEL", value="1")

    paths_file = design / "plan-review-voter-paths.txt"
    kept: list[str] = []
    for path_value, status in (
        (state.voter_1_path, state.voter_1_status),
        (state.voter_2_path, state.voter_2_status),
        (state.voter_3_path, state.voter_3_status),
    ):
        if status != "failed" and _file_nonempty(path_value):
            kept.append(str(path_value))
    _ = paths_file.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
    dispatch_ok = "false" if effective == 0 or wf_kv.get("DISPATCH_OK") == "false" else "true"
    _emit_final_kvs(state=state, voter_paths_file=paths_file, dispatch_ok=dispatch_ok)
    _emit(key="VOTER_1_RETRIED", value="false")
    return 0 if dispatch_ok == "true" else 1

def dispatch_panel_main(argv: list[str] | None = None) -> int:
    return dispatch_panel(argv or [])


def dispatch_voters_main(argv: list[str] | None = None) -> int:
    return dispatch_voters(argv or [])
