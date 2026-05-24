#!/usr/bin/env python3
"""Parse reviewer sidecar TSVs from $DESIGN_TMPDIR and emit a deduped findings JSON.

Output JSON shape: {"in_scope": [{"id": "FINDING_1", "reviewers": [...], "focus_area": ..., "location": ..., "what": ..., "scenario_or_breakage": ..., "suggested_fix": ..., "severity": ...}, ...], "oos": [...]}
"""
import os
import sys
import csv
import json
import re
import hashlib
from collections import defaultdict

DESIGN_TMPDIR = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DESIGN_TMPDIR")
if not DESIGN_TMPDIR:
    print("DESIGN_TMPDIR required", file=sys.stderr)
    sys.exit(2)


def reviewer_name_from_filename(fname):
    # codex-primary-plan-arch-output.txt.tsv -> Codex-Arch
    # cursor-plan-arch-output-phase2.txt.tsv -> Cursor-Arch (fell back to codex but attributed by manifest slot)
    base = os.path.basename(fname)
    if base == "timing-ledger.tsv":
        return None
    m = re.match(r"^codex-primary-plan-(.+)-output\.txt\.tsv$", base)
    if m:
        arch = m.group(1)
        if arch.startswith("dyn-"):
            return f"Codex-dyn-{arch[4:]}"
        return f"Codex-{arch.capitalize()}"
    m = re.match(r"^cursor-plan-(.+)-output-phase2\.txt\.tsv$", base)
    if m:
        arch = m.group(1)
        if arch.startswith("dyn-"):
            return f"Cursor-dyn-{arch[4:]}"
        return f"Cursor-{arch.capitalize()}"
    return None


def normalize_what(what):
    # Lower, strip punctuation, collapse whitespace, take first 80 chars
    w = re.sub(r"[^\w\s]", " ", what.lower())
    w = re.sub(r"\s+", " ", w).strip()
    return w[:80]


def location_key(loc):
    # Normalize file path; collapse line ranges to first ~main token
    if not loc:
        return ""
    loc = loc.strip()
    # take first colon-separated piece (file path)
    m = re.match(r"^([^:;]+)", loc)
    if m:
        return m.group(1).strip()
    return loc


def dedupe_key(row):
    """Group by (focus_area, location-file, normalized-what-prefix)."""
    fa = (row.get("focus_area") or "").strip().lower()
    loc = location_key(row.get("location") or "")
    what_norm = normalize_what(row.get("what") or "")
    # Use first 40 chars of normalized 'what' for grouping
    return (fa, loc, what_norm[:40])


in_scope_rows = []
oos_rows = []

for fname in sorted(os.listdir(DESIGN_TMPDIR)):
    if not fname.endswith(".tsv"):
        continue
    reviewer = reviewer_name_from_filename(fname)
    if not reviewer:
        continue
    path = os.path.join(DESIGN_TMPDIR, fname)
    with open(path, "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh, delimiter="\t")
        for row in rdr:
            row["_reviewer"] = reviewer
            scope = (row.get("scope") or "").strip().lower()
            if scope == "in_scope":
                in_scope_rows.append(row)
            elif scope == "out_of_scope":
                oos_rows.append(row)


def cluster_rows(rows):
    """Cluster rows by dedupe_key, merge reviewers."""
    clusters = defaultdict(list)
    for r in rows:
        clusters[dedupe_key(r)].append(r)
    out = []
    for k, members in clusters.items():
        # Pick the row with the longest 'what' as the canonical
        canonical = max(members, key=lambda r: len(r.get("what") or ""))
        reviewers = sorted(set(r["_reviewer"] for r in members))
        # Severity: highest among members (blocking > important > nit)
        order = {"blocking": 3, "important": 2, "nit": 1, "": 0}
        severity = max((r.get("severity") or "").strip().lower() for r in members)
        # Pick max by severity rank
        sev_ranked = sorted(members, key=lambda r: order.get((r.get("severity") or "").strip().lower(), 0), reverse=True)
        severity = (sev_ranked[0].get("severity") or "").strip()
        out.append({
            "focus_area": canonical.get("focus_area", ""),
            "location": canonical.get("location", ""),
            "what": canonical.get("what", ""),
            "scenario_or_breakage": canonical.get("scenario_or_breakage", ""),
            "suggested_fix": canonical.get("suggested_fix", ""),
            "severity": severity,
            "reviewers": reviewers,
            "count": len(members),
        })
    # Sort: blocking first, then important, then nit; tiebreak by reviewer count desc
    sev_rank = {"blocking": 3, "important": 2, "nit": 1, "": 0}
    out.sort(key=lambda x: (-sev_rank.get(x["severity"].lower(), 0), -x["count"], x["focus_area"], x["location"]))
    return out


in_scope_clusters = cluster_rows(in_scope_rows)
oos_clusters = cluster_rows(oos_rows)

# Assign sequential IDs
for i, c in enumerate(in_scope_clusters, 1):
    c["id"] = f"FINDING_{i}"
for i, c in enumerate(oos_clusters, 1):
    c["id"] = f"OOS_{i}"

result = {
    "in_scope": in_scope_clusters,
    "oos": oos_clusters,
    "stats": {
        "in_scope_raw": len(in_scope_rows),
        "oos_raw": len(oos_rows),
        "in_scope_deduped": len(in_scope_clusters),
        "oos_deduped": len(oos_clusters),
    },
}

print(json.dumps(result, indent=2, ensure_ascii=False))
