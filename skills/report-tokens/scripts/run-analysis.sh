#!/usr/bin/env bash
# run-analysis.sh - Analyze token-report costs across closed larch issues.

set -euo pipefail

usage() {
    cat <<'EOF' >&2
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
  LARCH_RATE_GEMINI_INPUT
  LARCH_RATE_GEMINI_OUTPUT
  LARCH_RATE_GEMINI_AGGREGATE

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
            [[ -n "${2:-}" ]] || { echo "ERROR: --plot-from requires an issue number" >&2; exit 1; }
            PLOT_FROM="$2"; shift 2 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage; exit 1 ;;
    esac
done

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: required command not found: $1" >&2
        exit 1
    }
}

need_cmd gh
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
    echo "ERROR: could not resolve GitHub repo owner/name" >&2
    exit 1
fi

export LARCH_REPORT_TOKENS_REPO_FULL="$REPO"
export LARCH_REPORT_TOKENS_NO_ISSUE="${NO_ISSUE:-}"
export LARCH_REPORT_TOKENS_NO_PLOT="${NO_PLOT:-}"

LIMIT="${LARCH_REPORT_TOKENS_LIMIT:-}"
if [[ -n "$LIMIT" && ! "$LIMIT" =~ ^[0-9]+$ ]]; then
    echo "ERROR: LARCH_REPORT_TOKENS_LIMIT must be a non-negative integer" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-report-tokens.XXXXXX")"
trap 'rm -rf "${TMPROOT:-}"' EXIT
SEARCH_JSONL="$TMPROOT/search.jsonl"
ISSUES_JSONL="$TMPROOT/issues.jsonl"
CACHE_TMP="$TMPROOT/issues-cache.json.tmp"
CACHE_JSON="$TMPROOT/issues-cache.json"
ANALYZER="$TMPROOT/analyze-token-reports.py"

if [[ -z "$PLOT_FROM" ]]; then
    echo "Scanning $REPO for closed issues with token-report-begin comments..."

    SEARCH_QUERY="repo:${REPO} is:issue is:closed token-report-begin in:comments"
    gh api --paginate -X GET search/issues \
        -f "q=$SEARCH_QUERY" \
        -f per_page=100 \
        --jq '.items[] | {number, closed_at, title, html_url}' > "$SEARCH_JSONL"

    if [[ -n "$LIMIT" && "$LIMIT" != "0" ]]; then
        head -n "$LIMIT" "$SEARCH_JSONL" > "$SEARCH_JSONL.limited"
        mv "$SEARCH_JSONL.limited" "$SEARCH_JSONL"
    fi

    : > "$ISSUES_JSONL"
    while IFS= read -r item; do
        [[ -n "$item" ]] || continue
        number="$(printf '%s\n' "$item" | jq -r '.number')"
        [[ "$number" =~ ^[0-9]+$ ]] || continue
        echo "Fetching issue #$number..."
        gh issue view "$number" \
            --repo "$REPO" \
            --comments \
            --json number,title,url,closedAt,body,comments \
            | jq -c . >> "$ISSUES_JSONL"
    done < "$SEARCH_JSONL"

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


def env_rate(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"WARNING: ignoring invalid {name}={raw!r}; using {default}", file=sys.stderr)
        return default


# Rates in USD per million tokens. Sources verified May 2026:
#   Claude Sonnet/Opus: https://anthropic.com/pricing
#   Codex (GPT-5.5 via OpenAI): https://developers.openai.com/api/docs/models/gpt-5.5
#   Cursor Composer 2: https://cursor.com/docs/models-and-pricing
#   Gemini 2.5 Pro: https://ai.google.dev/pricing
RATES = {
    "claude": {
        "input": env_rate("LARCH_RATE_CLAUDE_INPUT", 3.00),
        "cache_read": env_rate("LARCH_RATE_CLAUDE_CACHE_READ", 0.30),
        "cache_create": env_rate("LARCH_RATE_CLAUDE_CACHE_CREATE", 3.75),
        "output": env_rate("LARCH_RATE_CLAUDE_OUTPUT", 15.00),
    },
    # GPT-5.5 via Codex CLI. Input/Output columns are always 0 in token reports
    # (Codex CLI only reports an aggregate "tokens used" on stderr); the aggregate
    # rate is a working approximation of the true input-heavy mix at ~$5/M.
    # cache_read and output are documented here for future use when Codex CLI
    # exposes per-bucket token counts. Known limitation: the 2x/1.5x long-context
    # surcharge for prompts >272K tokens is not modeled.
    "codex": {
        "input": env_rate("LARCH_RATE_CODEX_INPUT", 5.00),
        "output": env_rate("LARCH_RATE_CODEX_OUTPUT", 30.00),
        "aggregate": env_rate("LARCH_RATE_CODEX_AGGREGATE", 5.00),
        "cache_read": env_rate("LARCH_RATE_CODEX_CACHE_READ", 0.50),
    },
    # Cursor Composer 2 Standard tier. Known limitation: cached vs uncached
    # input distinction is not tracked — cache hits are 10x cheaper ($0.50/M)
    # but not reported separately.
    "cursor": {
        "input": env_rate("LARCH_RATE_CURSOR_INPUT", 0.50),
        "output": env_rate("LARCH_RATE_CURSOR_OUTPUT", 2.50),
        "aggregate": env_rate("LARCH_RATE_CURSOR_AGGREGATE", 0.20),
    },
    # Gemini 2.5 Pro. aggregate approximates hidden-token cost (e.g. cache-inclusive
    # totals where total > input + output); defaults to input rate.
    "gemini": {
        "input": env_rate("LARCH_RATE_GEMINI_INPUT", 1.25),
        "output": env_rate("LARCH_RATE_GEMINI_OUTPUT", 10.00),
        "aggregate": env_rate("LARCH_RATE_GEMINI_AGGREGATE", 1.25),
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
    if name.startswith("gemini"):
        return "gemini"
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


def normalize_step(step):
    step = re.sub(r"^\s*Step\s*", "", step, flags=re.IGNORECASE)
    step = re.sub(r"^\d+[a-z]?(?:\.\d+)?\s*[-:]\s*", "", step)
    step = re.sub(r"\s+", " ", step).strip()
    return step or "unknown"


def dollars(value):
    return f"${value:,.2f}"


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
        text_parts = [issue.get("body") or ""]
        comments = issue.get("comments") or []
        for comment in comments:
            text_parts.append(comment.get("body") or "")
        combined = "\n\n".join(text_parts)
        block = latest_token_block(combined)
        if not block:
            skipped += 1
            continue
        totals, phase_rows = parse_report(block)
        cost = total_cost(totals)
        workflow = parse_workflow_path(combined)
        closed_at = parse_date(issue.get("closedAt"))
        records.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title") or "",
                "url": issue.get("url") or "",
                "closed_at": closed_at,
                "workflow": workflow,
                "totals": totals,
                "phase_rows": phase_rows,
                "cost": cost,
            }
        )

    records.sort(key=lambda r: (r["closed_at"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), r["number"] or 0))
    return records, skipped


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
    ax.set_xlabel("Issue closed date")
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
        "- Codex (GPT-5.5) input={input:g}, output={output:g}, aggregate={aggregate:g}, cache_read={cache_read:g}".format(
            **RATES["codex"]
        )
    )
    print(
        "- Cursor (Composer 2) input={input:g}, output={output:g}, aggregate/cache={aggregate:g}".format(
            **RATES["cursor"]
        )
    )
    print(
        "- Gemini (2.5 Pro) input={input:g}, output={output:g}".format(
            **RATES["gemini"]
        )
    )
    print("")
    if not records:
        print("No parseable token reports found.")
        if skipped:
            print(f"Skipped issues without a parseable report: {skipped}")
        return

    dates = [r["closed_at"] for r in records if r["closed_at"]]
    costs = [r["cost"] for r in records]
    print(
        f"Parsed {len(records)} issue(s); skipped {skipped}. "
        f"Total estimated cost: {dollars(sum(costs))}; "
        f"median issue cost: {dollars(statistics.median(costs))}."
    )
    if dates:
        print(f"Closed date range: {min(dates).date()} to {max(dates).date()}.")
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
            f"- {workflow}: {len(rows)} issue(s), total {dollars(sum(values))}, "
            f"median {dollars(statistics.median(values))}, max {dollars(max(values))}"
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
    print("### Top SIMPLE issues by estimated cost")
    if simple:
        for r in simple:
            print(f"- #{r['number']} {dollars(r['cost'])} - {r['title']}")
    else:
        print("- No SIMPLE issues found.")

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
            "closed_at": parse_date(item.get("closed_at")),
            "cost": float(item.get("cost") or 0),
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
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            "cost": r["cost"],
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
    args = ["gh", "issue", "create", "--title", title, "--body", body]
    if repo:
        args += ["--repo", repo]
    result = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        print(f"\nAnalysis report issue created: {result.stdout.strip()}")
    else:
        print(f"\nWarning: failed to create analysis report issue: {result.stderr.strip()}", file=sys.stderr)


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

if [[ -n "$PLOT_FROM" ]]; then
    echo "Fetching analysis report issue #$PLOT_FROM..."
    ISSUE_BODY_FILE="$TMPROOT/plot-from-body.txt"
    gh issue view "$PLOT_FROM" --repo "$REPO" --json body --jq '.body' > "$ISSUE_BODY_FILE"
    python3 "$ANALYZER" --plot-from "$ISSUE_BODY_FILE"
    exit $?
fi

python3 "$ANALYZER" "$CACHE_JSON"
