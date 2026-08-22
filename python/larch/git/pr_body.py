"""PR body composition and Mermaid sanitization."""

# pyright: reportUnusedCallResult=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.core.repo_roots import larch_entrypoint
from larch.report import design_diagram_log
from larch.git import gh
from larch.core import redact
from larch.report import report_tokens_cost
from larch.report import tokens
from larch.issue import tracking_issue
from larch.implement import scope_disposition
from larch.errors import ShipError
from larch.core.proc import Runner


@dataclass(frozen=True)
class MermaidResult:
    status: str
    reason_tokens: tuple[str, ...]
    fence_count: int


@dataclass(frozen=True)
class FinalReportResult:
    exit_code: int
    comment_url: str
    error: str


@dataclass(frozen=True)
class CodeFlowDiagramResult:
    exit_code: int
    status: str
    diagram_file: str
    reason: str

_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,})([^`]*)$")
_FLOWCHART_START = re.compile(r"^(flowchart|graph)(\s|$)")
_OPEN_BRACKET = frozenset("[{(")
_CLOSE_BRACKET = frozenset("]})")
_ISSUE_SECTION_NONE = 0
_ISSUE_SECTION_EXEC = 1
_ISSUE_SECTION_WARN = 2
_EXEC_ISSUE_HEADINGS = frozenset({"### Tool Failures", "### External Reviewer Issues"})
_OOS_FILED_URL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)", re.MULTILINE)
_DIAGRAM_FAILURE_TAIL_LIMIT = 200
_CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS = 180
_MAX_DIAGRAM_RETRIES = 4
_DIAGRAM_RETRY_DELAY_SECONDS = 10
_WARNING_TAIL_LIMIT = 500
_LAUNCHER_FAILURE_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_IMPLEMENT_SUCCESS_OUTCOMES = frozenset({
    "merged",
    "force-merged-externally",
    "pr-created",
    "pr-created-draft",
    "design-only",
    "forked-dry-run",
})
_DESIGN_SUCCESS_OUTCOMES = frozenset({"approved", "approved-partition"})
_SUCCESS_OUTCOMES = _IMPLEMENT_SUCCESS_OUTCOMES | _DESIGN_SUCCESS_OUTCOMES


def _map_outcome_display(outcome: str) -> str:
    if outcome in _SUCCESS_OUTCOMES:
        return "✅ DONE"
    if outcome == "stalled":
        return "❌ STALLED"
    return outcome


def _needs_user_outcome_display(*, reason: str, next_action: str) -> str:
    """Distinct outcome for a terminal needs-user ship handoff (#7074).

    A needs-user bail (e.g. architectural assessments unavailable) creates the PR
    but skips the merge and CI watch. That must not render as ``✅ DONE``.
    """
    pending = f"; pending: {next_action}" if next_action else ""
    return f"⚠️ NEEDS USER — merge and CI watch skipped (reason: {reason}{pending})"


def _summary_outcome_display(*, outcome: str, kwargs: Mapping[str, object]) -> str:
    """Outcome display line for the run summary; distinct on a needs-user handoff (#7074).

    The caller passes ``needs_user_reason`` only when a terminal needs-user ship
    handoff applies, so its presence alone selects the needs-user display.
    """
    needs_user_reason = str(kwargs.get("needs_user_reason") or "")
    if needs_user_reason:
        return _needs_user_outcome_display(
            reason=needs_user_reason,
            next_action=str(kwargs.get("needs_user_next_action") or ""),
        )
    return _map_outcome_display(outcome)


def _bounded_warning_detail(text: str) -> str:
    detail = " ".join(text.split()) or "no-output"
    if len(detail) > _WARNING_TAIL_LIMIT:
        return "..." + detail[-(_WARNING_TAIL_LIMIT - 3):]
    return detail


def _warn(message: str) -> None:
    print(f"pr_body: {_bounded_warning_detail(message)}", file=sys.stderr)


def _plugin_version_from_completed(completed: Any) -> str:
    if completed.returncode != 0:
        _warn(f"plugin read-version failed rc={completed.returncode} stderr={completed.stderr}")
        return "unknown"
    m: re.Match[str] | None = re.search(r"^LARCH_PLUGIN_VERSION=(.*)$", completed.stdout, re.MULTILINE)
    return m.group(1) if m else "unknown"


def _code_flow_launch_cmd() -> list[str]:
    launcher = os.environ.get("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS")
    if launcher:
        return [launcher]
    return [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "agent", "launch-claude-subprocess"]


def _launcher_stdout_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            values[key] = value.strip()
    return values


def _launcher_failure_label(stdout: str) -> str:
    values = _launcher_stdout_kv(stdout)
    failure_class = values.get("LAUNCHER_FAILURE_CLASS", "")
    failure_reason = values.get("LAUNCHER_FAILURE_REASON", "")
    if not (
        failure_class
        and failure_reason
        and _LAUNCHER_FAILURE_LABEL_RE.fullmatch(failure_class)
        and _LAUNCHER_FAILURE_LABEL_RE.fullmatch(failure_reason)
    ):
        return ""
    return f"{failure_class}/{failure_reason}"


def flowchart_rejects_pipe(line: str) -> bool:
    """Port sanitize-mermaid-fragment.sh flowchart_reject (depth + quote aware)."""
    depth = 0
    quote = False
    esc = False
    for char in line:
        if depth > 0 and quote:
            if esc:
                esc = False
            elif char == "\\":
                esc = True
            elif char == '"':
                quote = False
            continue
        if depth > 0 and char == '"':
            quote = True
            continue
        if char in _OPEN_BRACKET:
            depth += 1
            continue
        if depth > 0 and char in _CLOSE_BRACKET:
            depth -= 1
            continue
        if depth > 0 and char == "|":
            return True
    return False


def _first_non_blank_mermaid_fence(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        match = _FENCE_RE.match(line)
        return bool(
            match and re.match(r"^\s*mermaid\s*$", match.group(3) or ""),
        )
    return False


def body_start_line(lines: list[str]) -> int:
    in_frontmatter = False
    frontmatter_started = False
    for index, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if not frontmatter_started and line == "---":
            in_frontmatter = True
            frontmatter_started = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        return index
    return -1 if in_frontmatter else len(lines) + 1


def _validate_fence_body(*, body: str, _fence_num: int) -> list[str]:
    lines = body.splitlines()
    start = body_start_line(lines)
    if start == -1:
        return [config.MERMAID_REASON_UNCLOSED_FRONTMATTER]
    if start < 1 or start > len(lines):
        return []
    first = lines[start - 1].strip()
    reasons: list[str] = []
    if _FLOWCHART_START.match(first):
        for line in lines[start - 1 :]:
            if flowchart_rejects_pipe(line):
                reasons.append(config.MERMAID_REASON_PIPE_IN_NODE)
                break
    elif first == "sequenceDiagram":
        for line in lines[start - 1 :]:
            lower = line.strip().lower()
            if not re.match(
                r"^(participant|actor)\s+\S+\s+as\s+",
                lower,
            ):
                continue
            alias = re.sub(
                r"^[^\s]+\s+[^\s]+\s+as\s+",
                "",
                line.strip(),
                flags=re.IGNORECASE,
            )
            if re.search(r"<br\s*/?>", alias, re.IGNORECASE):
                reasons.append(config.MERMAID_REASON_BR_IN_ALIAS)
            if "$" in alias:
                reasons.append(config.MERMAID_REASON_DOLLAR_IN_ALIAS)
    return reasons


def sanitize_fragment(text: str, *, from_md: bool = False) -> MermaidResult:
    """Port sanitize-mermaid-fragment.sh; returns ok or rejected with reason tokens."""
    if not from_md and _first_non_blank_mermaid_fence(text):
        from_md = True
    if from_md:
        fences: list[str] = []
        in_outer = False
        outer_len = 0
        outer_mermaid = False
        current: list[str] = []
        for line in text.splitlines():
            match = _FENCE_RE.match(line)
            if match:
                opener = match.group(2)
                rest = match.group(3)
                length = len(opener)
                if not in_outer:
                    if re.match(r"^\s*mermaid\s*$", rest):
                        if current:
                            fences.append("\n".join(current))
                        current = []
                        in_outer = True
                        outer_len = length
                        outer_mermaid = True
                        continue
                    in_outer = True
                    outer_len = length
                    outer_mermaid = False
                elif length >= outer_len and not rest.strip():
                    in_outer = False
                    outer_mermaid = False
                    if current:
                        fences.append("\n".join(current))
                        current = []
                continue
            if in_outer and outer_mermaid:
                current.append(line)
        if current:
            fences.append("\n".join(current))
    else:
        fences = [text]
    all_reasons: list[str] = []
    for index, fence in enumerate(fences, start=1):
        all_reasons.extend(_validate_fence_body(body=fence, _fence_num=index))
    unique: tuple[str, ...] = tuple(dict.fromkeys(all_reasons))
    if unique:
        return MermaidResult(status="rejected", reason_tokens=unique, fence_count=len(fences))
    return MermaidResult(status="ok", reason_tokens=(), fence_count=len(fences))


def _fail_closed_body(redacted: str) -> str:
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    return redacted


def redact_pr_body(body: str) -> str:
    """Redact a PR body fail-closed: tmpdir paths then secrets.

    Single source of truth for outbound PR-body redaction, shared by
    ``compose_pr_body`` (the live ship path) and ``pr.create_pr_parity``
    (``cli.py pr create``). It pipes the body through ``redact tmpdir-paths``
    then ``redact secrets`` and fails closed. Raises :class:`ShipError` when
    redaction truncates the body.
    """
    return _fail_closed_body(redact.redact(body))


def architectural_guidelines_section(body: str) -> str:
    """Return normalized architectural-guidelines section body, or empty when absent."""
    heading = "## Architectural guidelines"
    idx = body.find(heading)
    if idx < 0:
        return ""
    rest = body[idx + len(heading) :].lstrip("\n")
    next_heading = rest.find("\n## ")
    section = rest[:next_heading] if next_heading >= 0 else rest
    return section.strip()


def architectural_invariants_section(body: str) -> str:
    """Return normalized architectural-invariants section body, or empty when absent."""
    heading = "## Architectural invariants"
    idx = body.find(heading)
    if idx < 0:
        return ""
    rest = body[idx + len(heading) :].lstrip("\n")
    next_heading = rest.find("\n## ")
    section = rest[:next_heading] if next_heading >= 0 else rest
    return section.strip()


def compose_pr_body(
    *,
    summary: str,
    mermaid: str = "",
    test_plan: str = "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
    issue_number: int | None = None,
    architectural_invariants_note: str = "",
    architectural_guidelines_note: str = "",
    implement_tmpdir: Path | None = None,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    if mermaid.strip():
        mermaid_result = sanitize_fragment(mermaid)
        if mermaid_result.status != "ok":
            msg = f"mermaid fragment rejected: {','.join(mermaid_result.reason_tokens)}"
            raise ShipError(msg)
    parts = [summary.rstrip(), ""]
    if architectural_invariants_note.strip():
        parts.extend(["## Architectural invariants", "", architectural_invariants_note.strip(), ""])
    if architectural_guidelines_note.strip():
        parts.extend(["## Architectural guidelines", "", architectural_guidelines_note.strip(), ""])
    if mermaid.strip():
        parts.extend(["## Code Flow Diagram", "", "```mermaid", mermaid.strip(), "```", ""])
    inventory = scope_disposition.disposition_deferred_inventory(
        implement_tmpdir, repo_root=repo_root, manifest_path=manifest_path
    )
    if inventory.strip():
        parts.extend([inventory.rstrip(), ""])
    parts.extend(["## Test plan", "", test_plan.rstrip(), ""])
    body = "\n".join(parts) + "\n"
    if issue_number is not None:
        body = tracking_issue.link_pr_for_disposition(
            body=body,
            issue_number=issue_number,
            partial=scope_disposition.disposition_link_kind(
                implement_tmpdir, repo_root=repo_root, manifest_path=manifest_path
            ) == "part-of",
        )
    mermaid_body = sanitize_fragment(body, from_md=True)
    if mermaid_body.status != "ok":
        msg = f"mermaid in PR body rejected: {','.join(mermaid_body.reason_tokens)}"
        raise ShipError(msg)
    redacted = redact_pr_body(body)
    return redacted.rstrip("\n") + "\n"


def update_pr_body(
    *,
    runner: Runner,
    number: int,
    body: str,
    repo: str,
    cwd: str | None = None,
) -> None:
    mermaid_result = sanitize_fragment(body, from_md=True)
    if mermaid_result.status != "ok":
        msg = f"mermaid in PR body rejected: {','.join(mermaid_result.reason_tokens)}"
        raise ShipError(msg)
    redacted = redact.redact(body)
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    result = gh.pr_edit_body(runner, number, redacted, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh pr edit failed ({result.returncode})"
        raise ShipError(msg)

# ---------------------------------------------------------------------------
# C4c report helper ports
# ---------------------------------------------------------------------------

def _read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True, cr_strip="strip", on_error_default=False)


def _fmt_money(value: float | str) -> str:
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _money_value(value: object) -> float | str:
    return value if isinstance(value, (float, int, str)) else "N/A"


def _identity_from_manifest(manifest_path: str) -> dict[str, str]:
    try:
        parsed: Any = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    data = cast("Mapping[str, object]", parsed)
    roster = data.get("model_roster")
    model = cast("Mapping[str, object]", roster).get("main", "") if isinstance(roster, dict) else ""
    return {
        "larch_version": str(data.get("larch_version") or ""),
        "main_model": str(model or ""),
        "effort": str(data.get("effort") or ""),
    }


def _plugin_version_local() -> str:
    try:
        parsed: Any = json.loads((Path(__file__).resolve().parents[3] / config.PLUGIN_JSON_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    return str(cast("Mapping[str, object]", parsed).get("version") or "")


def _resolve_run_identity(kwargs: Mapping[str, object]) -> tuple[str, str, str]:
    """Resolve (larch_version, main_agent_model, effort) for the run summary.

    The committed run manifest (captured at run-log init) is the single source.
    Explicit kwargs win for tests; live fallbacks keep the summary populated when
    a manifest field is missing.
    """
    def clean(value: object) -> str:
        text = str(value or "").strip()
        return "" if text in ("", "unknown", "None") else text

    ident: dict[str, str] = {}
    manifest_authoritative = False
    manifest_path = kwargs.get("manifest_path")
    if manifest_path:
        manifest = Path(str(manifest_path))
        manifest_authoritative = manifest.is_file()
        ident = _identity_from_manifest(str(manifest))
    version = clean(kwargs.get("larch_version")) or clean(ident.get("larch_version")) or _plugin_version_local() or "unknown"
    model = clean(kwargs.get("main_model")) or clean(ident.get("main_model"))
    if not model and not manifest_authoritative:
        try:
            model = tokens.read_main_model()
        except Exception:
            model = ""
    model = model or "unknown"
    effort = (
        clean(kwargs.get("effort"))
        or clean(ident.get("effort"))
        or clean(os.environ.get("CLAUDE_CODE_EFFORT_LEVEL"))
        or clean(os.environ.get("CLAUDE_EFFORT"))
        or "unknown"
    )
    return version, model, effort


def _identity_lines(kwargs: Mapping[str, object]) -> list[str]:
    version, model, effort = _resolve_run_identity(kwargs)
    return [
        f"- **Main agent model**: {model}",
        f"- **Effort**: {effort}",
        f"- **Larch version**: {version}",
    ]


def _codex_cost_segment(kwargs: Mapping[str, object]) -> str:
    """Render the per-model Codex portion of the cost line (gpt-5.6 default vs mini-class models).

    Legacy callers that pass only the model-summed codex_cost fall back to it as the
    gpt-5.6 slot with a zero mini slot.
    """
    codex_5_5 = kwargs.get("codex_gpt_5_5_cost")
    codex_mini = kwargs.get("codex_gpt_5_4_mini_cost")
    if codex_5_5 is None or codex_5_5 == "N/A":
        codex_5_5 = kwargs.get("codex_cost", 0)
        codex_mini = 0
    return f"Codex-5.6 {_fmt_money(_money_value(codex_5_5))}, Codex-mini {_fmt_money(_money_value(codex_mini))}"



def _cursor_cost_segment(kwargs: Mapping[str, object]) -> str:
    aggregate = _fmt_money(_money_value(kwargs.get("cursor_cost", 0)))
    components = tuple(kwargs.get(key) for key in ("cursor_composer_cost", "cursor_grok_cost"))
    if any(value is None for value in components):
        return f"Cursor {aggregate}"
    composer, grok = (_fmt_money(_money_value(value)) for value in components)
    return f"Cursor {aggregate} (Composer {composer}, Grok {grok})"


def _plan_coverage_summary_lines(kwargs: Mapping[str, object]) -> list[str]:
    line = str(kwargs.get("plan_coverage_line") or "")
    return [f"- **Plan coverage**: {line}"] if line else []

def _try_float_money(value: object) -> float | None:
    try:
        return float(cast("float | int | str", value))
    except (TypeError, ValueError):
        return None


def _glm_main_lane_cost_parts(
    *,
    kwargs: Mapping[str, object],
    total_cost: object,
    total_tokens: int,
) -> tuple[str, str] | None:
    """Build GLM main-lane cost line + explanation, or None when not applicable."""
    _version, main_model, _effort = _resolve_run_identity(kwargs)
    if config.canonicalize_glm_main_model(main_model) != config.CLAUDE_GLM_5_2_MODEL:
        return None
    token_cost = _try_float_money(_money_value(kwargs.get("claude_cost", 0)))
    headline_total = _try_float_money(_money_value(total_cost))
    if token_cost is None or headline_total is None:
        return None
    estimated = round(token_cost / config.GLM_TOKEN_TO_PLAN_DIVISOR, 2)
    adjusted_total = round(headline_total - token_cost + estimated, 2)
    cost = (
        f"💰 TOTAL ~{_fmt_money(adjusted_total)}: "
        f"Claude/GLM-5.2 token {_fmt_money(token_cost)} (estimated {_fmt_money(estimated)}), "
        f"{_codex_cost_segment(kwargs)}, {_cursor_cost_segment(kwargs)}, "
        f"Claude (subprocess) {_fmt_money(_money_value(kwargs.get('claude_sub_cost', 0)))}  |  "
        f"Tokens: {int((total_tokens + 500) / 1000)}k"
    )
    note = (
        "- **Cost note**: Token is API-equivalent GLM-5.2 pricing; "
        f"estimated is plan cost (token ÷ {config.GLM_TOKEN_TO_PLAN_DIVISOR})."
    )
    return cost, note


def _cost_lines(
    *,
    kwargs: Mapping[str, object],
    total_cost: object,
    total_tokens: int,
) -> list[str]:
    """Render the ``- **Cost**:`` bullet and the optional GLM plan-estimate note."""
    if kwargs.get("cost_unavailable") or total_cost == "N/A":
        return ["- **Cost**: N/A"]
    glm_parts = _glm_main_lane_cost_parts(
        kwargs=kwargs, total_cost=total_cost, total_tokens=total_tokens,
    )
    if glm_parts is not None:
        cost, note = glm_parts
        return [f"- **Cost**: {cost}", note]
    cost = (
        f"💰 TOTAL ~{_fmt_money(_money_value(total_cost))}: "
        f"Claude {_fmt_money(_money_value(kwargs.get('claude_cost', 0)))}, "
        f"{_codex_cost_segment(kwargs)}, {_cursor_cost_segment(kwargs)}, "
        f"Claude (subprocess) {_fmt_money(_money_value(kwargs.get('claude_sub_cost', 0)))}  |  "
        f"Tokens: {int((total_tokens + 500) / 1000)}k"
    )
    return [f"- **Cost**: {cost}"]


def render_run_summary(**kwargs: object) -> str:
    skill = str(kwargs.get("skill") or "implement")
    outcome = str(kwargs.get("outcome") or "unknown")
    run_id = str(kwargs.get("run_id") or "unknown")
    force = str(kwargs.get("force_requested") or "false") == "true"
    total_tokens = int(str(kwargs.get("total_tokens") or kwargs.get("claude_tokens") or 0) or 0)
    total_cost = kwargs.get("total_cost", "N/A")
    issue_number = str(kwargs.get("issue_number") or "")
    issue_url = str(kwargs.get("issue_url") or "")
    issue = "N/A"
    if issue_number and issue_number != "0":
        issue = f"#{issue_number}" + (f": {issue_url}" if issue_url and issue_url != "N/A" else "")
    pr_number = str(kwargs.get("pr_number") or "")
    pr_url = str(kwargs.get("pr_url") or "")
    pr = "N/A"
    if pr_number and pr_number != "0":
        pr = f"#{pr_number}" + (f": {pr_url}" if pr_url and pr_url != "N/A" else "")
    lines_disp = "N/A"
    ca, cd, la, ld = (str(kwargs.get(k) or "") for k in ("code_added", "code_deleted", "logs_added", "logs_deleted"))
    if ca.isdigit() and cd.isdigit() and la.isdigit() and ld.isdigit():
        lines_disp = f"code +{ca}/-{cd}, larch-logs +{la}/-{ld}"
    oos_count = str(kwargs.get("oos_count") or "0")
    oos_urls = str(kwargs.get("oos_urls") or "")
    oos_disp = oos_count if not oos_urls or oos_urls == "N/A" or oos_count == "0" else f"{oos_count}: {oos_urls}"
    run_logs_reference = str(kwargs.get("run_logs_path") or "")
    if not run_logs_reference and run_id != "unknown" and outcome not in {"failed-publish", "publish-skipped"}:
        run_logs_reference = f"provider `unknown`, skill `{skill}`, run ID `{run_id}`"
    lines = [f"## /{skill} run {run_id}: {outcome}", ""]
    # #7074: a terminal needs-user ship handoff (merge + CI watch skipped) must not
    # render as ✅ DONE. _summary_outcome_display picks the needs-user display when
    # the caller supplies the handoff reason.
    lines.append(f"- **Outcome**: {_summary_outcome_display(outcome=outcome, kwargs=kwargs)}")
    if skill != "design" and kwargs.get("workflow_path"):
        lines.append(f"- **Path**: {kwargs.get('workflow_path')}")
    if force:
        lines.append("- Force: true")
    lines.append(f"- **Duration**: {kwargs.get('duration') or 'N/A'}")
    lines.extend(_cost_lines(kwargs=kwargs, total_cost=total_cost, total_tokens=total_tokens))
    lines.append(f"- **Issue**: {issue}")
    if skill != "design" and pr != "N/A":
        lines.append(f"- **PR**: {pr}")
    if skill != "design" and str(kwargs.get("merge_downgraded") or "false") == "true":
        lines.append(
            "- **⚠ Merge downgraded**: requested `--merge`, but panel-failed "
            "recovery shipped a PR without merging. Manual review and merge required."
        )
    lines.extend([f"- **Plan review**: {kwargs.get('plan_review_line') or 'N/A'}", *_plan_coverage_summary_lines(kwargs)])
    difficulty_line = str(kwargs.get("difficulty_line") or "")
    if difficulty_line:
        lines.append(f"- **Difficulty**: {difficulty_line}")
    dynamic_line = str(kwargs.get("dynamic_archetypes_line") or "")
    if dynamic_line:
        lines.append(f"- **Dynamic archetypes**: {dynamic_line}")
    if skill != "design":
        lines.extend([
            f"- **Code review**: {kwargs.get('code_review_line') or 'N/A'}",
            f"- **Lines (PR diff)**: {lines_disp}",
        ])
    lines.extend([
        f"- **OOS filed**: {oos_disp}",
        f"- **Exec issues**: {kwargs.get('exec_issues') or 0}",
        f"- **Warnings**: {kwargs.get('warnings') or 0}",
        f"- **Run log**: {run_logs_reference or 'N/A'}",
        *_identity_lines(kwargs),
        "",
        "<!-- larch:run-summary v=1 -->",
    ])
    note = kwargs.get("note_lines")
    if note:
        lines.extend(["", str(note).rstrip("\n")])
    return "\n".join(lines).rstrip("\n") + "\n"


_CLAUDE_SUB_MODEL_TOKEN_ARGS = tuple(
    f"{prefix}-{suffix}"
    for prefix in report_tokens_cost.CLAUDE_SUB_MODEL_FLAG_PREFIXES.values()
    for suffix in (
        "input-tokens",
        "cache-read-tokens",
        "cache-write-5m-tokens",
        "cache-write-1h-tokens",
        "output-tokens",
    )
)
_TOKEN_COST_ARGS = ("claude-tokens", "codex-tokens", "cursor-tokens", "claude-sub-tokens", "claude-input-tokens", "claude-cache-read-tokens", "claude-cache-write-5m-tokens", "claude-cache-write-1h-tokens", "claude-output-tokens", "codex-input-tokens", "codex-cached-input-tokens", "codex-output-tokens", "codex-mini-input-tokens", "codex-mini-cached-input-tokens", "codex-mini-output-tokens", "cursor-input-tokens", "cursor-cache-read-tokens", "cursor-output-tokens", "cursor-grok-input-tokens", "cursor-grok-cache-read-tokens", "cursor-grok-output-tokens", "claude-sub-input-tokens", "claude-sub-cache-read-tokens", "claude-sub-cache-write-5m-tokens", "claude-sub-cache-write-1h-tokens", "claude-sub-output-tokens", *_CLAUDE_SUB_MODEL_TOKEN_ARGS)


def _summary_token_argv(args: argparse.Namespace) -> list[str]:
    _version, pricing_model, _effort = _resolve_run_identity({"manifest_path": args.manifest_path, "main_model": args.main_model})
    token_argv: list[str] = []
    if pricing_model and pricing_model != "unknown":
        token_argv += ["--claude-model", pricing_model]
    for name in _TOKEN_COST_ARGS:
        val = getattr(args, name.replace("-", "_"), "0") or "0"
        if val != "0":
            token_argv += [f"--{name}", val]
    return token_argv


def render_run_summary_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py render run-summary")
    parser.add_argument("--skill", required=True, choices=("implement", "design"))
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--run-id", required=True)
    for name in ("mode", "workflow-path", "duration", "issue-number", "issue-url", "pr-number", "pr-url", "plan-review-line", "plan-coverage-line", "difficulty-line", "dynamic-archetypes-line", "code-review-line", "code-added", "code-deleted", "logs-added", "logs-deleted", "oos-count", "oos-urls", "exec-issues", "warnings", "run-logs-path", "merge-downgraded", "manifest-path", "larch-version", "main-model", "effort"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--force-requested", choices=("true", "false"))
    parser.add_argument("--output-file")
    parser.add_argument("--note-lines-file")
    parser.add_argument("--print-stdout", action="store_true")
    parser.add_argument("--cost-unavailable", action="store_true")
    for name in _TOKEN_COST_ARGS:
        parser.add_argument(f"--{name}", default="0")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    cost_unavailable = args.cost_unavailable
    total_cost = "N/A"
    claude_cost: object = "N/A"
    codex_cost: object = "N/A"
    codex_gpt_5_5_cost: object = "N/A"
    codex_gpt_5_4_mini_cost: object = "N/A"
    cursor_cost: object = "N/A"
    cursor_composer_cost: object | None = None
    cursor_grok_cost: object | None = None
    claude_sub_cost: object = "N/A"
    total_tokens = sum(int(getattr(args, a.replace("-", "_")) or 0) for a in ("claude-tokens", "codex-tokens", "cursor-tokens", "claude-sub-tokens"))
    if not cost_unavailable:
        try:
            token_argv = _summary_token_argv(args)
            cost_kv = report_tokens_cost.token_cost_from_args(token_argv)
            total_cost = larch_io.kv_value(text=cost_kv, key="TOTAL_COST", default="N/A")
            claude_cost = larch_io.kv_value(text=cost_kv, key="CLAUDE_COST", default="N/A")
            codex_cost = larch_io.kv_value(text=cost_kv, key="CODEX_COST", default="N/A")
            codex_gpt_5_5_cost = larch_io.kv_value(text=cost_kv, key="CODEX_GPT_5_5_COST", default="N/A")
            codex_gpt_5_4_mini_cost = larch_io.kv_value(text=cost_kv, key="CODEX_GPT_5_4_MINI_COST", default="N/A")
            cursor_cost = larch_io.kv_value(text=cost_kv, key="CURSOR_COST", default="N/A")
            cursor_composer_cost = (larch_io.kv_value(text=cost_kv, key="CURSOR_COMPOSER_COST", default="") or None)
            cursor_grok_cost = (larch_io.kv_value(text=cost_kv, key="CURSOR_GROK_COST", default="") or None)
            claude_sub_cost = larch_io.kv_value(text=cost_kv, key="CLAUDE_SUB_COST", default="N/A")
            total_tokens = int(larch_io.kv_value(text=cost_kv, key="TOTAL_TOKENS", default="N/A") or total_tokens)
        except Exception:
            cost_unavailable = True

    note_lines = Path(args.note_lines_file).read_text(encoding="utf-8") if args.note_lines_file and Path(args.note_lines_file).is_file() else ""
    body = render_run_summary(
        skill=args.skill,
        outcome=args.outcome,
        run_id=args.run_id,
        mode=args.mode,
        workflow_path=args.workflow_path,
        duration=args.duration,
        issue_number=args.issue_number,
        issue_url=args.issue_url,
        pr_number=args.pr_number,
        pr_url=args.pr_url,
        plan_review_line=args.plan_review_line,
        plan_coverage_line=args.plan_coverage_line,
        difficulty_line=args.difficulty_line,
        dynamic_archetypes_line=args.dynamic_archetypes_line,
        code_review_line=args.code_review_line,
        code_added=args.code_added,
        code_deleted=args.code_deleted,
        logs_added=args.logs_added,
        logs_deleted=args.logs_deleted,
        oos_count=args.oos_count,
        oos_urls=args.oos_urls,
        exec_issues=args.exec_issues,
        warnings=args.warnings,
        run_logs_path=args.run_logs_path,
        force_requested=args.force_requested,
        merge_downgraded=args.merge_downgraded,
        cost_unavailable=cost_unavailable,
        total_tokens=total_tokens,
        total_cost=total_cost,
        claude_cost=claude_cost,
        codex_cost=codex_cost,
        codex_gpt_5_5_cost=codex_gpt_5_5_cost,
        codex_gpt_5_4_mini_cost=codex_gpt_5_4_mini_cost,
        cursor_cost=cursor_cost,
        cursor_composer_cost=cursor_composer_cost,
        cursor_grok_cost=cursor_grok_cost,
        claude_sub_cost=claude_sub_cost,
        note_lines=note_lines,
        manifest_path=args.manifest_path,
        larch_version=args.larch_version,
        main_model=args.main_model,
        effort=args.effort,
    )
    if args.output_file:
        Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_file).write_text(body, encoding="utf-8")
    if args.print_stdout or not args.output_file:
        sys.stdout.write(body)
    print("STATUS=ok", file=sys.stderr)
    if args.output_file:
        print(f"OUTPUT_FILE={args.output_file}", file=sys.stderr)
    return 0


def _diagram_failure_capture(*, returncode: int, stderr: str) -> tuple[str, str]:
    tail_source = f"stderr:\n{stderr or ''}\n"
    try:
        capture = redact.redact(design_diagram_log.strip_diagram_sections(tail_source))
    except Exception:
        return f"returncode: {returncode}\nredaction-failed\n", "redaction-failed"
    sanitized = design_diagram_log.sanitize_diagram_capture(capture)
    collapsed = re.sub(r"\s+", " ", sanitized).strip() or "no-output"
    if len(collapsed) > _DIAGRAM_FAILURE_TAIL_LIMIT:
        collapsed = "..." + collapsed[-(_DIAGRAM_FAILURE_TAIL_LIMIT - 3):]
    return f"returncode: {returncode}\n{sanitized}", collapsed


def _needs_diagram_retry(*, returncode: int, raw: Path) -> bool:
    """Return True when the code-flow subprocess warrants a single retry.

    Preserves the historical voter retry criteria: retry on EXIT_TIMEOUT
    (wall-clock timeout or degraded-auth fast-fail) and on empty output
    when the launcher did run (file present but zero-byte).  A completely
    absent file signals a hard argv / import failure — not a transient
    Claude API hiccup — so we do NOT retry in that case.
    """
    if returncode == config.EXIT_TIMEOUT:
        return True
    return raw.is_file() and raw.stat().st_size == 0


def _run_diagram_subprocess(
    launch_argv: list[str], raw: Path, retry_sidecar: Path
) -> subprocess.CompletedProcess[str]:
    """Run the diagram subprocess, retrying up to _MAX_DIAGRAM_RETRIES times on transient failure."""
    completed = subprocess.run(launch_argv, text=True, capture_output=True, check=False)
    if not _needs_diagram_retry(returncode=completed.returncode, raw=raw):
        return completed
    _first_rc = completed.returncode
    _retry_rcs: list[int] = []
    for _retry_n in range(1, _MAX_DIAGRAM_RETRIES + 1):
        time.sleep(_DIAGRAM_RETRY_DELAY_SECONDS)
        with contextlib.suppress(OSError):
            raw.unlink()
        completed = subprocess.run(launch_argv, text=True, capture_output=True, check=False)
        _retry_rcs.append(completed.returncode)
        if not _needs_diagram_retry(returncode=completed.returncode, raw=raw):
            break
    with contextlib.suppress(OSError):
        _sidecar_lines = [f"FIRST_RC={_first_rc}"]
        for _i, _rc in enumerate(_retry_rcs, 1):
            _sidecar_lines.append(f"RETRY_{_i}_RC={_rc}")
        _sidecar_lines.append(f"RETRIES={len(_retry_rcs)}")
        retry_sidecar.write_text("\n".join(_sidecar_lines) + "\n", encoding="utf-8")
    return completed


def _diagram_stderr_from_sidecar(raw: Path, fallback: str) -> str:
    """Read the .stderr sidecar written by launch-claude-subprocess; fall back to launcher stderr."""
    _sidecar_text = ""
    with contextlib.suppress(OSError):
        _sidecar_text = raw.with_suffix(raw.suffix + ".stderr").read_text(encoding="utf-8", errors="replace")
    return _sidecar_text or fallback


def generate_code_flow_diagram(
    implement_tmpdir: Path,
    *,
    model: str = "claude-sonnet-4-6",
    base_remote: str = "origin",
    base_ref: str = "main",
) -> CodeFlowDiagramResult:
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    raw = implement_tmpdir / "code-flow-diagram.raw.md"
    candidate = implement_tmpdir / "code-flow-diagram.candidate.md"
    diagram = implement_tmpdir / "code-flow-diagram.md"
    prompt_path = implement_tmpdir / "code-flow-prompt.md"
    failure_log = implement_tmpdir / "code-flow-diagram.failure.log"
    retry_sidecar = implement_tmpdir / "code-flow-diagram.retried"
    base_target = f"{base_remote}/{base_ref}"
    merge_base = subprocess.run(["git", "merge-base", "HEAD", base_target], text=True, capture_output=True, check=False)  # noqa: S607
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        fallback = subprocess.run(["git", "rev-parse", "HEAD~1"], text=True, capture_output=True, check=False)  # noqa: S607
        merge_ref = fallback.stdout.strip() if fallback.returncode == 0 and fallback.stdout.strip() else "HEAD"
    else:
        merge_ref = merge_base.stdout.strip()
    changed = subprocess.run(["git", "diff", "--name-only", f"{merge_ref}..HEAD"], text=True, capture_output=True, check=False)  # noqa: S607
    changed_lines: list[str] = changed.stdout.strip().splitlines() if changed.returncode == 0 else []
    prompt_lines = [
        "Generate a concise Mermaid code-flow diagram for the committed implementation diff.",
        "Return markdown containing exactly one `## Code Flow Diagram` heading and one mermaid fence.",
        "Focus on runtime calls, data flow, and control flow. Avoid structural architecture duplication.",
        "",
        "Changed files:",
        *changed_lines,
        "",
    ]
    prompt_path.write_text("\n".join(prompt_lines), encoding="utf-8")
    launch_cmd = _code_flow_launch_cmd()
    with contextlib.suppress(OSError):
        failure_log.unlink()
    _launch_argv = [
        *launch_cmd,
        "--model", model,
        "--prompt-file", str(prompt_path),
        "--output-file", str(raw),
        "--timeout", str(_CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS),
        "--allow-root", str(Path.cwd()),
        "--timing-task-kind", "implement-code-flow",
    ]
    completed = _run_diagram_subprocess(_launch_argv, raw, retry_sidecar)
    if completed.returncode != 0:
        raw_capture: Path | None = implement_tmpdir / "code-flow-diagram.raw-failure.log"
        try:
            raw_capture.write_text(
                f"stderr:\n{completed.stderr or ''}\nstdout:\n{completed.stdout or ''}\n",
                encoding="utf-8",
            )
        except OSError:
            raw_capture = None
        _stderr = _diagram_stderr_from_sidecar(raw, fallback=completed.stderr)
        diagnostic, tail = _diagram_failure_capture(returncode=completed.returncode, stderr=_stderr)
        failure_label = _launcher_failure_label(completed.stdout or "")
        reason = (
            f"generation-failed {failure_label} rc={completed.returncode} tail={tail}"
            if failure_label
            else f"generation-failed rc={completed.returncode} tail={tail}"
        )
        try:
            if raw_capture is not None:
                bounded = design_diagram_log.write_bounded_diagram_failure_log(
                    implement_tmpdir,
                    site="implement Step 7a",
                    reason=reason,
                    exit_code=completed.returncode,
                    raw_capture_path=raw_capture,
                )
                if bounded != failure_log:
                    failure_log.write_text(bounded.read_text(encoding="utf-8"), encoding="utf-8")
                with contextlib.suppress(OSError):
                    raw_capture.unlink()
            else:
                failure_log.write_text(diagnostic, encoding="utf-8")
        except OSError:
            reason = f"{reason} log-write-failed"
        return CodeFlowDiagramResult(1, "failed", "", reason)
    if not raw.is_file() or raw.stat().st_size == 0:
        return CodeFlowDiagramResult(1, "failed", "", "empty-generation")
    candidate.write_bytes(raw.read_bytes())
    result = sanitize_fragment(candidate.read_text(encoding="utf-8"), from_md=True)
    if result.status == "ok":
        candidate.replace(diagram)
        with contextlib.suppress(OSError):
            failure_log.unlink()
            _ = (implement_tmpdir / "code-flow-diagram.raw-failure.log").unlink(missing_ok=True)
        return CodeFlowDiagramResult(0, "ok", str(diagram), "")
    candidate.unlink(missing_ok=True)
    return CodeFlowDiagramResult(
        0,
        "skipped",
        "",
        result.reason_tokens[0] if result.reason_tokens else "sanitizer-rejected",
    )


def generate_code_flow_diagram_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py diagram code-flow")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = parser.parse_args(argv)
    result = generate_code_flow_diagram(
        Path(args.implement_tmpdir),
        model=args.model,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    logging_util.emit_kv(key="STATUS", value=result.status)
    logging_util.emit_kv(key="DIAGRAM_FILE", value=result.diagram_file)
    logging_util.emit_kv(key="SKIP_REASON", value=result.reason)
    return result.exit_code
