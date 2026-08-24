#!/usr/bin/env python3
"""Strict-partition guard for multi-target pytest harness files.

For each explicit pytest source file sliced across several `test-harnesses`
Makefile targets, assert that the selections form a strict partition. The
Rust migration retired every previously sliced Python runtime test, so the
enforced set is empty until a surviving development-tooling test is sliced.

Invoked from scripts/test-harness-shards-coverage.sh (rides the
`test-harness-shards-coverage` harness target, already in `make lint`).
Runs `python3 -m pytest --co` per selection, so it requires pytest and the
test dependencies on PATH (true on the test-harnesses shard that owns it).
"""
import os
import re
import shlex
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
MAKEFILE = os.path.join(REPO_ROOT, "Makefile")

# Source files whose harness targets must strictly partition the file.
# Add a repo-relative path when a surviving file is split across targets.
ENFORCED: tuple[str, ...] = ()

# Mirrors CARVE_OUTS in scripts/test-harness-shards-coverage.sh: targets that
# are deliberately not part of the test-harnesses aggregate.
CARVE = {
    "test-eval-set-structure",
    "test-eval-research-baseline-flag",
    "test-review-and-fix",
    "test-stall-recovery-report",
}


def parse_targets(makefile):
    """Map each test-* recipe target to its (tab-indented) recipe lines."""
    targets = {}
    cur = None
    with open(makefile, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^(test-[^\s:]+):", line)
            if match:
                cur = match.group(1)
                targets.setdefault(cur, [])
                continue
            if line.startswith("\t"):
                if cur:
                    targets[cur].append(line.rstrip("\n"))
            else:
                cur = None
    return targets


def extract_pytest(recipe_lines):
    """Return (repo_relative_file, kexpr, [node_ids]) for a pytest recipe."""
    for raw in recipe_lines:
        if "pytest" not in raw:
            continue
        text = raw
        cwd = "repo"
        wrapped = re.search(r"sh -c '([^']*)'", text)
        if wrapped:
            text = wrapped.group(1)
        if "cd python &&" in text or "cd python&&" in text:
            cwd = "python"
        after = text[text.find("pytest") + len("pytest"):]
        after = after.replace("$(PYTHON)", "python3").replace("$@", "LABEL")
        try:
            toks = shlex.split(after)
        except ValueError:
            toks = after.split()
        files, nodeids, kexpr = [], [], None
        j = 0
        while j < len(toks):
            tok = toks[j]
            if tok == "-k" and j + 1 < len(toks):
                kexpr = toks[j + 1]
                j += 2
                continue
            if "::" in tok:
                nodeids.append(tok)
            elif tok.endswith(".py"):
                files.append(tok)
            j += 1
        if not files and not nodeids:
            continue
        fpath = files[0] if files else nodeids[0].split("::")[0]
        if cwd == "python" and not fpath.startswith("python/"):
            fpath = "python/" + fpath
        return (fpath, kexpr, nodeids)
    return None


def collect(fpath, kexpr, nodeids):
    """Return the set of node-ids a selection collects (pytest --co)."""
    if nodeids:
        args = ["python3", "-m", "pytest", "--co", "-q"] + nodeids
    else:
        args = ["python3", "-m", "pytest", "--co", "-q", fpath]
        if kexpr:
            args += ["-k", kexpr]
    proc = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)
    return set(line for line in proc.stdout.splitlines() if "::" in line)


def group_targets_by_file(makefile):
    byfile = {}
    for name, recipe in parse_targets(makefile).items():
        if name in CARVE or re.match(r"^test-harnesses(-\d+)?$", name):
            continue
        result = extract_pytest(recipe)
        if result:
            fpath, kexpr, nodeids = result
            byfile.setdefault(fpath, []).append((name, kexpr, nodeids))
    return byfile


def check_file(fpath, tlist):
    """Return a failure message string, or None when fpath strictly partitions."""
    if not tlist:
        return f"{fpath}: ENFORCED but no test-harnesses target runs it"
    full = collect(fpath, None, None)
    if not full:
        return f"{fpath}: pytest collected 0 tests (missing file or import error?)"
    union, overlap, rows = set(), set(), []
    for name, kexpr, nodeids in sorted(tlist):
        selected = collect(fpath, kexpr, nodeids)
        overlap |= union & selected
        union |= selected
        sel = f"-k {kexpr}" if kexpr else (f"{len(nodeids)} node-ids" if nodeids else "FULL-FILE")
        rows.append(f"    {name}: {sel} -> {len(selected)} tests")
    uncovered = full - union
    extra = union - full
    if not (overlap or uncovered or extra):
        return None
    msg = [f"{fpath}: NOT a strict partition (full={len(full)} union={len(union)} targets={len(tlist)})"]
    msg.extend(rows)
    if overlap:
        msg.append(f"    covered by >1 target: {sorted(overlap)[:8]}")
    if uncovered:
        msg.append(f"    not covered by any target: {sorted(uncovered)[:8]}")
    if extra:
        msg.append(f"    selected but not present in file: {sorted(extra)[:8]}")
    return "\n".join(msg)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    makefile = argv[0] if argv else MAKEFILE  # optional override for testing
    byfile = group_targets_by_file(makefile)
    failures = [m for m in (check_file(f, byfile.get(f, [])) for f in ENFORCED) if m]
    if failures:
        print("harness pytest partition guard: FAILED", file=sys.stderr)
        for failure in failures:
            print("- " + failure, file=sys.stderr)
        return 1
    print(f"harness pytest partition guard: OK ({len(ENFORCED)} enforced files partition cleanly)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
