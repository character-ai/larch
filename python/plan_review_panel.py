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
from pathlib import Path
from collections.abc import Sequence
from typing import cast

import findings_ledger
import larch_io
import redact
import run_logs
from session_env import validate_design_tmpdir

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ARCHETYPES = ("arch", "innovation", "pragmatic", "requirements")
_DISPATCH_LABEL = "plan-review voter-dispatch"
_PLAN_VOTER_PANEL_SIZE = 3
_SLOT_LABEL_MAX_LEN = 200
_GENERIC_CODEX_PLAN_REVIEW_ROLE = (
    "You are a senior code reviewer for this project. Review code, plans, or conflict resolutions across "
    "five focus areas: code quality, risk/integration, correctness, architecture, and security."
)
# launch-claude-review is spawned via PATH `python3`, not sys.executable, to match
# the legacy dispatch-plan-voters.sh `python3 cli.py ...` contract and the panel
# test harness's python3-agent stub that short-circuits the claude launch. In
# production python3 resolves to the same interpreter the larch wrapper runs.
_AGENT_LAUNCH_PYTHON = "python3"


def _static_slot_rows(
    *,
    design: Path,
    round_dir: Path,
    round_num: int,
    codex_present: str,
    cursor_present: str,
    plan_file: str,
    feature_file: str,
) -> list[dict[str, object]]:
    _ = cursor_present
    rows: list[dict[str, object]] = []
    codex_slots = codex_present == "true"
    cli = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "render", "plan-review"]
    for archetype in _ARCHETYPES:
        prompt_path = design / f"render-plan-cursor-{archetype}.prompt"
        proc = subprocess.run(
            [
                *cli,
                "--archetype",
                archetype,
                "--vendor",
                "cursor",
                "--plan-file",
                plan_file,
                "--design-tmpdir",
                str(design),
                "--feature-file",
                feature_file,
                "--findings-ledger-file",
                str(findings_ledger.ledger_path(design)),
            ],
            cwd=str(_REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        prompt = proc.stdout if proc.returncode == 0 else ""
        rows.append(
            _slot_row(
                tool="cursor", slot=f"cursor-plan-{archetype}", focus=archetype, output=round_dir / f"cursor-plan-{archetype}-output.txt", prompt_file=prompt_path, prompt=prompt,
            )
        )
        if codex_slots:
            codex_prompt_path = design / f"render-plan-codex-{archetype}.prompt"
            proc = subprocess.run(
                [
                    *cli,
                    "--archetype",
                    archetype,
                    "--vendor",
                    "codex",
                    "--plan-file",
                    plan_file,
                    "--design-tmpdir",
                    str(design),
                    "--feature-file",
                    feature_file,
                    "--findings-ledger-file",
                    str(findings_ledger.ledger_path(design)),
                ],
                cwd=str(_REPO_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            codex_prompt = proc.stdout if proc.returncode == 0 else ""
            rows.append(
                _slot_row(
                    tool="codex", slot=f"codex-plan-{archetype}", focus=archetype, output=round_dir / f"codex-primary-plan-{archetype}-output.txt", prompt_file=codex_prompt_path, prompt=codex_prompt,
                )
            )
    generic = _generic_plan_codex_row(
        design=design,
        round_dir=round_dir,
        round_num=round_num,
        plan_file=plan_file,
        feature_file=feature_file,
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
) -> dict[str, object] | None:
    if round_num not in {1, 2}:
        return None
    body_file = round_dir / "render-plan-codex-generic.body"
    _ = body_file.write_text(_GENERIC_CODEX_PLAN_REVIEW_ROLE + "\n", encoding="utf-8")
    prompt_path = round_dir / "render-plan-codex-generic.prompt"
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
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    row = _slot_row(
        tool="codex",
        slot="codex-plan-generic",
        focus="code-quality",
        output=round_dir / "codex-plan-generic-output.txt",
        prompt_file=prompt_path,
        prompt=proc.stdout if proc.returncode == 0 else "",
    )
    row["model_role"] = "default"
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


def _slot_row(*, tool: str, slot: str, focus: str, output: Path, prompt_file: Path, prompt: str = "") -> dict[str, object]:
    # Write the rendered prompt (or the one-line fallback when the render was empty or
    # non-zero) to its own file and reference it via "prompt_file", matching the voter
    # manifest pattern below. agent_waterfall._load_slots accepts only "agent" or
    # "prompt_file"; an inline "prompt" key is ignored, so the consumer rejected the
    # first row and the panel launched zero reviewers (#4765).
    prompt_text = prompt or f"Review the design plan with a {focus} lens."
    _ = prompt_file.write_text(prompt_text, encoding="utf-8")
    return {
        "tool": tool,
        "slot": slot,
        "name": slot,
        "focus_area": focus,
        "prompt_file": str(prompt_file),
        "output": str(output),
    }


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
) -> tuple[list[dict[str, object]], list[tuple[str, str, int]]]:
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
        rows.append(_slot_row(tool=tool, slot=slot, focus=focus, output=round_dir / f"{slot}.txt", prompt_file=round_dir / f"{slot}.prompt", prompt=rendered))
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
    if prune_round_num not in {3, 4}:
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
    ns = parser.parse_args(list(argv))
    design = _validate_tmpdir(parser=parser, value=ns.design_tmpdir)
    round_dir = design / "plan-review" / f"round-{ns.round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = _static_slot_rows(
        design=design, round_dir=round_dir,
        round_num=ns.round_num,
        codex_present=ns.codex_present,
        cursor_present=ns.cursor_present,
        plan_file=ns.plan_file,
        feature_file=ns.feature_file,
    )
    static_count = len(rows)
    dynamic = _load_dynamic_rows(design)
    dynamic_rows, dynamic_failures = _dynamic_slot_rows(
        design=design, round_dir=round_dir, dynamic=dynamic,
        plan_file=ns.plan_file,
        feature_file=ns.feature_file,
    )
    rows.extend(dynamic_rows)
    manifest = design / "plan-review-slots.ndjson"
    _write_manifest(rows=rows, path=manifest)
    manifest, prune_kv = _filter_pruned(design=design, manifest=manifest, prune_round_num=ns.prune_round_num or ns.round_num)
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
    proc = subprocess.run(
        [
            *cmd,
            "--slots-file",
            str(manifest),
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
            "review",
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
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


def _make_voter_prompt(*, design: Path, ballot: Path, tool: str, scope_anchor: str = "") -> Path:
    prompt_file = design / f"{tool}-plan-voter-prompt.txt"
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
    ]
    if scope_anchor:
        args.extend(["--scope-anchor-file", scope_anchor])
    proc = subprocess.run(args, cwd=str(_REPO_ROOT), text=True, capture_output=True, check=False)
    if proc.returncode != 0 or "Read the ballot from this path" not in proc.stdout:
        raise RuntimeError(f"render voter failed for {tool}")
    _ = prompt_file.write_text(proc.stdout, encoding="utf-8")
    return prompt_file


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
    return proc.stdout.strip() or "SKIPPED"


def dispatch_voters(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review voter-dispatch")
    parser.add_argument("--ballot-file", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--codex-available", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--cursor-available", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--scope-anchor-file", default="")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    design = _validate_tmpdir(parser=parser, value=ns.design_tmpdir, create=True)
    ballot = Path(ns.ballot_file)
    scope_anchor = ns.scope_anchor_file or str(design / "plan-review-scope-anchor.txt")
    if scope_anchor and not Path(scope_anchor).is_file():
        scope_anchor = ""

    if ns.codex_available == "false" and ns.cursor_available == "false":
        # Render all voter prompt templates up front, matching the legacy
        # dispatch-plan-voters.sh which rendered claude/codex/cursor prompts
        # unconditionally; availability gates only the launch, not the render.
        claude_prompt = _make_voter_prompt(design=design, ballot=ballot, tool="claude", scope_anchor=scope_anchor)
        _ = _make_voter_prompt(design=design, ballot=ballot, tool="codex", scope_anchor=scope_anchor)
        _ = _make_voter_prompt(design=design, ballot=ballot, tool="cursor", scope_anchor=scope_anchor)
        voter_1_path = design / "claude-vote-output.txt"
        rc = subprocess.run(
            [
                _AGENT_LAUNCH_PYTHON,
                str(_plugin_root() / "python" / "cli.py"),
                "agent",
                "launch-claude-review",
                "--output",
                str(voter_1_path),
                "--prompt-file",
                str(claude_prompt),
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
        ).returncode
        voter_1_status = "launched" if rc in {0, 99} and voter_1_path.is_file() and voter_1_path.stat().st_size > 0 else "failed"
        voter_1_parse = "SKIPPED" if voter_1_status == "failed" else _parse_rate_retry(design=design, ballot=ballot, slot="1", voter_file=voter_1_path, voter_tool="claude", prompt_file=claude_prompt)
        if voter_1_status != "failed" and voter_1_parse == "NOT_SUBSTANTIVE":
            voter_1_status = "failed"
        paths_file = design / "plan-review-voter-paths.txt"
        kept = [str(voter_1_path)] if voter_1_status != "failed" else []
        _ = paths_file.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
        print("DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1/3 effective judges produced substantive vote output.** quota hit")
        _emit(key="VOTER_1_PATH", value=voter_1_path)
        _emit(key="VOTER_1_TOOL", value="claude")
        _emit(key="VOTER_1_STATUS", value=voter_1_status)
        _emit(key="VOTER_1_PARSE_RATE_STATUS", value=voter_1_parse)
        _emit(key="VOTER_2_PATH", value=design / "codex-vote-output.txt")
        _emit(key="VOTER_3_PATH", value=design / "cursor-vote-output.txt")
        _emit(key="VOTER_PATHS_FILE", value=paths_file)
        _emit(key="VOTER_2_TOOL", value="codex")
        _emit(key="VOTER_3_TOOL", value="cursor")
        _emit(key="VOTER_2_STATUS", value="failed")
        _emit(key="VOTER_3_STATUS", value="failed")
        _emit(key="VOTER_2_PARSE_RATE_STATUS", value="not-run")
        _emit(key="VOTER_3_PARSE_RATE_STATUS", value="not-run")
        dispatch_ok = "true" if voter_1_status == "launched" else "false"
        _emit(key="DISPATCH_OK", value=dispatch_ok)
        # A degraded panel (the sole claude voter produced no substantive votes)
        # is surfaced via DISPATCH_OK, not a dispatch failure: the dispatch ran,
        # so exit 0 (matching new main and the full-panel path; the loop handles
        # the degraded result downstream via tally, not the dispatch exit code).
        return 0

    try:
        claude_prompt = _make_voter_prompt(design=design, ballot=ballot, tool="claude", scope_anchor=scope_anchor)
        codex_prompt = _make_voter_prompt(design=design, ballot=ballot, tool="codex", scope_anchor=scope_anchor)
        cursor_prompt = _make_voter_prompt(design=design, ballot=ballot, tool="cursor", scope_anchor=scope_anchor)
    except RuntimeError:
        return 2

    voter_1_path = design / "claude-vote-output.txt"
    voter_2_path = design / "codex-vote-output.txt"
    voter_3_path = design / "cursor-vote-output.txt"

    stderr_file = Path(f"{voter_1_path}.launcher-stderr").open("w", encoding="utf-8")  # noqa: SIM115  # pylint: disable=consider-using-with
    claude_proc = subprocess.Popen(  # pylint: disable=consider-using-with
        [
            _AGENT_LAUNCH_PYTHON,
            str(_plugin_root() / "python" / "cli.py"),
            "agent",
            "launch-claude-review",
            "--output",
            str(voter_1_path),
            "--prompt-file",
            str(claude_prompt),
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
        stdout=subprocess.DEVNULL,
        stderr=stderr_file,
    )

    manifest = design / "plan-voter-slots.ndjson"
    manifest_lines: list[str] = []
    if ns.codex_available == "true":
        manifest_lines.append(
            json.dumps({"slot": "voter-2", "tool": "codex", "output": str(voter_2_path), "prompt_file": str(codex_prompt)})
        )
    if ns.cursor_available == "true":
        manifest_lines.append(
            json.dumps({"slot": "voter-3", "tool": "cursor", "output": str(voter_3_path), "prompt_file": str(cursor_prompt)})
        )
    _ = manifest.write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")

    waterfall_output = ""
    if manifest_lines:
        wf = subprocess.run(
            [
                sys.executable,
                str(_plugin_root() / "python" / "cli.py"),
                "agent",
                "dispatch-waterfall",
                "--slots-file",
                str(manifest),
                "--codex-present",
                ns.codex_available,
                "--cursor-present",
                ns.cursor_available,
                "--mode",
                "description",
                "--model-role",
                "vote",
                "--no-fallback",
                "--site",
                "design Step 3",
                "--timeout",
                "1860",
            ],
            cwd=str(_REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        waterfall_output = wf.stdout

    voter1_rc = claude_proc.wait()
    stderr_file.close()
    done_path = Path(f"{voter_1_path}.done")
    if not done_path.is_file():
        _ = done_path.write_text(f"{voter1_rc}\n", encoding="utf-8")

    wf_kv = _parse_kv(waterfall_output)
    if manifest_lines:
        import agent_waterfall  # noqa: PLC0415

        bindings = agent_waterfall.bind_manifest_slot_outputs(manifest_path=manifest, wf_kv=wf_kv)
        voter_2_binding = bindings.get("voter-2", agent_waterfall.SlotOutputBinding())
        voter_3_binding = bindings.get("voter-3", agent_waterfall.SlotOutputBinding())
        if voter_2_binding.path:
            voter_2_path = Path(voter_2_binding.path)
        if voter_3_binding.path:
            voter_3_path = Path(voter_3_binding.path)

    voter_1_status = "launched" if (voter1_rc in {0, 99} and voter_1_path.is_file() and voter_1_path.stat().st_size > 0) else "failed"
    voter_2_status = "failed" if ns.codex_available != "true" else ("launched" if voter_2_path.is_file() and voter_2_path.stat().st_size > 0 else "failed")
    voter_3_status = "failed" if ns.cursor_available != "true" else ("launched" if voter_3_path.is_file() and voter_3_path.stat().st_size > 0 else "failed")

    voter_1_parse = "SKIPPED" if voter_1_status == "failed" else _parse_rate_retry(design=design, ballot=ballot, slot="1", voter_file=voter_1_path, voter_tool="claude", prompt_file=claude_prompt)
    voter_2_parse = "SKIPPED" if voter_2_status == "failed" else _parse_rate_retry(design=design, ballot=ballot, slot="2", voter_file=voter_2_path, voter_tool="codex", prompt_file=codex_prompt)
    voter_3_parse = "SKIPPED" if voter_3_status == "failed" else _parse_rate_retry(design=design, ballot=ballot, slot="3", voter_file=voter_3_path, voter_tool="cursor", prompt_file=cursor_prompt)

    if voter_1_status != "failed" and voter_1_parse == "NOT_SUBSTANTIVE":
        voter_1_status = "failed"
    if voter_2_status != "failed" and voter_2_parse == "NOT_SUBSTANTIVE":
        voter_2_status = "failed"
    if voter_3_status != "failed" and voter_3_parse == "NOT_SUBSTANTIVE":
        voter_3_status = "failed"

    effective_proc = subprocess.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voting",
            "effective-judges",
            f"{voter_1_status}\t{voter_1_path}\t{voter_1_parse}",
            f"{voter_2_status}\t{voter_2_path}\t{voter_2_parse}",
            f"{voter_3_status}\t{voter_3_path}\t{voter_3_parse}",
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    effective = int(effective_proc.stdout.strip() or "0") if effective_proc.returncode == 0 else 0
    if effective < _PLAN_VOTER_PANEL_SIZE:
        warn_proc = subprocess.run(
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
            text=True,
            capture_output=True,
            check=False,
        )
        if warn_proc.stdout.strip():
            print(warn_proc.stdout.strip())

    paths_file = design / "plan-review-voter-paths.txt"
    kept: list[str] = []
    for path, status in ((voter_1_path, voter_1_status), (voter_2_path, voter_2_status), (voter_3_path, voter_3_status)):
        if status != "failed" and path.is_file() and path.stat().st_size > 0:
            kept.append(str(path))
    _ = paths_file.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")

    status_proc = subprocess.run(
        [
            sys.executable,
            str(_plugin_root() / "python" / "cli.py"),
            "voting",
            "voter-status-block",
            str(voter_1_path),
            "claude",
            voter_1_status,
            voter_1_parse,
            str(voter_2_path),
            "codex",
            voter_2_status,
            voter_2_parse,
            str(voter_3_path),
            "cursor",
            voter_3_status,
            voter_3_parse,
            str(paths_file),
        ],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    print(status_proc.stdout, end="")

    dispatch_ok = "false" if voter_1_status == "failed" else "true"
    _emit(key="DISPATCH_OK", value=dispatch_ok)
    return 0 if dispatch_ok == "true" else 1


def dispatch_panel_main(argv: list[str] | None = None) -> int:
    return dispatch_panel(argv or [])


def dispatch_voters_main(argv: list[str] | None = None) -> int:
    return dispatch_voters(argv or [])
