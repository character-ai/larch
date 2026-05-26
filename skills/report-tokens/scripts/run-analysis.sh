#!/usr/bin/env bash
# run-analysis.sh - Analyze token costs from committed larch run logs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'EOF'
Usage: run-analysis.sh [--no-issue] [--no-plot] [--plot-from <issue-number>]

Flags:
  --no-issue               Skip posting the analysis report GitHub issue.
  --no-plot                Skip plot generation (text analysis still printed).
  --plot-from <N>          Re-plot from a prior [Analysis Report] issue body (skips scan).

Environment overrides:
  LARCH_REPORT_TOKENS_REPO=<owner/repo>   GitHub repository to scan; defaults to gh repo view.
  LARCH_REPORT_TOKENS_LIMIT=<N>           Optional max issue count after search.
  LARCH_REPORT_TOKENS_NO_OPEN=1           Do not open generated PNGs.
  LARCH_RATE_<VENDOR>_<FIELD>=<USD/M>     Override default cost rates.

Rate env names:
  LARCH_RATE_CLAUDE_INPUT
  LARCH_RATE_CLAUDE_CACHE_READ
  LARCH_RATE_CLAUDE_CACHE_CREATE
  LARCH_RATE_CLAUDE_OUTPUT
  LARCH_RATE_CODEX_INPUT
  LARCH_RATE_CODEX_OUTPUT
  LARCH_RATE_CODEX_AGGREGATE
  LARCH_RATE_CODEX_CACHE_READ
  LARCH_RATE_CURSOR_INPUT
  LARCH_RATE_CURSOR_OUTPUT
  LARCH_RATE_CURSOR_AGGREGATE

Reconciliation:
  LARCH_REPORT_TOKENS_ACTUAL_SPEND=<USD>  When set, prints tracked vs actual spend delta at report end.
                                           Contains billing data — use --no-issue when set to avoid
                                           posting actual spend figures to a public GitHub issue.
EOF
}

NO_ISSUE=
NO_PLOT=
PLOT_FROM=

while [[ $# -gt 0 ]]; do
    case "${1:-}" in
        --help|-h) usage; exit 0 ;;
        --no-issue) NO_ISSUE=1; shift ;;
        --no-plot)  NO_PLOT=1;  shift ;;
        --plot-from)
            [[ -n "${2:-}" ]] || { larch_err "ERROR: --plot-from requires an issue number"; exit 1; }
            PLOT_FROM="$2"; shift 2 ;;
        *) larch_err "ERROR: unknown argument: $1"; usage; exit 1 ;;
    esac
done

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        larch_err "ERROR: required command not found: $1"
        exit 1
    }
}

if [[ -z "${LARCH_REPORT_TOKENS_REPO:-}" ]]; then
    need_cmd gh
fi
need_cmd jq
need_cmd python3

resolve_repo() {
    if [[ -n "${LARCH_REPORT_TOKENS_REPO:-}" ]]; then
        printf '%s\n' "$LARCH_REPORT_TOKENS_REPO"
        return 0
    fi
    gh repo view --json nameWithOwner --jq '.nameWithOwner'
}

REPO="$(resolve_repo)"
if [[ -z "$REPO" || "$REPO" != */* ]]; then
    larch_err "ERROR: could not resolve GitHub repo owner/name"
    exit 1
fi

export LARCH_REPORT_TOKENS_REPO_FULL="$REPO"
export LARCH_REPORT_TOKENS_NO_ISSUE="${NO_ISSUE:-${LARCH_REPORT_TOKENS_NO_ISSUE:-}}"
export LARCH_REPORT_TOKENS_NO_PLOT="${NO_PLOT:-${LARCH_REPORT_TOKENS_NO_PLOT:-}}"

LIMIT="${LARCH_REPORT_TOKENS_LIMIT:-}"
if [[ -n "$LIMIT" && ! "$LIMIT" =~ ^[0-9]+$ ]]; then
    larch_err "ERROR: LARCH_REPORT_TOKENS_LIMIT must be a non-negative integer"
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-report-tokens.XXXXXX")"
trap 'rm -rf "${TMPROOT:-}"' EXIT
ISSUES_JSONL="$TMPROOT/issues.jsonl"
CACHE_TMP="$TMPROOT/issues-cache.json.tmp"
CACHE_JSON="$TMPROOT/issues-cache.json"
ANALYZER="$TMPROOT/analyze-token-reports.py"

if [[ -z "$PLOT_FROM" ]]; then
    REPO_ROOT=$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || pwd)
    LOG_BASE="$REPO_ROOT/larch-logs/implement"
    emit_breadcrumb --category=progress "Scanning $LOG_BASE for larch run logs..."

    : > "$ISSUES_JSONL"
    run_count=0
    while IFS= read -r dir; do
        manifest="$dir/manifest.json"
        token_report_json="$dir/token-report.json"
        timing_report_json="$dir/timing-report.json"
        plan_tally_json="$dir/plan-review-tally.json"

        [[ -f "$manifest" ]] || continue
        [[ -f "$token_report_json" ]] || continue

        issue_number=$(jq -r '.issue_number // empty' "$manifest" 2>/dev/null)
        [[ -n "$issue_number" && "$issue_number" != "null" ]] || continue
        [[ "$issue_number" =~ ^[0-9]+$ ]] || continue

        started_at=$(jq -r '(.started_at // "")' "$manifest" 2>/dev/null)
        closed_at=$(jq -r '(.updated_at // .started_at) // ""' "$manifest" 2>/dev/null)

        workflow_path="unknown"
        if [[ -f "$timing_report_json" ]]; then
            workflow_path=$(jq -r '.workflow_path // "unknown"' "$timing_report_json" 2>/dev/null || printf 'unknown')
            case "$workflow_path" in SIMPLE|HARD|unknown) ;; *) workflow_path="unknown" ;; esac
        fi
        if [[ "$workflow_path" == "unknown" && -f "$plan_tally_json" ]]; then
            tally_body=$(jq -r '(.body // .tally) // ""' "$plan_tally_json" 2>/dev/null || true)
            if [[ "$tally_body" == "Quick mode"* || "$tally_body" == "Both externals unavailable"* ]]; then
                workflow_path="SIMPLE"
            elif [[ -n "$tally_body" ]]; then
                workflow_path="HARD"
            fi
        fi

        combined_body="**Workflow path**: ${workflow_path}"
        emit_breadcrumb --category=progress "Processing run for issue #${issue_number}..."
        # Isolate jq failure per-run so a single invalid token-report.json
        # warns and is skipped rather than aborting the whole scan under
        # set -euo pipefail.
        if ! jq -cn \
            --argjson number "$issue_number" \
            --arg title "Issue #${issue_number}" \
            --arg url "https://github.com/${REPO}/issues/${issue_number}" \
            --arg startedAt "$started_at" \
            --arg closedAt "$closed_at" \
            --arg workflow_path "$workflow_path" \
            --arg body "$combined_body" \
            --slurpfile token_report "$token_report_json" \
            'if ($token_report[0] | type) == "object" then {number: $number, title: $title, url: $url, startedAt: $startedAt, closedAt: $closedAt, workflow_path: $workflow_path, body: $body, token_report: $token_report[0], comments: []} else error("not-an-object") end' \
            >> "$ISSUES_JSONL" 2>/dev/null; then
            larch_err "Warning: invalid token-report.json for issue #${issue_number} — skipping run"
        fi

        run_count=$((run_count + 1))
        if [[ -n "$LIMIT" && "$LIMIT" != "0" && "$run_count" -ge "$LIMIT" ]]; then
            break
        fi
    done < <(find "$LOG_BASE" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)

    jq -s . "$ISSUES_JSONL" > "$CACHE_TMP"
    mv "$CACHE_TMP" "$CACHE_JSON"
fi

cat > "$ANALYZER" <<'PY'
#!/usr/bin/env python3
import contextlib
import datetime as dt
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict


def env_rate(names, default):
    if isinstance(names, str):
        names = (names,)
    for name in names:
        raw = os.environ.get(name)
        if raw is None or raw == "":
            continue
        try:
            return float(raw)
        except ValueError:
            print(f"WARNING: ignoring invalid {name}={raw!r}; using next/default", file=sys.stderr)
    return default


def safe_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return default
        return int(value)
    if isinstance(value, str):
        s = value.replace(",", "").strip()
        if not s:
            return default
        try:
            return int(float(s))
        except ValueError:
            return default
    return default


# Frozen defaults used before DE-2622 for the "Reported cost" column (historical estimator).
LEGACY_REPORTED_RATES = {
    "claude": {"input": 3.00, "cache_read": 0.30, "cache_create": 3.75, "output": 15.00},
    "codex": {"input": 5.00, "output": 30.00, "aggregate": 5.00, "cache_read": 0.50},
    "cursor": {"input": 0.50, "output": 2.50, "aggregate": 0.20},
}

# Rates in USD per million tokens — aligned with scripts/token-cost.sh defaults for
# in-Python phase/vendor breakdown (see token-cost.md). Claude cache_create in JSON
# is merged 5m+1h; use the 5m default as a single blended bucket for this estimator.
RATES = {
    "claude": {
        "input": env_rate(("LARCH_RATE_CLAUDE_INPUT", "LARCH_CLAUDE_INPUT_RATE_PER_M"), 5.00),
        "cache_read": env_rate(("LARCH_RATE_CLAUDE_CACHE_READ", "LARCH_CLAUDE_CACHE_READ_RATE_PER_M"), 0.50),
        "cache_create": env_rate(("LARCH_RATE_CLAUDE_CACHE_CREATE", "LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M"), 6.25),
        "output": env_rate(("LARCH_RATE_CLAUDE_OUTPUT", "LARCH_CLAUDE_OUTPUT_RATE_PER_M"), 25.00),
    },
    "codex": {
        "input": env_rate(("LARCH_RATE_CODEX_INPUT", "LARCH_CODEX_INPUT_RATE_PER_M"), 0.44),
        "output": env_rate(("LARCH_RATE_CODEX_OUTPUT", "LARCH_CODEX_OUTPUT_RATE_PER_M"), 3.50),
        "aggregate": env_rate(("LARCH_RATE_CODEX_AGGREGATE", "LARCH_CODEX_RATE_PER_M"), 2.00),
        "cache_read": env_rate(("LARCH_RATE_CODEX_CACHE_READ", "LARCH_CODEX_CACHED_INPUT_RATE_PER_M"), 0.04),
    },
    "cursor": {
        "input": env_rate(("LARCH_RATE_CURSOR_INPUT", "LARCH_CURSOR_INPUT_RATE_PER_M"), 1.25),
        "output": env_rate(("LARCH_RATE_CURSOR_OUTPUT", "LARCH_CURSOR_OUTPUT_RATE_PER_M"), 6.00),
        "aggregate": env_rate(("LARCH_RATE_CURSOR_AGGREGATE", "LARCH_CURSOR_RATE_PER_M"), 1.50),
        "cache_read": env_rate(("LARCH_RATE_CURSOR_CACHE_READ", "LARCH_CURSOR_CACHE_READ_RATE_PER_M"), 0.25),
    },
}


ACTUAL_SPEND = env_rate("LARCH_REPORT_TOKENS_ACTUAL_SPEND", 0.0)


def parse_date(raw):
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def split_md_row(line):
    line = line.strip()
    if not line.startswith("|"):
        return []
    if line.endswith("|"):
        line = line[:-1]
    line = line[1:]
    cells = []
    current = []
    escaped = False
    for ch in line:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip())
    return cells


def clean_cell(value):
    return re.sub(r"\s+", " ", value.replace("\\|", "|").strip())


def parse_int(value):
    value = clean_cell(value)
    match = re.search(r"-?\d[\d,]*", value)
    if not match:
        return 0
    return int(match.group(0).replace(",", ""))


def section_name(line):
    match = re.match(r"^###\s+(.+?)\s*$", line)
    if not match:
        return None
    name = match.group(1).strip().lower()
    if name.startswith("claude"):
        return "claude"
    if name.startswith("codex"):
        return "codex"
    if name.startswith("cursor"):
        return "cursor"
    return re.sub(r"[^a-z0-9_-]+", "-", name).strip("-") or "unknown"


def latest_token_block(text):
    pattern = re.compile(
        r"(?ms)^<!-- token-report-begin -->\s*(.*?)^\s*<!-- token-report-end -->\s*$"
    )
    blocks = pattern.findall(text)
    if blocks:
        return blocks[-1]
    if "### Claude" in text or "**Grand total**" in text:
        return text
    return ""


def parse_workflow_path(text):
    match = re.search(
        r"\*\*Workflow path\*\*\s*:?\s*(SIMPLE|HARD|unknown)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "unknown"
    val = match.group(1).upper()
    return val if val in ("SIMPLE", "HARD") else "unknown"


def empty_totals():
    return {
        "claude": {"input": 0, "cache_read": 0, "cache_create": 0, "output": 0},
        "codex": {"input": 0, "output": 0, "total": 0},
        "cursor": {"input": 0, "output": 0, "total": 0},
    }


def parse_report(markdown):
    totals = empty_totals()
    phase_rows = []
    current = None
    for line in markdown.splitlines():
        maybe_section = section_name(line)
        if maybe_section:
            current = maybe_section
            if current not in totals and current != "claude":
                totals[current] = {"input": 0, "output": 0, "total": 0}
            continue
        if current is None or not line.lstrip().startswith("|"):
            continue
        cells = [clean_cell(c) for c in split_md_row(line)]
        if not cells or any(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if len(cells) >= 3 and cells[0].lower() == "step":
            continue
        is_grand = any("Grand total" in c for c in cells[:2])
        is_step_total = len(cells) >= 2 and "step total" in cells[1].lower()
        if current == "claude":
            if len(cells) >= 6:
                row = {
                    "input": parse_int(cells[-4]),
                    "cache_read": parse_int(cells[-3]),
                    "cache_create": parse_int(cells[-2]),
                    "output": parse_int(cells[-1]),
                }
            elif len(cells) >= 4:
                row = {
                    "input": parse_int(cells[-2]),
                    "cache_read": 0,
                    "cache_create": 0,
                    "output": parse_int(cells[-1]),
                }
            else:
                continue
            if is_grand:
                totals["claude"] = row
            elif is_step_total:
                phase_rows.append({"vendor": "claude", "step": cells[0], **row})
        else:
            if len(cells) < 5:
                continue
            row = {
                "input": parse_int(cells[-3]),
                "output": parse_int(cells[-2]),
                "total": parse_int(cells[-1]),
            }
            if current not in totals:
                totals[current] = {"input": 0, "output": 0, "total": 0}
            if is_grand:
                totals[current] = row
            elif is_step_total:
                phase_rows.append({"vendor": current, "step": cells[0], **row})
    return totals, phase_rows


def parse_json_report(report):
    totals = empty_totals()
    phase_rows = []
    if not isinstance(report, dict):
        return totals, phase_rows

    claude = report.get("claude") if isinstance(report.get("claude"), dict) else {}
    claude_totals = claude.get("totals") if isinstance(claude.get("totals"), dict) else {}
    totals["claude"] = {
        "input": safe_int(claude_totals.get("input")),
        "cache_read": safe_int(claude_totals.get("cache_read")),
        "cache_create": safe_int(claude_totals.get("cache_create")),
        "output": safe_int(claude_totals.get("output")),
    }
    for row in claude.get("per_step") or []:
        if not isinstance(row, dict):
            continue
        row_totals = row.get("totals") if isinstance(row.get("totals"), dict) else {}
        phase_rows.append({
            "vendor": "claude",
            "step": str(row.get("step") or ""),
            "input": safe_int(row_totals.get("input")),
            "cache_read": safe_int(row_totals.get("cache_read")),
            "cache_create": safe_int(row_totals.get("cache_create")),
            "output": safe_int(row_totals.get("output")),
        })

    vendor_names = report.get("vendors") if isinstance(report.get("vendors"), list) else []
    for vendor in vendor_names:
        if vendor == "claude" or not isinstance(vendor, str):
            continue
        section = report.get(vendor) if isinstance(report.get(vendor), dict) else {}
        section_totals = section.get("totals") if isinstance(section.get("totals"), dict) else {}
        totals[vendor] = {
            "input": safe_int(section_totals.get("input")),
            "output": safe_int(section_totals.get("output")),
            "total": safe_int(section_totals.get("total")),
        }
        for row in section.get("per_step") or []:
            if not isinstance(row, dict):
                continue
            row_totals = row.get("totals") if isinstance(row.get("totals"), dict) else {}
            phase_rows.append({
                "vendor": vendor,
                "step": str(row.get("step") or ""),
                "input": safe_int(row_totals.get("input")),
                "output": safe_int(row_totals.get("output")),
                "total": safe_int(row_totals.get("total")),
            })
    return totals, phase_rows


def cost_vendor(vendor, totals):
    if vendor == "claude":
        rate = RATES["claude"]
        return (
            totals.get("input", 0) * rate["input"]
            + totals.get("cache_read", 0) * rate["cache_read"]
            + totals.get("cache_create", 0) * rate["cache_create"]
            + totals.get("output", 0) * rate["output"]
        ) / 1_000_000
    if vendor not in RATES:
        import sys
        print(f"Warning: unknown vendor '{vendor}' — skipping (no pricing data)", file=sys.stderr)
        return 0.0
    rate = RATES[vendor]
    input_tokens = totals.get("input", 0)
    output_tokens = totals.get("output", 0)
    total_tokens = totals.get("total", 0)
    known = input_tokens + output_tokens
    hidden_or_aggregate = max(total_tokens - known, 0)
    if known == 0 and total_tokens > 0:
        return total_tokens * rate.get("aggregate", rate.get("input", 0)) / 1_000_000
    return (
        input_tokens * rate.get("input", 0)
        + output_tokens * rate.get("output", 0)
        + hidden_or_aggregate * rate.get("aggregate", 0)
    ) / 1_000_000


def total_cost(totals):
    return sum(cost_vendor(vendor, data) for vendor, data in totals.items())


def total_cost_legacy_vendor(vendor, totals):
    if vendor == "claude":
        rate = LEGACY_REPORTED_RATES["claude"]
        return (
            totals.get("input", 0) * rate["input"]
            + totals.get("cache_read", 0) * rate["cache_read"]
            + totals.get("cache_create", 0) * rate["cache_create"]
            + totals.get("output", 0) * rate["output"]
        ) / 1_000_000
    if vendor not in LEGACY_REPORTED_RATES:
        return 0.0
    rate = LEGACY_REPORTED_RATES[vendor]
    input_tokens = totals.get("input", 0)
    output_tokens = totals.get("output", 0)
    total_tokens = totals.get("total", 0)
    known = input_tokens + output_tokens
    hidden_or_aggregate = max(total_tokens - known, 0)
    if known == 0 and total_tokens > 0:
        return total_tokens * rate.get("aggregate", rate.get("input", 0)) / 1_000_000
    return (
        input_tokens * rate.get("input", 0)
        + output_tokens * rate.get("output", 0)
        + hidden_or_aggregate * rate.get("aggregate", 0)
    ) / 1_000_000


def total_cost_legacy(totals):
    return sum(total_cost_legacy_vendor(vendor, data) for vendor, data in totals.items())


def read_total_cost_from_kv(stdout: str) -> float:
    for line in stdout.splitlines():
        if line.startswith("TOTAL_COST="):
            try:
                return float(line.split("=", 1)[1])
            except ValueError:
                return 0.0
    return 0.0


def estimated_cost_token_cost_sh(plugin_root: str, token_report, totals) -> float:
    exe = os.path.join(plugin_root, "scripts", "token-cost.sh")
    if not plugin_root or not os.path.isfile(exe):
        return total_cost(totals)
    tr = token_report if isinstance(token_report, dict) else {}
    bc = tr.get("BUCKETS_claude")
    bd = tr.get("BUCKETS_codex")
    bu = tr.get("BUCKETS_cursor")
    if isinstance(bc, dict) and isinstance(bd, dict) and isinstance(bu, dict):
        args = [
            exe,
            "--claude-input-tokens", str(safe_int(bc.get("input"))),
            "--claude-cache-read-tokens", str(safe_int(bc.get("cache_read"))),
            "--claude-cache-write-5m-tokens", str(safe_int(bc.get("cache_create_5m"))),
            "--claude-cache-write-1h-tokens", str(safe_int(bc.get("cache_create_1h"))),
            "--claude-output-tokens", str(safe_int(bc.get("output"))),
            "--codex-input-tokens", str(safe_int(bd.get("input"))),
            "--codex-cached-input-tokens", str(safe_int(bd.get("cached_input"))),
            "--codex-output-tokens", str(safe_int(bd.get("output"))),
            "--cursor-input-tokens", str(safe_int(bu.get("input"))),
            "--cursor-cache-read-tokens", str(safe_int(bu.get("cache_read"))),
            "--cursor-output-tokens", str(safe_int(bu.get("output"))),
        ]
    else:
        ct = totals.get("claude") or {}
        cod = totals.get("codex") or {}
        cur = totals.get("cursor") or {}
        ctot = int(
            safe_int(ct.get("input"))
            + safe_int(ct.get("cache_read"))
            + safe_int(ct.get("cache_create"))
            + safe_int(ct.get("output"))
        )
        args = [
            exe,
            "--claude-tokens", str(ctot),
            "--codex-tokens", str(safe_int(cod.get("total"))),
            "--cursor-tokens", str(safe_int(cur.get("total"))),
        ]
    try:
        proc = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        return total_cost(totals)
    if proc.stderr and proc.stderr.strip():
        for line in proc.stderr.strip().splitlines():
            print(f"token-cost.sh: {line}", file=sys.stderr)
    if proc.returncode != 0:
        return total_cost(totals)
    return read_total_cost_from_kv(proc.stdout)


def normalize_step(step):
    step = re.sub(r"^\s*Step\s*", "", step, flags=re.IGNORECASE)
    step = re.sub(r"^\d+[a-z]?(?:\.\d+)?\s*[-:]\s*", "", step)
    step = re.sub(r"\s+", " ", step).strip()
    return step or "unknown"


def dollars(value):
    return f"${value:,.2f}"


def table_dollars(value):
    return f"${value:,.4f}" if 0 < value < 0.01 else dollars(value)


def pct(part, whole):
    if not whole:
        return "0.0%"
    return f"{(100.0 * part / whole):.1f}%"


def analyze(cache_path):
    with open(cache_path, "r", encoding="utf-8") as fh:
        issues = json.load(fh)

    records = []
    skipped = 0
    for issue in issues:
        token_report = issue.get("token_report")
        text_parts = [issue.get("body") or ""]
        comments = issue.get("comments") or []
        for comment in comments:
            text_parts.append(comment.get("body") or "")
        combined = "\n\n".join(text_parts)
        if isinstance(token_report, dict):
            totals, phase_rows = parse_json_report(token_report)
        else:
            block = latest_token_block(combined)
            if not block:
                skipped += 1
                continue
            totals, phase_rows = parse_report(block)
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        cost_reported = total_cost_legacy(totals)
        cost_estimated = estimated_cost_token_cost_sh(
            plugin_root,
            token_report if isinstance(token_report, dict) else None,
            totals,
        )
        cost = cost_estimated
        workflow = issue.get("workflow_path") or parse_workflow_path(combined)
        if workflow not in ("SIMPLE", "HARD", "unknown"):
            workflow = "unknown"
        started_at_date = parse_date(issue.get("startedAt"))
        closed_at = parse_date(issue.get("closedAt"))
        records.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title") or "",
                "url": issue.get("url") or "",
                "started_at_date": started_at_date,
                "closed_at": closed_at,
                "workflow": workflow,
                "totals": totals,
                "phase_rows": phase_rows,
                "cost": cost,
                "cost_reported": cost_reported,
                "cost_estimated": cost_estimated,
            }
        )

    records.sort(key=lambda r: (r["closed_at"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), r["number"] or 0))
    return records, skipped


def per_day_trend_tables(records):
    groups = {}
    vendor_buckets = (
        ("total", "Total cost", lambda record: record["cost"]),
        ("claude", "Claude cost", lambda record: cost_vendor("claude", record["totals"].get("claude", {}))),
        ("codex", "Codex cost", lambda record: cost_vendor("codex", record["totals"].get("codex", {}))),
        ("cursor", "Cursor cost", lambda record: cost_vendor("cursor", record["totals"].get("cursor", {}))),
    )

    excluded = 0
    for record in records:
        if record["workflow"] not in {"SIMPLE", "HARD"}:
            continue
        if record["started_at_date"] is None:
            excluded += 1
            continue
        day = record["started_at_date"].date()
        for vendor_key, _vendor_title, cost_fn in vendor_buckets:
            groups.setdefault((vendor_key, record["workflow"], day), []).append(cost_fn(record))

    lines = ["", "### Per-day cost trend"]
    if excluded:
        lines.append(f"_Note: {excluded} run(s) excluded from day buckets (missing or unparseable started_at in manifest)._")
    used_single_run_marker = False
    for vendor_key, vendor_title, _cost_fn in vendor_buckets:
        for workflow in ("SIMPLE", "HARD"):
            day_rows = []
            for key_vendor, key_workflow, day in groups:
                if key_vendor == vendor_key and key_workflow == workflow:
                    day_rows.append((day, sorted(groups[(key_vendor, key_workflow, day)])))
            lines.extend([
                "",
                f"#### {vendor_title} — {workflow}",
                "",
                "| Date | N | Median | Mean | P75 | Max | Total |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ])
            if not day_rows:
                lines.append("| — | — | — | — | — | — | — |")
                continue
            for day, values in sorted(day_rows):
                count = len(values)
                # floor((n-1)*0.75) gives index 2 for n=4, avoiding P75==Max on small buckets
                p75_index = int((count - 1) * 0.75)
                n_cell = f"{count}*" if count == 1 else str(count)
                if count == 1:
                    used_single_run_marker = True
                lines.append(
                    "| {date} | {n} | {median} | {mean} | {p75} | {max_value} | {total} |".format(
                        date=day.isoformat(),
                        n=n_cell,
                        median=table_dollars(statistics.median(values)),
                        mean=table_dollars(sum(values) / count),
                        p75=table_dollars(values[p75_index]),
                        max_value=table_dollars(max(values)),
                        total=table_dollars(sum(values)),
                    )
                )
    if used_single_run_marker:
        lines.extend(["", "_* single-run day — statistically limited_"])
    return "\n".join(lines)


def plot(records):
    out_paths = []
    if os.environ.get("LARCH_REPORT_TOKENS_NO_PLOT") in {"1", "true", "TRUE", "yes", "YES"}:
        return out_paths
    if os.environ.get("LARCH_REPORT_TOKENS_NO_OPEN") in {"1", "true", "TRUE", "yes", "YES"}:
        should_open = False
    else:
        should_open = True
    plot_rows = []
    for record in records:
        if record["closed_at"] is None or record["workflow"] not in {"SIMPLE", "HARD"}:
            continue
        plot_rows.append(
            {
                "workflow": record["workflow"],
                "closed_at": record["closed_at"].isoformat(),
                "cost": record["cost"],
                "number": record["number"],
            }
        )
    if not plot_rows:
        return out_paths

    plot_dir = tempfile.mkdtemp(prefix="larch-report-tokens-plot.")
    input_path = os.path.join(plot_dir, "plot-input.json")
    script_path = os.path.join(plot_dir, "plot.py")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(plot_rows, fh)
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(
            r'''
import datetime as dt
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    rows = json.load(fh)

plot_dir = sys.argv[2]
paths = []
for workflow in ("SIMPLE", "HARD"):
    selected = [r for r in rows if r["workflow"] == workflow]
    if not selected:
        continue
    selected.sort(key=lambda r: (r["closed_at"], r["number"] or 0))
    dates = [dt.datetime.fromisoformat(r["closed_at"]) for r in selected]
    costs = [r["cost"] for r in selected]
    numbers = [r["number"] for r in selected]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(dates, costs, marker="o", linewidth=1.5)
    ax.set_title(f"{workflow} token cost over time")
    ax.set_ylabel("Estimated cost (USD)")
    ax.set_xlabel("Run date")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    for x, y, number in zip(dates, costs, numbers):
        ax.annotate(f"#{number}", (x, y), xytext=(4, 5), textcoords="offset points", fontsize=8)
    out = os.path.join(plot_dir, f"larch-report-tokens-{workflow.lower()}.png")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    paths.append(out)

print(json.dumps(paths))
'''
        )

    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", os.path.join(plot_dir, "mpl"))
    os.makedirs(env["MPLCONFIGDIR"], exist_ok=True)
    result = subprocess.run(
        [sys.executable, script_path, input_path, plot_dir],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stderr_text = (result.stderr or "").strip()
        if stderr_text:
            tail = stderr_text[-2000:]
            print(f"Plot generation skipped: matplotlib subprocess exited {result.returncode}:")
            print(tail)
        else:
            print(f"Plot generation skipped: matplotlib subprocess exited {result.returncode} with no stderr")
        return out_paths
    try:
        out_paths = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Plot generation skipped: matplotlib subprocess returned invalid JSON")
        return []

    if should_open:
        for path in out_paths:
            try:
                subprocess.run(["open", path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                print("Note: 'open' not available; plots saved but not opened automatically.")
                break
    return out_paths


def print_analysis(cache_path, records, skipped, plot_paths):
    print("")
    print("## Report Tokens Analysis")
    print("")
    print(f"Cache JSON: {cache_path}")
    if plot_paths:
        print("Plots:")
        for path in plot_paths:
            print(f"- {path}")
    else:
        print("Plots: not generated")
    print("")
    print("Default rates, USD per million tokens:")
    print(
        "- Claude input={input:g}, cache_read={cache_read:g}, cache_create={cache_create:g}, output={output:g}".format(
            **RATES["claude"]
        )
    )
    print(
        "- Codex input={input:g}, output={output:g}, aggregate={aggregate:g}, cached_input={cache_read:g}".format(
            **RATES["codex"]
        )
    )
    print(
        "- Cursor input={input:g}, output={output:g}, aggregate={aggregate:g}, cache_read={cache_read:g}".format(
            **RATES["cursor"]
        )
    )
    print("")
    if not records:
        print("No parseable token reports found.")
        if skipped:
            print(f"Skipped runs without a parseable report: {skipped}")
        return

    dates = [r["closed_at"] for r in records if r["closed_at"]]
    costs = [r["cost"] for r in records]
    print(
        f"Parsed {len(records)} run(s); skipped {skipped}. "
        f"Total estimated cost (token-cost.sh / BUCKETS): {dollars(sum(costs))}; "
        f"median run cost: {dollars(statistics.median(costs))}."
    )
    if dates:
        print(f"Closed date range: {min(dates).date()} to {max(dates).date()}.")
    print("")
    print("### Reported vs estimated (per issue)")
    print("")
    print("| Issue | Reported (legacy estimator) | Estimated (token-cost.sh) |")
    print("| --- | ---: | ---: |")
    for r in sorted(records, key=lambda x: (x.get("number") or 0)):
        cr = r.get("cost_reported", r["cost"])
        ce = r.get("cost_estimated", r["cost"])
        print(f"| #{r.get('number')} | {dollars(cr)} | {dollars(ce)} |")
    print("")

    by_workflow = defaultdict(list)
    for record in records:
        by_workflow[record["workflow"]].append(record)
    print("### Cost by workflow")
    for workflow in ("SIMPLE", "HARD", "unknown"):
        rows = by_workflow.get(workflow, [])
        if not rows:
            continue
        values = [r["cost"] for r in rows]
        print(
            f"- {workflow}: {len(rows)} run(s), total {dollars(sum(values))}, "
            f"median {dollars(statistics.median(values))}, mean {dollars(statistics.mean(values))}, max {dollars(max(values))}"
        )
        vendor_costs: dict = {}
        for r in rows:
            for vendor, data in r["totals"].items():
                vendor_costs[vendor] = vendor_costs.get(vendor, 0.0) + cost_vendor(vendor, data)
        for vendor in sorted(vendor_costs):
            vc = vendor_costs[vendor]
            if vc > 0:
                print(f"  - {vendor}: {dollars(vc)}")

    simple = sorted(by_workflow.get("SIMPLE", []), key=lambda r: r["cost"], reverse=True)[:10]
    print("")
    print("### Top SIMPLE runs by estimated cost")
    if simple:
        for r in simple:
            print(f"- #{r['number']} {dollars(r['cost'])} - {r['title']}")
    else:
        print("- No SIMPLE runs found.")

    hard_rows = by_workflow.get("HARD", [])
    phase_costs = Counter()
    for record in hard_rows:
        for row in record["phase_rows"]:
            vendor = row["vendor"]
            step = normalize_step(row["step"])
            if vendor == "claude":
                row_cost = cost_vendor("claude", row)
            else:
                row_cost = cost_vendor(vendor, row)
            phase_costs[step] += row_cost
    print("")
    print("### HARD phase breakdown")
    if phase_costs:
        for step, value in phase_costs.most_common(12):
            print(f"- {step}: {dollars(value)}")
    else:
        print("- No HARD phase rows found.")

    claude_input = sum(r["totals"].get("claude", {}).get("input", 0) for r in records)
    claude_cache_read = sum(r["totals"].get("claude", {}).get("cache_read", 0) for r in records)
    claude_cache_create = sum(r["totals"].get("claude", {}).get("cache_create", 0) for r in records)
    claude_output = sum(r["totals"].get("claude", {}).get("output", 0) for r in records)
    claude_total_tokens = claude_input + claude_cache_read + claude_cache_create + claude_output
    claude_cache_read_cost = claude_cache_read * RATES["claude"]["cache_read"] / 1_000_000
    print("")
    print("### Cache-read dominance")
    print(
        f"Claude cache-read tokens: {claude_cache_read:,} "
        f"({pct(claude_cache_read, claude_total_tokens)} of Claude token volume), "
        f"estimated cache-read cost {dollars(claude_cache_read_cost)}."
    )

    print("")
    print("### Suggestions")
    print("- Keep high-volume shared context in generated artifacts and have reviewers cite files instead of re-pasting long prompt context.")
    print("- For expensive HARD phases, inspect the top phase rows above before optimizing; repeated review or design phases usually dominate more than implementation.")
    print("- When cache-read volume dominates, prioritize trimming repeated static context and large unchanged markdown blocks before reducing output verbosity.")

    print(per_day_trend_tables(records))

    if ACTUAL_SPEND > 0:
        tracked = sum(r["cost"] for r in records)
        delta_pct = (tracked - ACTUAL_SPEND) / ACTUAL_SPEND * 100 if ACTUAL_SPEND else 0
        print("")
        print(f"### Reconciliation (LARCH_REPORT_TOKENS_ACTUAL_SPEND)")
        print(f"tracked={dollars(tracked)}  actual={dollars(ACTUAL_SPEND)}  delta={delta_pct:+.1f}%")


def load_raw_records(body_file):
    with open(body_file, encoding="utf-8") as fh:
        body = fh.read()
    # Anchor on the "## Raw per-issue data" heading to avoid matching earlier code fences
    section_match = re.search(r"## Raw per-issue data\s*\n", body)
    if not section_match:
        print("ERROR: could not find '## Raw per-issue data' section in issue body", file=sys.stderr)
        return None
    tail = body[section_match.end():]
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", tail, re.DOTALL)
    if not fence_match:
        print("ERROR: could not find raw per-issue data block in issue body", file=sys.stderr)
        return None
    try:
        raw = json.loads(fence_match.group(1))
    except json.JSONDecodeError as exc:
        print(f"ERROR: failed to parse raw data: {exc}", file=sys.stderr)
        return None
    records = []
    for item in raw:
        records.append({
            "number": item.get("number"),
            "workflow": item.get("workflow", "unknown"),
            "started_at_date": parse_date(item.get("started_at")),
            "closed_at": parse_date(item.get("closed_at")),
            "cost": float(item.get("cost") or 0),
            "cost_reported": float(item.get("cost_reported") or item.get("cost") or 0),
            "cost_estimated": float(item.get("cost_estimated") or item.get("cost") or 0),
            "title": "",
            "url": "",
            "totals": {},
            "phase_rows": [],
        })
    return records


def create_report_issue(records, analysis_text):
    raw_rows = [
        {
            "number": r["number"],
            "workflow": r["workflow"],
            "started_at": r["started_at_date"].isoformat() if r["started_at_date"] else None,
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            "cost": r["cost"],
            "cost_reported": r.get("cost_reported", r["cost"]),
            "cost_estimated": r.get("cost_estimated", r["cost"]),
        }
        for r in records
    ]
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    title = f"[Analysis Report] Token costs as of {now}"
    body = (
        analysis_text
        + "\n\n## Raw per-issue data\n\n```json\n"
        + json.dumps(raw_rows, indent=2)
        + "\n```\n"
    )
    repo = os.environ.get("LARCH_REPORT_TOKENS_REPO_FULL", "")
    body_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, prefix="larch-report-tokens-body-"
        ) as f:
            body_path = f.name
            f.write(body)
        args = ["gh", "issue", "create", "--title", title, "--body-file", body_path]
        if repo:
            args += ["--repo", repo]
        result = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print(f"\nAnalysis report issue created: {result.stdout.strip()}")
        else:
            print(f"\nWarning: failed to create analysis report issue: {result.stderr.strip()}", file=sys.stderr)
    finally:
        if body_path:
            try:
                os.unlink(body_path)
            except OSError:
                pass


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--plot-from":
        if len(sys.argv) != 3:
            print("usage: analyze-token-reports.py --plot-from <issue-body-file>", file=sys.stderr)
            return 2
        records = load_raw_records(sys.argv[2])
        if records is None:
            return 1
        plot_paths = plot(records)
        if plot_paths:
            print("Plots written to:")
            for p in plot_paths:
                print(f"  {p}")
        else:
            print("No plots generated.")
        return 0

    if len(sys.argv) != 2:
        print("usage: analyze-token-reports.py <cache-json>", file=sys.stderr)
        return 2

    records, skipped = analyze(sys.argv[1])
    plot_paths = plot(records)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_analysis(sys.argv[1], records, skipped, plot_paths)
    analysis_text = buf.getvalue()
    sys.stdout.write(analysis_text)

    if not os.environ.get("LARCH_REPORT_TOKENS_NO_ISSUE") in {"1", "true", "TRUE", "yes", "YES"}:
        create_report_issue(records, analysis_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ANALYZER"
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}"

# Restore original stdout so the Python analyzer's report reaches the caller.
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

if [[ -n "$PLOT_FROM" ]]; then
    emit_breadcrumb --category=progress "Fetching analysis report issue #$PLOT_FROM..."
    ISSUE_BODY_FILE="$TMPROOT/plot-from-body.txt"
    gh issue view "$PLOT_FROM" --repo "$REPO" --json body --jq '.body' > "$ISSUE_BODY_FILE"
    python3 "$ANALYZER" --plot-from "$ISSUE_BODY_FILE"
    exit $?
fi

python3 "$ANALYZER" "$CACHE_JSON"
