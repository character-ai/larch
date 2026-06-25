"""Per-entity cost breakdown for /design and /implement runs, Codex split by role.

Scans committed ``larch-logs/{design,implement}/`` run directories whose
``started_at`` falls within the last ``--days`` days and reports, for each skill:

1. A complete table grouped by review-round count, with average cost and percent
   share for five entities: Claude, Codex-coder, Codex-reviewer, Codex-other, and
   Cursor.
2. A compressed single-row "average run" table (n-weighted across round counts).

Codex is treated as two separate entities. For /implement the split comes from
per-step token attribution (``Step 2 — implementation`` is the coder,
``Step 5 — code review`` is the reviewer, the rest is "other"). For /design it
comes from the committed token ledger ``raw`` labels (``codex_plan_draft`` is the
coder, ``codex_review`` is the reviewer).

``--force`` /implement runs are excluded entirely (they self-review with the
Claude main agent rather than a Codex reviewer panel). The Claude lane folds in
the ``claude_sub`` subprocess lane, priced at Claude rates.

Pricing uses larch's own display rates (``report_tokens_cost.display_rates``);
dollar figures are estimates, not billing truth.

Usage::

    python3 python/analysis/codex_role_costs.py --days 7
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

_PYTHON_DIR = Path(__file__).resolve().parent.parent
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

from report_tokens_cost import CODEX_MINI_MODEL, DisplayRates, display_rates  # noqa: E402

TOKENS_PER_M = 1_000_000
DEFAULT_DAYS = 30
MIN_REVIEW_ROUNDS = 1
CODER_STEP_PREFIX = "Step 2 "
REVIEWER_STEP_PREFIX = "Step 5 "
LEDGER_CODER_LABEL = "codex_plan_draft"
LEDGER_REVIEWER_LABEL = "codex_review"
SKILLS = ("design", "implement")
TOKEN_BASENAME = {"design": "token-report-final.json", "implement": "token-report.json"}
BUCKET_TOKEN_KEYS = (
    "input", "cache_read", "cached_input", "cache_create",
    "cache_create_5m", "cache_create_1h", "output",
)
FORCE_RE = re.compile(r"(?im)^\s*-\s*(?:Force|Emergency):\s*(true|false)\s*$")


@dataclass(frozen=True)
class RunCost:
    """Priced per-entity cost for one run, with its review-round group."""

    started: str
    group: int
    claude: float
    coder: float
    reviewer: float
    other: float
    cursor: float

    @property
    def total(self) -> float:
        return self.claude + self.coder + self.reviewer + self.other + self.cursor


# ---- JSON / value helpers -------------------------------------------------

def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _as_map(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _num(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _started_at(run_dir: Path) -> str:
    manifest = _as_map(_load_json(run_dir / "manifest.json"))
    started = manifest.get("started_at")
    return started if isinstance(started, str) else ""


# ---- Pricing --------------------------------------------------------------

def _claude_cost(bucket: dict[str, object], rates: DisplayRates) -> float:
    five_min = _num(bucket.get("cache_create_5m"))
    one_hour = _num(bucket.get("cache_create_1h"))
    legacy = _num(bucket.get("cache_create"))
    if not five_min and not one_hour and legacy:
        five_min = legacy
    return (
        _num(bucket.get("input")) / TOKENS_PER_M * rates.claude_input
        + _num(bucket.get("cache_read")) / TOKENS_PER_M * rates.claude_cache_read
        + five_min / TOKENS_PER_M * rates.claude_cache_create_5m
        + one_hour / TOKENS_PER_M * rates.claude_cache_create_1h
        + _num(bucket.get("output")) / TOKENS_PER_M * rates.claude_output
    )


def _codex_cost(bucket: dict[str, object], rates: DisplayRates, *, model: str = "") -> float:
    """Price a codex bucket at ``model``'s rates; gpt-5.4-mini vs the gpt-5.5 default."""
    if model == CODEX_MINI_MODEL:
        r_in, r_cached, r_out = rates.codex_mini_input, rates.codex_mini_cached_input, rates.codex_mini_output
    else:
        r_in, r_cached, r_out = rates.codex_input, rates.codex_cached_input, rates.codex_output
    cached = _num(bucket.get("cached_input")) + _num(bucket.get("cache_read"))
    return (
        _num(bucket.get("input")) / TOKENS_PER_M * r_in
        + cached / TOKENS_PER_M * r_cached
        + _num(bucket.get("output")) / TOKENS_PER_M * r_out
    )


def _codex_run_cost(report: dict[str, object], rates: DisplayRates) -> float:
    """Model-aware total codex cost: price each model's bucket at its own rate."""
    by_model = _as_map(report.get("BUCKETS_codex_by_model"))
    if by_model:
        return sum(_codex_cost(_as_map(mb), rates, model=model) for model, mb in by_model.items())
    return _codex_cost(_pick_bucket(report, "codex"), rates)


def _cursor_cost(bucket: dict[str, object], rates: DisplayRates) -> float:
    return (
        _num(bucket.get("input")) / TOKENS_PER_M * rates.cursor_input
        + _num(bucket.get("cache_read")) / TOKENS_PER_M * rates.cursor_cache_read
        + _num(bucket.get("output")) / TOKENS_PER_M * rates.cursor_output
    )


def _bucket_tokens(bucket: dict[str, object]) -> int:
    return sum(_num(bucket.get(key)) for key in BUCKET_TOKEN_KEYS)


def _pick_bucket(report: dict[str, object], vendor: str) -> dict[str, object]:
    """Prefer the BUCKETS_<vendor> split; fall back to <vendor>.totals."""
    buckets = _as_map(report.get(f"BUCKETS_{vendor}"))
    if _bucket_tokens(buckets):
        return buckets
    return _as_map(_as_map(report.get(vendor)).get("totals"))


def _codex_eff_per_token(report: dict[str, object], rates: DisplayRates) -> float:
    """Model-aware effective Codex $/token for the run, used to price per-step costs."""
    bucket = _pick_bucket(report, "codex")
    tokens = _bucket_tokens(bucket)
    if not tokens:
        return 0.0
    return _codex_run_cost(report, rates) / tokens


def _codex_step_cost(totals: dict[str, object], eff: float) -> float:
    # per_step totals carry no per-row model, so distribute the run's model-aware
    # effective $/token across steps by token share. Keeps the run total correct
    # under mixed models; for all-gpt-5.5 runs the step sum equals per-bucket pricing.
    tokens = _bucket_tokens(totals) or _num(totals.get("total"))
    return tokens * eff


def _lane_costs(report: dict[str, object], rates: DisplayRates) -> tuple[float, float]:
    """Return (claude_lane, cursor_lane); Claude folds in the claude_sub lane."""
    claude = _claude_cost(_pick_bucket(report, "claude"), rates) + _claude_cost(
        _pick_bucket(report, "claude_sub"), rates
    )
    return claude, _cursor_cost(_pick_bucket(report, "cursor"), rates)


# ---- Codex role attribution ----------------------------------------------

def _implement_roles(
    run_dir: Path, report: dict[str, object], rates: DisplayRates
) -> tuple[float, float, float]:
    _ = run_dir
    per_step = _as_map(report.get("codex")).get("per_step")
    eff = _codex_eff_per_token(report, rates)
    coder = reviewer = other = 0.0
    if not isinstance(per_step, list):
        return coder, reviewer, other
    for item in cast("list[object]", per_step):
        entry = _as_map(item)
        step = str(entry.get("step") or "")
        cost = _codex_step_cost(_as_map(entry.get("totals")), eff)
        if not cost:
            continue
        if step.startswith(CODER_STEP_PREFIX):
            coder += cost
        elif step.startswith(REVIEWER_STEP_PREFIX):
            reviewer += cost
        else:
            other += cost
    return coder, reviewer, other


def _single_ledger(run_dir: Path) -> Path | None:
    ledgers = [
        p for p in run_dir.glob("larch-tokens-*.jsonl")
        if p.is_file() and not p.is_symlink()
    ]
    return ledgers[0] if len(ledgers) == 1 else None


def _design_roles(run_dir: Path, rates: DisplayRates) -> tuple[float, float, float]:
    ledger = _single_ledger(run_dir)
    coder = reviewer = other = 0.0
    if ledger is None:
        return coder, reviewer, other
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        return coder, reviewer, other
    for line in lines:
        entry = _as_map(_load_json_line(line))
        if entry.get("type") != "vendor" or entry.get("vendor") != "codex":
            continue
        # Each ledger row carries its own model; price it at that model's rate so a
        # single role (e.g. reviewer) that mixes gpt-5.5 + gpt-5.4-mini is exact.
        cost = _codex_cost(entry, rates, model=str(entry.get("model") or ""))
        raw = str(entry.get("raw") or "")
        if raw == LEDGER_CODER_LABEL:
            coder += cost
        elif raw == LEDGER_REVIEWER_LABEL:
            reviewer += cost
        else:
            other += cost
    return coder, reviewer, other


def _load_json_line(line: str) -> object:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


# ---- Review-round grouping + force detection -------------------------

def _design_group(run_dir: Path) -> int:
    marker = run_dir / "review-round-count.txt"
    if marker.is_file():
        try:
            return int(marker.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
    rounds_dir = run_dir / "plan-review"
    return len(list(rounds_dir.glob("round-*"))) if rounds_dir.is_dir() else 0


def _implement_group(run_dir: Path) -> int | None:
    """Number of code-review rounds; None for degenerate/self-review-only runs."""
    tally = _as_map(_load_json(run_dir / "code-review-tally.json"))
    rounds = tally.get("rounds")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds >= MIN_REVIEW_ROUNDS:
        return rounds
    dirs = len(list(run_dir.glob("round-*")))
    return dirs if dirs >= MIN_REVIEW_ROUNDS else None


def _is_force(run_dir: Path) -> bool:
    summary = run_dir / "final-summary.md"
    if not summary.is_file():
        return False
    match = FORCE_RE.search(summary.read_text(encoding="utf-8", errors="replace"))
    return bool(match) and match.group(1).lower() == "true"


# ---- Per-run assembly + collection ---------------------------------------

def _build_run_cost(run_dir: Path, skill: str, rates: DisplayRates) -> RunCost | None:
    group = _design_group(run_dir) if skill == "design" else _implement_group(run_dir)
    if group is None:
        return None
    report = _as_map(_load_json(run_dir / TOKEN_BASENAME[skill]))
    if not report:
        return None
    claude, cursor = _lane_costs(report, rates)
    if skill == "design":
        coder, reviewer, other = _design_roles(run_dir, rates)
    else:
        coder, reviewer, other = _implement_roles(run_dir, report, rates)
    run_cost = RunCost(
        started=_started_at(run_dir), group=group, claude=claude,
        coder=coder, reviewer=reviewer, other=other, cursor=cursor,
    )
    return run_cost if run_cost.total else None


@dataclass(frozen=True)
class Collection:
    runs: tuple[RunCost, ...]
    skipped: int
    excluded: int
    window: tuple[str, str]


def collect(log_root: Path, skill: str, days: int, rates: DisplayRates) -> Collection:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    base = log_root / skill
    run_dirs = [p for p in base.glob("*") if p.is_dir() and not p.is_symlink()]
    runs: list[RunCost] = []
    skipped = excluded = 0
    for run_dir in run_dirs:
        parsed = _parse_dt(_started_at(run_dir))
        if parsed is None or parsed < cutoff:
            continue
        if skill == "implement" and _is_force(run_dir):
            excluded += 1
            continue
        run_cost = _build_run_cost(run_dir, skill, rates)
        if run_cost is None:
            skipped += 1
            continue
        runs.append(run_cost)
    runs.sort(key=lambda r: r.started)
    window = (runs[0].started, runs[-1].started) if runs else ("-", "-")
    return Collection(tuple(runs), skipped, excluded, window)


# ---- Rendering ------------------------------------------------------------

def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct(part: float, whole: float) -> float:
    return 100.0 * part / whole if whole else 0.0


def _means(runs: tuple[RunCost, ...]) -> tuple[float, float, float, float, float, float]:
    claude = _avg([r.claude for r in runs])
    coder = _avg([r.coder for r in runs])
    reviewer = _avg([r.reviewer for r in runs])
    other = _avg([r.other for r in runs])
    cursor = _avg([r.cursor for r in runs])
    return claude, coder, reviewer, other, cursor, claude + coder + reviewer + other + cursor


def _entity_row(label: str, runs: tuple[RunCost, ...]) -> str:
    claude, coder, reviewer, other, cursor, total = _means(runs)
    return (
        f"{label:>5} | {len(runs):>4} | {claude:>8.2f} | {coder:>8.2f} | {reviewer:>9.2f} | "
        f"{other:>8.2f} | {cursor:>8.2f} | {total:>8.2f} || "
        f"{_pct(claude, total):>4.1f}% {_pct(coder, total):>6.1f}% {_pct(reviewer, total):>6.1f}% "
        f"{_pct(other, total):>5.1f}% {_pct(cursor, total):>4.1f}%"
    )


_COMPLETE_HEADER = (
    f"{'rnds':>5} | {'runs':>4} | {'Claude$':>8} | {'cdCODER$':>8} | {'cdREVIEW$':>9} | "
    f"{'cdothr$':>8} | {'Cursor$':>8} | {'Total$':>8} || "
    f"{'Cl%':>5} {'cdCODE%':>6} {'cdREV%':>6} {'cdoth%':>5} {'Cu%':>4}"
)


def format_complete_table(skill: str, coll: Collection) -> str:
    note = " (--force excluded)" if skill == "implement" else ""
    lines = [
        f"### {skill} — per-entity cost by review-round count{note}",
        f"runs={len(coll.runs)}  window {coll.window[0]}..{coll.window[1]}  "
        f"(skipped {coll.skipped} w/o cost+round data; excluded {coll.excluded})",
        "",
        _COMPLETE_HEADER,
        "-" * len(_COMPLETE_HEADER),
    ]
    groups: dict[int, list[RunCost]] = {}
    for run in coll.runs:
        groups.setdefault(run.group, []).append(run)
    lines.extend(_entity_row(str(group), tuple(groups[group])) for group in sorted(groups))
    lines.append("-" * len(_COMPLETE_HEADER))
    lines.append(_entity_row("ALL", coll.runs))
    return "\n".join(lines)


def format_compressed_row(skill: str, coll: Collection) -> str:
    claude, coder, reviewer, other, cursor, total = _means(coll.runs)

    def cell(value: float) -> str:
        return f"${value:.2f} ({_pct(value, total):.1f}%)"

    header = (
        f"{'Claude':>16} | {'Codex-coder':>16} | {'Codex-reviewer':>16} | "
        f"{'Codex-other':>16} | {'Cursor':>16} | {'Total':>9}"
    )
    row = (
        f"{cell(claude):>16} | {cell(coder):>16} | {cell(reviewer):>16} | "
        f"{cell(other):>16} | {cell(cursor):>16} | {('$' + format(total, '.2f')):>9}"
    )
    return "\n".join([
        f"### {skill} — average run (n-weighted across round counts, N={len(coll.runs)})",
        header,
        "-" * len(header),
        row,
    ])


def _default_repo_root() -> Path:
    return _PYTHON_DIR.parent


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="codex_role_costs.py",
        description="Per-entity (Codex coder vs reviewer) cost tables for recent runs.",
    )
    _ = parser.add_argument(
        "--days", type=int, default=DEFAULT_DAYS,
        help=f"Look back this many days by started_at (default: {DEFAULT_DAYS}).",
    )
    _ = parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Repository root containing larch-logs/ (default: inferred).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    days = int(args.days)
    if days <= 0:
        print("error: --days must be a positive integer", file=sys.stderr)
        return 2
    repo_root = cast("Path | None", args.repo_root) or _default_repo_root()
    log_root = repo_root / "larch-logs"
    if not log_root.is_dir():
        print(f"error: no larch-logs/ under {repo_root}", file=sys.stderr)
        return 2
    rates = display_rates()
    print(f"# Codex coder-vs-reviewer cost report — last {days} days")
    print("# Rates are larch display estimates, not billing truth. "
          "Claude lane includes claude_sub.\n")
    for skill in SKILLS:
        coll = collect(log_root, skill, days, rates)
        print(format_complete_table(skill, coll))
        print()
        print(format_compressed_row(skill, coll))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
