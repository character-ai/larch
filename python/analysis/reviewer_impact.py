"""Measure each review vendor's UNIQUE accepted contribution, given its peers.

Question answered
-----------------
Across committed ``/implement`` run logs, how many findings did a given vendor
(``claude`` | ``codex`` | ``cursor``) get ACCEPTED that none of the other
vendors present in the same review independently raised -- broken down by
importance (severity)? With no ``--vendor`` the report covers all three.

Method (and why each choice)
----------------------------
1. Source of truth per run is ``larch-logs/implement/<RUN_ID>/``:
   - ``review-findings-full.jsonl`` -- one row per finding: ``phase``,
     ``outcome`` (accepted|rejected|out_of_scope), ``reviewer_slots``
     (proposer attribution AFTER larch's intra-run dedup), ``round_num``,
     ``prose_body``.
   - ``round-<N>/panel-manifest.ndjson`` -- maps every reviewer-slot output
     basename to its TOOL. This is the authority that resolves tool-agnostic
     ``dyn-*`` slots and tells us which tools were PRESENT in a run.
   - ``round-<N>/findings-classification.tsv`` -- per (round, finding_id) the
     voters' votes and assigned severities; source of the PANEL severity.

2. "Accepted only" means ``outcome == "accepted"`` (in-scope, implemented).
   Out-of-scope items carry ``outcome == "out_of_scope"`` and are excluded.

3. "Unique to vendor V" uses larch's own intra-run dedup: independently-raised
   duplicates are merged into one finding whose ``reviewer_slots`` lists every
   proposer. So a finding is V-unique when its resolved proposer set contains V
   and contains no other vendor. Cross-run semantic matching is intentionally
   NOT attempted -- "the others did not raise this" only means anything within
   the same review of the same diff.

4. "Given peers present" anchors the head-to-head count on runs where V AND at
   least one other vendor reviewed (presence read from panel-manifest tools).
   A realized rate over every run with a peer present (V may be absent there,
   contributing zero) is also reported, exposing the cost of sporadic vendor
   availability.

5. Importance level is the PANEL severity: the severity the accepting voters
   (vote YES) assigned, taken as the modal value (ties break high), bucketed
   blocker > major > minor > nit. Falls back to the modal over all voters when
   no YES-voter severity parses. This is the consensus importance and matches
   larch's own +2 scoring threshold (blocker/major). The reviewer's self-label
   from the finding body is reported as a secondary view.

Caveats surfaced in the report: gc-slimmed runs (no round artifacts, so not
attributable), opaque legacy ``panel`` rows (no per-proposer breakdown), and
findings whose attribution stays ambiguous after manifest + heuristic resolution.

Stdlib only. Read-only over the committed logs. Run directly:

    python3 python/analysis/reviewer_impact.py [--vendor codex] [--json]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

VENDORS: tuple[str, ...] = ("claude", "codex", "cursor")
PANEL_ORDER: dict[str, int] = {"blocker": 3, "major": 2, "minor": 1, "nit": 0}
PANEL_BUCKETS: tuple[str, ...] = ("blocker", "major", "minor", "nit", "unknown")
PROSE_TOKENS: tuple[str, ...] = ("blocking", "important", "latent", "nit")
PROSE_BUCKETS: tuple[str, ...] = (*PROSE_TOKENS, "(unlabeled)")

DEFAULT_ROOT = "larch-logs/implement"
DEFAULT_EXAMPLES = 12

PROSE_SEV_RE = re.compile(r"\*\*Severity\*\*:\s*([A-Za-z]+)")
SPECIALIST_RE = re.compile(r"(?:codex|cursor)-specialist-(.+?)-output\.txt")
ROUND_RE = re.compile(r"round-(\d+)")

VoteRow = list[tuple[str, str]]          # [(vote, severity), ...] for the voter slots
TsvMap = dict[str, VoteRow]              # finding_id -> voter rows
RoundTsvs = dict[str, TsvMap]            # round number -> tsv map


@dataclass(frozen=True)
class Coverage:
    runs_total: int
    runs_with_findings: int
    runs_with_manifest: int
    runs_gc_slimmed: int


@dataclass(frozen=True)
class Finding:
    run_id: str
    present: frozenset[str]               # vendors present in the run
    proposers: frozenset[str]             # resolved vendor proposers
    opaque: bool                          # at least one unresolved/opaque slot
    panel_severity: str
    prose_severity: str
    focus: tuple[tuple[str, str], ...]    # (vendor, focus-area) per resolved slot
    finding_id: str
    round_num: str
    category: str


@dataclass(frozen=True)
class Dataset:
    coverage: Coverage
    run_present: dict[str, frozenset[str]]
    findings: tuple[Finding, ...]
    opaque_accepted: int                  # accepted rows with no attributable proposer


@dataclass(frozen=True)
class RunCounts:
    head_to_head: int                     # V present AND >=1 peer present
    realized: int                         # >=1 peer present (V may be absent)
    with_unique: int                      # head-to-head runs with >=1 V-unique find


@dataclass(frozen=True)
class Venn:
    unique: int                           # V proposed, no peer proposed
    shared: int                           # V proposed AND a peer proposed
    ambiguous: int                        # V-unique shape but an opaque slot remains


@dataclass(frozen=True)
class VendorSummary:
    vendor: str
    runs: RunCounts
    venn: Venn
    panel_severity: dict[str, int]
    prose_severity: dict[str, int]
    focus: dict[str, int]
    examples: tuple[Finding, ...]


def _strip_legacy(label: str) -> str:
    return label[len("legacy:"):] if label.lower().startswith("legacy:") else label


def resolve_tool(label: str, manifest_map: dict[str, str]) -> str:
    """Resolve one reviewer-slot label to a tool, ``unknown`` when opaque.

    The run's panel-manifest is authoritative. The heuristic fallback (for
    gc-slimmed or legacy runs without a manifest) follows the slot naming
    convention and deliberately checks ``dyn-`` BEFORE substring matching, so a
    dynamic slot whose archetype name mentions a tool as its review *subject*
    (e.g. ``dyn-lint-claude``) is not misread as that tool.
    """
    raw = _strip_legacy(label)
    mapped = manifest_map.get(raw)
    if mapped:
        return mapped
    low = raw.lower()
    if low == "panel":
        return "unknown"
    if low.startswith("dyn-"):
        return "codex" if low.endswith("-codex-output.txt") else "cursor"
    for vendor in ("codex", "cursor", "claude"):
        if low.startswith(vendor):
            return vendor
    return "unknown"


def slot_focus(label: str) -> str:
    """Best-effort focus area for a reviewer slot (for the by-slot breakdown)."""
    raw = _strip_legacy(label)
    match = SPECIALIST_RE.match(raw)
    if match:
        return match.group(1)
    if "generalist" in raw:
        return "generalist"
    if "generic" in raw:
        return "generic"
    if raw.startswith("dyn-"):
        return "dynamic"
    return "other"


def load_manifest_map(run_dir: Path) -> dict[str, str]:
    """basename(output) -> tool, unioned across every round of one run."""
    mapping: dict[str, str] = {}
    for manifest in run_dir.glob("round-*/panel-manifest.ndjson"):
        for obj in _iter_json_lines(manifest):
            output = obj.get("output")
            tool = obj.get("tool")
            if isinstance(output, str) and isinstance(tool, str) and output and tool:
                mapping[Path(output).name] = tool
    return mapping


def parse_round_tsv(path: Path) -> TsvMap:
    """finding_id -> the three voter (vote, severity) pairs for one round."""
    out: TsvMap = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            rows = list(csv.reader(handle, delimiter="\t"))
    except OSError:
        return out
    if not rows:
        return out
    index = {name: pos for pos, name in enumerate(rows[0])}
    if "finding_id" not in index:
        return out

    def cell(row: list[str], name: str) -> str:
        pos = index.get(name)
        if pos is None or pos >= len(row):
            return ""
        return (row[pos] or "").strip()

    for row in rows[1:]:
        if not row:
            continue
        fid = cell(row, "finding_id")
        if not fid:
            continue
        out[fid] = [
            (cell(row, f"v{slot}_vote").upper(), cell(row, f"v{slot}_severity").lower())
            for slot in ("1", "2", "3")
        ]
    return out


def modal_severity(severities: list[str]) -> str | None:
    """Most common severity; ties break toward the higher severity."""
    ranked = [sev for sev in severities if sev in PANEL_ORDER]
    if not ranked:
        return None
    counts = Counter(ranked)
    top = max(counts.values())
    tied = [sev for sev, count in counts.items() if count == top]
    return max(tied, key=lambda sev: PANEL_ORDER[sev])


def panel_severity(finding_id: str, round_num: str, run_tsvs: RoundTsvs) -> str:
    """Bucket the accepting voters' consensus severity for one finding."""
    rows: VoteRow | None = None
    key = round_num.strip()
    if key and key in run_tsvs:
        rows = run_tsvs[key].get(finding_id)
    if rows is None:
        for tsv in run_tsvs.values():
            if finding_id in tsv:
                rows = tsv[finding_id]
                break
    if rows is None:
        return "unknown"
    yes = [sev for (vote, sev) in rows if vote == "YES"]
    bucket = modal_severity(yes) or modal_severity([row[1] for row in rows])
    return bucket or "unknown"


def prose_severity(prose_body: str) -> str:
    """The reviewer's self-assigned severity token from the finding body."""
    match = PROSE_SEV_RE.search(prose_body or "")
    if not match:
        return "(unlabeled)"
    token = match.group(1).lower()
    return token if token in PROSE_TOKENS else "(unlabeled)"


def _iter_json_lines(path: Path) -> list[dict[str, Any]]:
    objs: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                obj = _load_obj(stripped)
                if obj is not None:
                    objs.append(obj)
    except OSError:
        return objs
    return objs


def _load_obj(line: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return cast("dict[str, Any]", parsed)
    return None


def _slot_labels(obj: dict[str, Any]) -> list[str]:
    raw = obj.get("reviewer_slots")
    if isinstance(raw, list) and raw:
        return [str(item) for item in cast("list[Any]", raw)]
    legacy = obj.get("reviewer")
    return [str(legacy)] if isinstance(legacy, str) and legacy else []


def _classify_proposers(
    labels: list[str], manifest_map: dict[str, str]
) -> tuple[frozenset[str], bool, tuple[tuple[str, str], ...]]:
    kinds: set[str] = set()
    focus: list[tuple[str, str]] = []
    opaque = False
    for label in labels:
        tool = resolve_tool(label, manifest_map)
        if tool in VENDORS:
            kinds.add(tool)
            focus.append((tool, slot_focus(label)))
        else:
            opaque = True
    return frozenset(kinds), opaque, tuple(focus)


def _build_finding(
    obj: dict[str, Any],
    present: frozenset[str],
    manifest_map: dict[str, str],
    run_tsvs: RoundTsvs,
    run_id: str,
) -> Finding | None:
    if obj.get("phase") != "code-review" or obj.get("outcome") != "accepted":
        return None
    labels = _slot_labels(obj)
    if not labels:
        return None
    kinds, opaque, focus = _classify_proposers(labels, manifest_map)
    fid = str(obj.get("id") or "")
    round_num = str(obj.get("round_num") or "")
    return Finding(
        run_id=run_id,
        present=present,
        proposers=kinds,
        opaque=opaque,
        panel_severity=panel_severity(fid, round_num, run_tsvs),
        prose_severity=prose_severity(str(obj.get("prose_body") or "")),
        focus=focus,
        finding_id=fid,
        round_num=round_num,
        category=str(obj.get("category") or ""),
    )


def _scan_run(run_dir: Path) -> tuple[frozenset[str], list[Finding], int, bool, bool]:
    manifest_map = load_manifest_map(run_dir)
    present = frozenset(manifest_map.values()) & frozenset(VENDORS)
    findings_path = run_dir / "review-findings-full.jsonl"
    has_findings = findings_path.exists()
    if not has_findings:
        return present, [], 0, bool(manifest_map), False
    run_tsvs: RoundTsvs = {}
    for tsv in run_dir.glob("round-*/findings-classification.tsv"):
        match = ROUND_RE.search(tsv.parent.name)
        if match:
            run_tsvs[match.group(1)] = parse_round_tsv(tsv)
    findings: list[Finding] = []
    opaque_accepted = 0
    for obj in _iter_json_lines(findings_path):
        finding = _build_finding(obj, present, manifest_map, run_tsvs, run_dir.name)
        if finding is None:
            continue
        if not finding.proposers:
            opaque_accepted += 1
            continue
        findings.append(finding)
    return present, findings, opaque_accepted, bool(manifest_map), True


def scan(root: Path) -> Dataset:
    """Walk every run directory once and collect attributable accepted findings."""
    run_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    run_present: dict[str, frozenset[str]] = {}
    findings: list[Finding] = []
    runs_with_findings = 0
    runs_with_manifest = 0
    runs_gc_slimmed = 0
    opaque_accepted = 0
    for run_dir in run_dirs:
        if (run_dir / "gc-slimmed").exists():
            runs_gc_slimmed += 1
        present, run_findings, run_opaque, has_manifest, has_findings = _scan_run(run_dir)
        run_present[run_dir.name] = present
        if has_manifest:
            runs_with_manifest += 1
        if has_findings:
            runs_with_findings += 1
        findings.extend(run_findings)
        opaque_accepted += run_opaque
    coverage = Coverage(
        runs_total=len(run_dirs),
        runs_with_findings=runs_with_findings,
        runs_with_manifest=runs_with_manifest,
        runs_gc_slimmed=runs_gc_slimmed,
    )
    return Dataset(
        coverage=coverage,
        run_present=run_present,
        findings=tuple(findings),
        opaque_accepted=opaque_accepted,
    )


def _peers(present: frozenset[str], vendor: str) -> frozenset[str]:
    return present & (frozenset(VENDORS) - {vendor})


def summarize(data: Dataset, vendor: str, max_examples: int) -> VendorSummary:
    """Aggregate vendor V's unique accepted contribution and its breakdowns."""
    head_to_head = sum(
        1 for present in data.run_present.values()
        if vendor in present and _peers(present, vendor)
    )
    realized = sum(1 for present in data.run_present.values() if _peers(present, vendor))
    others = frozenset(VENDORS) - {vendor}
    unique = shared = ambiguous = 0
    panel: Counter[str] = Counter()
    prose: Counter[str] = Counter()
    focus: Counter[str] = Counter()
    runs_with_unique: set[str] = set()
    examples: list[Finding] = []
    for finding in data.findings:
        if vendor not in finding.present or not _peers(finding.present, vendor):
            continue  # only head-to-head runs
        if vendor not in finding.proposers:
            continue
        if finding.proposers & others:
            shared += 1
            continue
        if finding.opaque:
            ambiguous += 1  # an unresolved slot could hide a peer
            continue
        unique += 1
        runs_with_unique.add(finding.run_id)
        panel[finding.panel_severity] += 1
        prose[finding.prose_severity] += 1
        for proposer, area in finding.focus:
            if proposer == vendor:
                focus[area] += 1
        if len(examples) < max_examples:
            examples.append(finding)
    return VendorSummary(
        vendor=vendor,
        runs=RunCounts(head_to_head=head_to_head, realized=realized, with_unique=len(runs_with_unique)),
        venn=Venn(unique=unique, shared=shared, ambiguous=ambiguous),
        panel_severity=dict(panel),
        prose_severity=dict(prose),
        focus=dict(focus),
        examples=tuple(examples),
    )


def _pct(num: int, den: int) -> str:
    return f"{100.0 * num / den:.1f}%" if den else "n/a"


def _rate(num: int, den: int) -> str:
    return f"{num / den:.2f}" if den else "n/a"


def _render_coverage(data: Dataset, lines: list[str]) -> None:
    cov = data.coverage
    lines.append("## Data coverage")
    lines.append(f"  implement run dirs scanned ........ {cov.runs_total}")
    lines.append(f"  runs with review findings ......... {cov.runs_with_findings}")
    lines.append(f"  runs with panel manifest .......... {cov.runs_with_manifest}  (attribution-capable)")
    lines.append(f"  gc-slimmed runs (not attributable). {cov.runs_gc_slimmed}")
    lines.append(f"  opaque legacy `panel` accepted rows {data.opaque_accepted}  (no proposer breakdown)")


def _render_availability(data: Dataset, lines: list[str]) -> None:
    present_counts: dict[str, int] = dict.fromkeys(VENDORS, 0)
    for present in data.run_present.values():
        for vendor in present:
            present_counts[vendor] += 1
    lines.append("")
    lines.append("## Reviewer availability (per run, from panel manifests)")
    lines.extend(
        f"  {vendor:<7} present ................... {present_counts[vendor]}"
        for vendor in VENDORS
    )


def _render_comparison(summaries: list[VendorSummary], lines: list[str]) -> None:
    lines.append("")
    lines.append("## Unique accepted findings by vendor (each vs its peers, head-to-head)")
    lines.append(f"  {'vendor':<8}{'h2h runs':>10}{'unique':>9}{'shared':>9}{'/run':>8}")
    lines.extend(
        f"  {summ.vendor:<8}{summ.runs.head_to_head:>10}{summ.venn.unique:>9}"
        f"{summ.venn.shared:>9}{_rate(summ.venn.unique, summ.runs.head_to_head):>8}"
        for summ in summaries
    )


def _render_severity(title: str, buckets: tuple[str, ...], counts: dict[str, int], lines: list[str]) -> None:
    total = sum(counts.values())
    lines.append(f"  {title}")
    for bucket in buckets:
        count = counts.get(bucket, 0)
        lines.append(f"    {bucket:<11}{count:>6}  ({_pct(count, total)})")
    lines.append(f"    {'TOTAL':<11}{total:>6}")


def _render_vendor(summ: VendorSummary, peers_unique: int, lines: list[str]) -> None:
    venn, runs = summ.venn, summ.runs
    lines.append("")
    lines.append(f"## {summ.vendor.upper()} -- unique accepted contribution")
    if runs.head_to_head == 0:
        lines.append("  Never reviewed alongside a peer in these logs (head-to-head runs: 0).")
        return
    lines.append(
        f"  {venn.unique} accepted findings only {summ.vendor} raised, across "
        f"{runs.head_to_head} head-to-head runs ({_rate(venn.unique, runs.head_to_head)}/run)."
    )
    lines.append(
        f"  Landed >=1 unique accepted finding in {runs.with_unique}/{runs.head_to_head} runs "
        f"({_pct(runs.with_unique, runs.head_to_head)})."
    )
    lines.append(
        f"  Realized across all {runs.realized} runs with a peer present: "
        f"{_rate(venn.unique, runs.realized)}/run "
        f"({summ.vendor} absent in {runs.realized - runs.head_to_head} of them -> 0 there)."
    )
    lines.append(f"  Overlap with peers (both proposed): {venn.shared}.")
    if venn.ambiguous:
        lines.append(f"  Ambiguous attribution excluded: {venn.ambiguous}.")
    if peers_unique:
        lines.append(f"  Weight vs peers: {_pct(venn.unique, venn.unique + peers_unique)} "
                     f"of all single-vendor-unique accepted findings came only from {summ.vendor}.")
    lines.append("")
    _render_severity("by IMPORTANCE (panel-vote severity):", PANEL_BUCKETS, summ.panel_severity, lines)
    lines.append("")
    _render_severity("by reviewer-assigned severity (secondary):", PROSE_BUCKETS, summ.prose_severity, lines)
    if summ.focus:
        lines.append("  by reviewer slot / focus area:")
        for area, count in sorted(summ.focus.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"    {area:<18}{count:>6}")
    if summ.examples:
        lines.append("  examples:")
        lines.extend(
            f"    [{ex.run_id[:8]}] {ex.finding_id} r{ex.round_num}  "
            f"<{ex.panel_severity}>  {ex.category[:72]}"
            for ex in summ.examples
        )


def render(data: Dataset, summaries: list[VendorSummary], requested: list[str]) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("REVIEWER IMPACT -- unique accepted contribution per vendor, given peers")
    lines.append("=" * 72)
    _render_coverage(data, lines)
    _render_availability(data, lines)
    _render_comparison(summaries, lines)
    by_vendor = {summ.vendor: summ for summ in summaries}
    for vendor in requested:
        summ = by_vendor[vendor]
        peers_unique = sum(other.venn.unique for other in summaries if other.vendor != vendor)
        _render_vendor(summ, peers_unique, lines)
    lines.append("")
    return "\n".join(lines)


def _summary_json(summ: VendorSummary) -> dict[str, Any]:
    return {
        "vendor": summ.vendor,
        "head_to_head_runs": summ.runs.head_to_head,
        "realized_runs": summ.runs.realized,
        "runs_with_unique": summ.runs.with_unique,
        "unique": summ.venn.unique,
        "shared": summ.venn.shared,
        "ambiguous": summ.venn.ambiguous,
        "unique_by_panel_severity": summ.panel_severity,
        "unique_by_prose_severity": summ.prose_severity,
        "unique_by_slot": summ.focus,
    }


def to_json(data: Dataset, summaries: list[VendorSummary], requested: list[str]) -> str:
    by_vendor = {summ.vendor: summ for summ in summaries}
    payload: dict[str, Any] = {
        "coverage": {
            "runs_total": data.coverage.runs_total,
            "runs_with_findings": data.coverage.runs_with_findings,
            "runs_with_manifest": data.coverage.runs_with_manifest,
            "runs_gc_slimmed": data.coverage.runs_gc_slimmed,
            "opaque_accepted_rows": data.opaque_accepted,
        },
        "vendors": [_summary_json(by_vendor[vendor]) for vendor in requested],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Per-vendor unique accepted review contribution from larch /implement run logs.",
    )
    _ = parser.add_argument("--vendor", choices=VENDORS, help="restrict the report to one vendor (default: all)")
    _ = parser.add_argument("--root", default=DEFAULT_ROOT, help=f"implement run-log root (default: {DEFAULT_ROOT})")
    _ = parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    _ = parser.add_argument("--examples", type=int, default=DEFAULT_EXAMPLES, help="example findings per vendor")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    requested: list[str] = [args.vendor] if args.vendor else list(VENDORS)
    max_examples = max(0, int(args.examples))
    data = scan(root)
    summaries = [summarize(data, vendor, max_examples) for vendor in VENDORS]
    if args.json:
        print(to_json(data, summaries, requested))
    else:
        print(render(data, summaries, requested))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
