"""Design decomposition helpers ported from shell."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict, deque
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import larch_io
import logging_util
import proc
import retry
import session_env

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT
DECOMPOSE_ARCHETYPES = ("decomposition-specialist", "dependency-analyst", "scope-minimalist", "risk-isolation")
RECOMMENDATION_RE = re.compile(r"^[ \t]*## Recommendation", re.MULTILINE)
PROMPT_PREFIX_LINE_MAX = 8


class UsageError(ValueError):
    """CLI usage error."""


def _err(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _fail(message: str) -> None:
    raise UsageError(message)


def _emit_kv(*, key: str, value: object) -> None:
    text = ("true" if value else "false") if isinstance(value, bool) else str(value)
    logging_util.emit_kv(key, text)


def _validate_design_tmpdir(value: str) -> Path:
    ok, message = session_env.validate_design_tmpdir(value)
    if not ok:
        _fail(message)
    return Path(value).resolve()


def _positive_int(*, value: str, flag: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        _fail(f"{flag} must be a positive integer")
    return int(value)


def _binary_bool(*, value: str, binary: str) -> bool:
    if value in {"true", "false"}:
        return value == "true"
    return shutil.which(binary) is not None


def _neutralize_markdown_h3_line_starts(text: str) -> str:
    return re.sub(r"(?m)^###", "\u200b###", text)


def _prepare_parse_dependency(*, dep: str, index_by_num: dict[int, int]) -> list[int] | None:
    match = re.search(r"blocked-by\b(.*)$", dep, re.IGNORECASE)
    if not match:
        return []
    remainder = match.group(1)
    segments = [seg.strip() for seg in re.split(r",|\s+and\b", remainder, flags=re.IGNORECASE)]
    segments = [seg for seg in segments if seg]
    if not segments:
        return None
    blockers: list[int] = []
    seen: set[int] = set()
    for segment in segments:
        sm = re.fullmatch(r"Piece\s+(\d+)", segment, re.IGNORECASE)
        if not sm:
            return None
        blocker = int(sm.group(1))
        if blocker in seen:
            continue
        seen.add(blocker)
        if blocker not in index_by_num:
            return None
        blockers.append(blocker)
    return blockers


def prepare_partition_issues(
    *,
    design_tmpdir: Path,
    partition_file: Path,
    issue_number: str = "",
) -> tuple[str, str]:
    if not partition_file.is_file():
        raise UsageError("prepare: partition file not found")
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    out_input = dec / "partition-input.txt"
    out_deps = dec / "partition-deps.tsv"
    for path in (out_input, out_deps):
        path.unlink(missing_ok=True)

    text = partition_file.read_text(encoding="utf-8")
    if "## Pieces" not in text:
        return "invalid-partition-file", ""
    piece_rx = re.compile(r"(?m)^###\s+Piece\s+(\d+)\s*:\s*([^\n]+)$")
    pieces: list[tuple[int, str, str]] = []
    matches = list(piece_rx.finditer(text))
    for idx, match in enumerate(matches):
        pnum = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pieces.append((pnum, title, text[start:end].strip()))
    if not pieces:
        return "no-pieces", ""
    pieces.sort(key=lambda item: item[0])
    index_by_num: dict[int, int] = {pnum: i for i, (pnum, _title, _body) in enumerate(pieces)}

    edges: list[tuple[int, int]] = []
    dep_lines: list[str] = []
    for i, (_pnum, _title, body) in enumerate(pieces):
        dep = "none"
        for line in body.splitlines():
            if line.strip().lower().startswith("- dependencies:"):
                dep = line.split(":", 1)[1].strip()
                break
        dep_lines.append(dep)
        blockers = _prepare_parse_dependency(dep=dep, index_by_num=index_by_num)
        if blockers is None:
            return "bad-dependency-ref", ""
        edges.extend((index_by_num[blocker], i) for blocker in blockers)

    adj: dict[int, list[int]] = defaultdict(list)
    indeg = [0] * len(pieces)
    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1
    q: deque[int] = deque(i for i, degree in enumerate(indeg) if degree == 0)
    seen_count = 0
    while q:
        u = q.popleft()
        seen_count += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if seen_count != len(pieces):
        witness = "; ".join(f"Piece {pieces[a][0]}→Piece {pieces[b][0]}" for a, b in edges) or "(edges unavailable)"
        return "cycle-detected", witness

    feat_path = design_tmpdir / "feature-description.txt"
    feat = feat_path.read_text(encoding="utf-8") if feat_path.is_file() else ""
    feat = _neutralize_markdown_h3_line_starts(feat)
    orig = f"#{issue_number}" if issue_number.isdigit() else "(original issue — set ISSUE_NUMBER in session)"
    lines: list[str] = []
    n = len(pieces)
    for i, (pnum, title, body) in enumerate(pieces):
        scope = ""
        for line in body.splitlines():
            if line.strip().lower().startswith("- scope:"):
                scope = line.split(":", 1)[1].strip()
                break
        lines.append(f"### {title}\n")
        body_text = (
            f"Partition piece {pnum} of {n} split from {orig}.\n\n"
            f"**Scope**: {scope or '(see parent partition file)'}\n\n"
            f"**Dependencies (from panel)**: {dep_lines[i]}\n\n"
            "```\n"
            "<!-- larch:plan:start -->\n"
            "## Plan\n\n"
            "(needs /design — operator runs `/design` on this issue after partition lands.)\n\n"
            "<!-- larch:plan:end -->\n"
            "```\n\n"
            f"**Original feature context (excerpt)**:\n\n{feat[:4000]}\n"
        )
        lines.append(_neutralize_markdown_h3_line_starts(body_text))
    out_input.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with out_deps.open("w", encoding="utf-8") as handle:
        for a, b in edges:
            _ = handle.write(f"{a + 1}\t{b + 1}\n")
    return "ok", ""


def annotate_partition_issues(*, design_tmpdir: Path, issue_stdout_file: Path) -> None:
    if not issue_stdout_file.is_file():
        raise UsageError("annotate: stdout capture missing")
    sent = design_tmpdir / ".decompose-issues-filed"
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    filed = dec / "partition-filed.md"
    text = issue_stdout_file.read_text(encoding="utf-8")

    def kv(pattern: str) -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1) if m else ""

    created = kv(r"^ISSUES_CREATED=([0-9]+)\s*$") or "0"
    failed = kv(r"^ISSUES_FAILED=([0-9]+)\s*$") or "0"
    try:
        failed_n = int(failed)
    except ValueError:
        failed_n = 0
    urls: dict[int, str] = {}
    for m in re.finditer(r"^ISSUE_([0-9]+)_URL=(.+)\s*$", text, re.MULTILINE):
        urls[int(m.group(1))] = m.group(2).strip()

    if sent.is_file():
        prev = sent.read_text(encoding="utf-8")
        if prev.strip() and filed.is_file() and failed_n == 0:
            ok = all(f"PARTITION_FILE_MAP\t{i}\t{url}" in prev for i, url in sorted(urls.items()))
            try:
                created_n = int(created)
            except ValueError:
                created_n = 0
            if ok and created_n == len(urls):
                return

    lines = ["# Partition filing record", "", f"- **ISSUES_CREATED**: {created}", f"- **ISSUES_FAILED**: {failed}", ""]
    for i in sorted(urls):
        lines.extend([f"## Piece {i}", f"- **Filed URL**: {urls[i]}", ""])
    filed.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failed_n == 0:
        with sent.open("w", encoding="utf-8") as handle:
            for i in sorted(urls):
                _ = handle.write(f"PARTITION_FILE_MAP\t{i}\t{urls[i]}\n")
    else:
        sent.unlink(missing_ok=True)


def _append_failure(design_tmpdir: Path, *, site: str, tool: str, exit_code: int, output_file: Path) -> None:
    cli = PLUGIN_ROOT / "python" / "cli.py"
    subprocess.run(
        [  # noqa: S607
            "python3",
            str(cli),
            "run-log",
            "append-failure",
            "--log",
            str(design_tmpdir / "execution-issues.md"),
            "--site",
            site,
            "--tool",
            tool,
            "--exit-code",
            str(exit_code),
            "--category",
            "External Reviewer Issues",
            "--output-file",
            str(output_file),
            "--redact",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_command(argv: Sequence[str], *, stdin: Path | None = None, stdout: Path | None = None) -> tuple[int, str]:
    with (stdin.open("rb") if stdin else Path(os.devnull).open("rb")) as inp:
        if stdout is None:
            result = subprocess.run(argv, input=inp.read() if stdin else None, check=False, capture_output=True)
            out = result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace")
            return result.returncode, out
        with stdout.open("wb") as out_handle:
            result = subprocess.run(argv, stdin=inp if stdin else None, stdout=out_handle, stderr=subprocess.PIPE, check=False)
            return result.returncode, result.stderr.decode("utf-8", errors="replace")


def close_original_issue(*, design_tmpdir: Path, original_issue: str, repo: str) -> str:
    if (design_tmpdir / ".decompose-original-closed").is_file():
        return "ok"
    dec = design_tmpdir / "decompose"
    filed = dec / "partition-filed.md"
    if not filed.is_file():
        raise UsageError("close-original: missing partition-filed.md (run annotate first)")
    body = dec / "close-comment-draft.md"
    comment_sent = dec / ".decompose-close-comment-posted"
    summary_lines = ["This issue is **obviated by a partition** into follow-up work.", "", "## New pieces", ""]
    summary_lines.extend(
        line
        for line in filed.read_text(encoding="utf-8", errors="replace").splitlines()
        if re.match(r"^## Piece ", line) or re.match(r"^-\s\*\*Filed URL\*\*", line)
    )
    summary_lines.extend(["", "## Blocked-by chain", "", "See intra-batch dependency edges filed via /larch:issue (partition-deps.tsv).", ""])
    body.write_text("\n".join(summary_lines), encoding="utf-8")

    redacted = dec / "close-comment.redacted.md"
    redact_env = os.environ.get("DECOMPOSE_REDACT_SH", "").strip()
    redact_cmd = redact_env.split() if redact_env else ["python3", str(PLUGIN_ROOT / "python" / "cli.py"), "redact", "secrets"]
    rc, _combined = _run_command(redact_cmd, stdin=body, stdout=redacted)
    if rc != 0:
        _append_failure(design_tmpdir, site="design decompose close-original", tool="redact secrets", exit_code=rc, output_file=body)
        return "failed"

    def run_gh(argv: list[str]) -> tuple[None, int, str]:
        result = proc.run(argv)
        return None, result.returncode, result.stdout + result.stderr

    if not comment_sent.is_file():
        result = retry.with_transient_retry(
            lambda: run_gh(["gh", "issue", "comment", original_issue, "--repo", repo, "--body-file", str(redacted)]),
        )
        if result.last_returncode != 0:
            _append_failure(design_tmpdir, site="design decompose close-original", tool="gh issue comment", exit_code=result.last_returncode, output_file=redacted)
            return "failed"
        comment_sent.touch()

    result = retry.with_transient_retry(lambda: run_gh(["gh", "issue", "close", original_issue, "--repo", repo]))
    if result.last_returncode != 0:
        _append_failure(design_tmpdir, site="design decompose close-original", tool="gh issue close", exit_code=result.last_returncode, output_file=redacted)
        return "failed"
    comment_sent.unlink(missing_ok=True)
    (design_tmpdir / ".decompose-original-closed").touch()
    return "ok"


def _read_text_or_empty(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _render_decompose_prompt(archetype: str, *, primary_input: Path, discussion_file: Path | None, out: Path) -> None:
    prompts = PLUGIN_ROOT / "skills" / "design" / "scripts" / "decompose-prompts"
    arch_file = prompts / f"{archetype}.txt"
    common_tail = prompts / "_common-tail.txt"
    if not arch_file.is_file():
        raise UsageError(f"missing archetype template: {arch_file}")
    if not common_tail.is_file():
        raise UsageError(f"missing common tail: {common_tail}")
    primary = _read_text_or_empty(primary_input).strip() or "(empty primary input file)"
    disc_body = "(none — discussion-round1 artifact not passed or absent.)"
    if discussion_file is not None:
        disc_body = _read_text_or_empty(discussion_file).strip() or "(discussion path not readable)"
    full = arch_file.read_text(encoding="utf-8").replace("{COMMON_TAIL}", common_tail.read_text(encoding="utf-8"))
    full = full.replace("{PLAN_OR_FEATURE_BLOCK}", f"## Primary input\n\n{primary}\n\n")
    full = full.replace("{DISCUSSION_BLOCK}", f"## Discussion round 1\n\n{disc_body}\n\n")
    out.write_text(full, encoding="utf-8")


def _parse_kv_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _write_json_line(*, path: Path, row: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def dispatch_panel(
    *,
    design_tmpdir: Path,
    codex_present: bool,
    cursor_present: bool,
    mode: str,
    plan_file: Path | None = None,
    feature_file: Path | None = None,
    discussion_file: Path | None = None,
    timeout: int = 1800,
) -> None:
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    if mode == "plan":
        if plan_file is None or not plan_file.is_file():
            raise UsageError("plan mode requires --plan-file")
        primary_input = plan_file
    elif mode == "feature-only":
        if feature_file is None or not feature_file.is_file():
            raise UsageError("feature-only mode requires --feature-file")
        primary_input = feature_file
    else:
        raise UsageError("--mode must be plan or feature-only")
    feature = feature_file or (design_tmpdir / "feature-description.txt")
    if not feature.is_file():
        raise UsageError(f"feature-description not found (set --feature-file): {feature}")
    if discussion_file is not None and not discussion_file.is_file():
        raise UsageError(f"discussion file not found: {discussion_file}")

    manifest = dec / "decompose-slots.ndjson"
    panel_rows = dec / "panel-outputs.ndjson"
    manifest.write_text("", encoding="utf-8")
    panel_rows.write_text("", encoding="utf-8")

    if not codex_present and not cursor_present:
        generic_output = dec / "decomp-claude-generic-output.txt"
        generic_prompt = dec / "decomp-claude-generic.prompt"
        tail_src = dec / ".generic-tail-src.prompt"
        _render_decompose_prompt("decomposition-specialist", primary_input=primary_input, discussion_file=discussion_file, out=tail_src)
        parts: list[str] = ["You are a combined decomposition panel applying all four standard archetype lenses in a single pass. Address each lens below, then follow the shared output contract.", ""]
        prompts = PLUGIN_ROOT / "skills" / "design" / "scripts" / "decompose-prompts"
        for arch in DECOMPOSE_ARCHETYPES:
            lines = (prompts / f"{arch}.txt").read_text(encoding="utf-8").splitlines()
            prefix: list[str] = []
            for line in lines:
                prefix.append(line)
                if line == "Your focus:":
                    break
                if len(prefix) >= PROMPT_PREFIX_LINE_MAX:
                    break
            parts.extend(prefix)
            parts.append("")
        tail_lines = tail_src.read_text(encoding="utf-8").splitlines()[1:]
        parts.extend(tail_lines)
        generic_prompt.write_text("\n".join(parts) + "\n", encoding="utf-8")
        tail_src.unlink(missing_ok=True)
        env_launch = os.environ.get("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", "").strip()
        launch_cmd: list[str] = [env_launch] if env_launch else ["python3", str(PLUGIN_ROOT / "python" / "cli.py"), "agent", "launch-claude-review"]
        with (generic_output.with_suffix(generic_output.suffix + ".launch-stderr")).open("wb") as stderr_handle:
            launch: subprocess.CompletedProcess[bytes] = subprocess.run(
                [*launch_cmd, "--output", str(generic_output), "--prompt-file", str(generic_prompt), "--mode", "description", "--model", "claude-sonnet-4-6", "--timeout", str(timeout), "--timing-task-kind", "claude-decomp-generic", "--feature-file", str(feature)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=stderr_handle,
            )
        if not (generic_output.with_suffix(generic_output.suffix + ".done")).is_file():
            generic_output.with_suffix(generic_output.suffix + ".done").write_text(str(launch.returncode) + "\n", encoding="utf-8")
        status = "missing"
        if generic_output.is_file() and RECOMMENDATION_RE.search(generic_output.read_text(encoding="utf-8", errors="replace")):
            status = "ok"
        elif generic_output.is_file():
            status = "unparsed"
        _write_json_line(path=panel_rows, row={"archetype": "generic", "vendor": "claude", "output": str(generic_output), "status": status})
        dispatch_ok = launch.returncode == 0 and status == "ok"
        for k, v in {
            "DISPATCH_OK": dispatch_ok,
            "FALLBACK_COUNT": 0,
            "COMBINED_FALLBACK_COUNT": 0,
            "STATIC_DISPATCH_OK": dispatch_ok,
            "DYNAMIC_DISPATCH_OK": True,
        }.items():
            _emit_kv(key=k, value=v)
        degraded = not dispatch_ok
        _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
        _emit_kv(key="DEGRADED_PANEL", value=degraded)
        _emit_kv(key="PANEL_STATUS", value="panel-failed" if degraded else "ok")
        return

    for arch in DECOMPOSE_ARCHETYPES:
        if cursor_present:
            prompt_file = dec / f"render-decomp-cursor-{arch}.prompt"
            output = dec / f"decomp-cursor-{arch}-output.txt"
            _render_decompose_prompt(arch, primary_input=primary_input, discussion_file=discussion_file, out=prompt_file)
            _write_json_line(path=manifest, row={"slot": f"decomp-cursor-{arch}", "tool": "cursor", "output": str(output), "prompt_file": str(prompt_file)})
        if codex_present:
            prompt_file = dec / f"render-decomp-codex-{arch}.prompt"
            output = dec / f"decomp-codex-{arch}-output.txt"
            _render_decompose_prompt(arch, primary_input=primary_input, discussion_file=discussion_file, out=prompt_file)
            _write_json_line(path=manifest, row={"slot": f"decomp-codex-{arch}", "tool": "codex", "output": str(output), "prompt_file": str(prompt_file)})
    if "DECOMPOSE_PANEL_WATERFALL_SH" in os.environ:
        waterfall_argv: list[str] = [os.environ["DECOMPOSE_PANEL_WATERFALL_SH"]]
    else:
        waterfall_argv = [sys.executable, str(PLUGIN_ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]
    cmd: list[str] = [*waterfall_argv, "--slots-file", str(manifest), "--codex-present", str(codex_present).lower(), "--cursor-present", str(cursor_present).lower(), "--mode", "description", "--no-fallback", "--require-result-pattern", "^[[:space:]]*## Recommendation", "--feature-file", str(feature), "--timeout", str(timeout)]
    if mode == "plan" and plan_file is not None:
        cmd.extend(["--plan-file", str(plan_file)])
    wf: subprocess.CompletedProcess[str] = subprocess.run(cmd, check=False, capture_output=True, text=True)
    dispatch_out = wf.stdout
    if wf.returncode != 0:
        cap = dec / "decompose-waterfall-failure.log"
        cap.write_text(dispatch_out, encoding="utf-8")
        _append_failure(design_tmpdir, site="design Step 2b.5 decompose panel", tool="agent dispatch-waterfall", exit_code=wf.returncode, output_file=cap)
    kvs: dict[str, str] = _parse_kv_lines(dispatch_out)
    dispatch_ok = kvs.get("DISPATCH_OK", "")
    fallback_count = kvs.get("FALLBACK_COUNT", "0")
    combined_fallback_count = kvs.get("COMBINED_FALLBACK_COUNT", fallback_count or "0")
    static_dispatch_ok = kvs.get("STATIC_DISPATCH_OK", "true")
    all_outputs_file = kvs.get("ALL_OUTPUT_FILES_PATH", "")
    all_slots_dropped = kvs.get("ALL_SLOTS_DROPPED", "")
    manifest_rows: list[dict[str, object]] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row: object = json.loads(line)
        except json.JSONDecodeError:
            _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
            _emit_kv(key="DEGRADED_PANEL", value=True)
            _emit_kv(key="PANEL_STATUS", value="panel-failed")
            raise UsageError("malformed decompose-slots.ndjson") from None
        if not isinstance(row, dict):
            _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
            _emit_kv(key="DEGRADED_PANEL", value=True)
            _emit_kv(key="PANEL_STATUS", value="panel-failed")
            raise UsageError("malformed decompose-slots.ndjson") from None
        manifest_rows.append(cast("dict[str, object]", row))
    slot_count = len(manifest_rows)
    try:
        combined_fallback_n = int(combined_fallback_count)
    except ValueError:
        combined_fallback_n = 0
    degraded = static_dispatch_ok == "false" or combined_fallback_n > (slot_count // 2) or all_slots_dropped == "true"
    resolved_paths: list[str] = []
    if all_outputs_file and Path(all_outputs_file).is_file():
        resolved_paths = [line for line in Path(all_outputs_file).read_text(encoding="utf-8").splitlines() if line]
    if slot_count > 0 and len(resolved_paths) < slot_count:
        degraded = True
    usable = 0
    warned_missing_paths = False

    def match_resolved(manifest_out: str) -> str:
        base = Path(manifest_out).name
        for rp in resolved_paths:
            if rp == manifest_out or Path(rp).name == base:
                return rp
        return ""

    for row in manifest_rows:
        manifest_out = str(row.get("output", ""))
        slot = str(row.get("slot", ""))
        arch = slot.removeprefix("decomp-cursor-").removeprefix("decomp-codex-")
        vendor = str(row.get("tool", ""))
        if resolved_paths:
            out_resolved = match_resolved(manifest_out)
            if not out_resolved:
                _write_json_line(path=panel_rows, row={"archetype": arch, "vendor": vendor, "output": manifest_out, "status": "missing"})
                continue
        else:
            if all_slots_dropped == "true":
                continue
            if not warned_missing_paths:
                _err("decompose-panel-dispatch.sh: ALL_OUTPUT_FILES_PATH empty or missing; skipping manifest rows (no resolved paths)")
                warned_missing_paths = True
            continue
        status = "missing"
        path = Path(out_resolved)
        if path.is_file() and RECOMMENDATION_RE.search(path.read_text(encoding="utf-8", errors="replace")):
            status = "ok"
            usable += 1
        elif path.is_file():
            status = "unparsed"
        _write_json_line(path=panel_rows, row={"archetype": arch, "vendor": vendor, "output": out_resolved, "status": status})
    panel_status = "ok"
    if usable == 0:
        panel_status = "panel-failed"
    elif degraded:
        panel_status = "degraded"
    if wf.returncode != 0:
        degraded = True
        if usable > 0 and panel_status == "ok":
            panel_status = "degraded"
    for line in dispatch_out.splitlines():
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key == "WARN":
            _emit_kv(key="WARN", value=val)
        else:
            _emit_kv(key=key, value=val)
    _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
    _emit_kv(key="DEGRADED_PANEL", value=degraded)
    _emit_kv(key="PANEL_STATUS", value=panel_status)


def aggregate_partition(*, design_tmpdir: Path, panel_outputs_file: Path, codex_present: bool, cursor_present: bool, output: Path, timeout: int = 1800) -> str:
    if not panel_outputs_file.is_file():
        raise UsageError("--panel-outputs-file must exist")
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    combined = dec / "combined-proposals.txt"
    with combined.open("w", encoding="utf-8") as handle:
        for line in panel_outputs_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row: object = json.loads(line)
            except json.JSONDecodeError:
                _emit_kv(key="AGGREGATOR_STATUS", value="failed")
                raise UsageError("malformed panel-outputs.ndjson") from None
            if not isinstance(row, dict):
                _emit_kv(key="AGGREGATOR_STATUS", value="failed")
                raise UsageError("malformed panel-outputs.ndjson") from None
            row_obj = cast("dict[str, object]", row)
            outp = Path(str(row_obj.get("output", "")))
            _ = handle.write(f"\n## Panel output ({row_obj.get('archetype', '')} / {row_obj.get('vendor', '')})\n\n")
            if outp.is_file():
                _ = handle.write(outp.read_text(encoding="utf-8", errors="replace"))
            else:
                _ = handle.write(f"(missing file: {outp})\n")
            _ = handle.write("\n")
    feature = design_tmpdir / "feature-description.txt"
    if not feature.is_file():
        raise UsageError(f"missing {feature} for aggregator context")
    merge_prompt = dec / "aggregator-partition-merge.prompt"
    merge_prompt.write_text(
        "You are the decomposition aggregator. Below are eight independent partition proposals from external reviewers (four archetypes x two vendors).\n\n"
        "Task: produce **one** canonical merged partition that best satisfies the independently-mergeable constraint (acyclic blocker graph) while minimizing unnecessary coupling.\n\n"
        + combined.read_text(encoding="utf-8")
        + "\nOutput **only** Markdown matching this schema (first heading must be detectable):\n\n"
        "## Recommendation\nsplit | no-split\n\n"
        "## Pieces (only when Recommendation is split)\n\n"
        "### Piece 1: <short title>\n"
        "- Scope: <files / behaviors covered>\n"
        "- Dependencies: none | blocked-by Piece N[, Piece M ...]\n"
        "- Diff_lines estimate: <integer>\n"
        "- Why independently mergeable: <prose>\n\n"
        "### Piece 2: ...\n",
        encoding="utf-8",
    )
    agg_out = dec / "aggregator-raw-output.txt"
    slots = dec / "aggregator-slots.ndjson"
    slots.write_text(json.dumps({"slot": "decompose-aggregator", "tool": "codex", "output": str(agg_out), "prompt_file": str(merge_prompt)}, separators=(",", ":")) + "\n", encoding="utf-8")
    if "DECOMPOSE_AGGREGATE_WATERFALL_SH" in os.environ:
        waterfall_argv: list[str] = [os.environ["DECOMPOSE_AGGREGATE_WATERFALL_SH"]]
    else:
        waterfall_argv = [sys.executable, str(PLUGIN_ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]
    cmd: list[str] = [*waterfall_argv, "--slots-file", str(slots), "--codex-present", str(codex_present).lower(), "--cursor-present", str(cursor_present).lower(), "--mode", "description", "--feature-file", str(feature), "--require-result-pattern", "^[[:space:]]*## Recommendation", "--timeout", str(timeout)]
    result: subprocess.CompletedProcess[str] = subprocess.run(cmd, check=False, capture_output=True, text=True)
    kvs: dict[str, str] = _parse_kv_lines(result.stdout)
    final_out = agg_out
    paths_file = kvs.get("ALL_OUTPUT_FILES_PATH", "")
    if paths_file and Path(paths_file).is_file():
        first = Path(paths_file).read_text(encoding="utf-8").splitlines()
        if first:
            final_out = Path(first[0])
    if result.returncode == 0 and kvs.get("DISPATCH_OK", "false") == "true" and final_out.is_file() and RECOMMENDATION_RE.search(final_out.read_text(encoding="utf-8", errors="replace")):
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final_out, output)
        return "ok"
    return "failed"


def prepare_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose prepare", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--partition-file", required=True)
    parser.add_argument("--issue-number", default="")
    try:
        args = parser.parse_args(argv)
        design_tmpdir = _validate_design_tmpdir(args.design_tmpdir)
        status, witness = prepare_partition_issues(design_tmpdir=design_tmpdir, partition_file=Path(args.partition_file), issue_number=args.issue_number)
        _emit_kv(key="DECOMPOSE_PARTITION_STATUS", value=status)
        if witness:
            _emit_kv(key="DECOMPOSE_PARTITION_CYCLE_WITNESS", value=witness)
        if status != "ok":
            (design_tmpdir / "decompose" / "partition-input.txt").unlink(missing_ok=True)
            (design_tmpdir / "decompose" / "partition-deps.tsv").unlink(missing_ok=True)
            return 2 if status != "cycle-detected" else 0
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose prepare: {exc}")
        return 2


def annotate_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose annotate", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--issue-stdout-file", required=True)
    parser.add_argument("--issue-number", default="")
    try:
        args = parser.parse_args(argv)
        annotate_partition_issues(design_tmpdir=_validate_design_tmpdir(args.design_tmpdir), issue_stdout_file=Path(args.issue_stdout_file))
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose annotate: {exc}")
        return 2


def close_original_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose close-original", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--original-issue", required=True)
    parser.add_argument("--repo", required=True)
    try:
        args = parser.parse_args(argv)
        status = close_original_issue(design_tmpdir=_validate_design_tmpdir(args.design_tmpdir), original_issue=args.original_issue, repo=args.repo)
        _emit_kv(key="CLOSE_ORIGINAL_STATUS", value=status)
        return 0 if status == "ok" else 1
    except (SystemExit, UsageError) as exc:
        _err(f"decompose close-original: {exc}")
        return 2


def panel_dispatch_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-panel-dispatch.sh")
    parser = argparse.ArgumentParser(prog="decompose panel-dispatch", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--mode", required=True)
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--feature-file", default="")
    parser.add_argument("--discussion-round1-file", default="")
    parser.add_argument("--timeout", default="1800")
    try:
        args = parser.parse_args(argv)
        dispatch_panel(
            design_tmpdir=_validate_design_tmpdir(args.design_tmpdir),
            codex_present=_binary_bool(value=args.codex_binary_found, binary="codex"),
            cursor_present=_binary_bool(value=args.cursor_binary_found, binary="cursor"),
            mode=args.mode,
            plan_file=Path(args.plan_file) if args.plan_file else None,
            feature_file=Path(args.feature_file) if args.feature_file else None,
            discussion_file=Path(args.discussion_round1_file) if args.discussion_round1_file else None,
            timeout=_positive_int(value=args.timeout, flag="--timeout"),
        )
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose-panel-dispatch.sh: {exc}")
        return 2


def aggregate_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-aggregator.sh")
    parser = argparse.ArgumentParser(prog="decompose aggregate", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--panel-outputs-file", required=True)
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", default="1800")
    try:
        args = parser.parse_args(argv)
        status = aggregate_partition(
            design_tmpdir=_validate_design_tmpdir(args.design_tmpdir),
            panel_outputs_file=Path(args.panel_outputs_file),
            codex_present=_binary_bool(value=args.codex_binary_found, binary="codex"),
            cursor_present=_binary_bool(value=args.cursor_binary_found, binary="cursor"),
            output=Path(args.output),
            timeout=_positive_int(value=args.timeout, flag="--timeout"),
        )
        _emit_kv(key="AGGREGATOR_STATUS", value=status)
        if status == "ok":
            _emit_kv(key="AGGREGATOR_OUTPUT", value=args.output)
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose-aggregator.sh: {exc}")
        return 2
