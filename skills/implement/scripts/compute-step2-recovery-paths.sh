#!/usr/bin/env bash
# compute-step2-recovery-paths.sh — Recompute malformed-manifest recovery paths.

set -euo pipefail

usage() {
    echo "Usage: compute-step2-recovery-paths.sh --repo-root PATH --tmpdir PATH --prelaunch-porcelain PATH --postlaunch-porcelain PATH --prelaunch-digests PATH --out-file PATH" >&2
}

REPO_ROOT=""
TMPDIR_PATH=""
PRELAUNCH_PORCELAIN=""
POSTLAUNCH_PORCELAIN=""
PRELAUNCH_DIGESTS=""
OUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-root) REPO_ROOT="${2:?--repo-root requires a value}"; shift 2 ;;
        --tmpdir) TMPDIR_PATH="${2:?--tmpdir requires a value}"; shift 2 ;;
        --prelaunch-porcelain) PRELAUNCH_PORCELAIN="${2:?--prelaunch-porcelain requires a value}"; shift 2 ;;
        --postlaunch-porcelain) POSTLAUNCH_PORCELAIN="${2:?--postlaunch-porcelain requires a value}"; shift 2 ;;
        --prelaunch-digests) PRELAUNCH_DIGESTS="${2:?--prelaunch-digests requires a value}"; shift 2 ;;
        --out-file) OUT_FILE="${2:?--out-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "compute-step2-recovery-paths.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

for var in REPO_ROOT TMPDIR_PATH PRELAUNCH_PORCELAIN POSTLAUNCH_PORCELAIN PRELAUNCH_DIGESTS OUT_FILE; do
    if [[ -z "${!var}" ]]; then
        usage
        exit 2
    fi
done

python3 - "$REPO_ROOT" "$TMPDIR_PATH" "$PRELAUNCH_PORCELAIN" "$POSTLAUNCH_PORCELAIN" "$PRELAUNCH_DIGESTS" "$OUT_FILE" <<'PY'
import hashlib
import os
import sys

repo, tmpdir, pre_file, post_file, digest_file, out_file = sys.argv[1:7]


def parse(path):
    raw = open(path, "rb").read() if os.path.exists(path) else b""
    items = raw.split(b"\0")
    tuples = set()
    paths = set()
    i = 0
    while i < len(items):
        rec = items[i]
        i += 1
        if not rec:
            continue
        status = rec[:2].decode("ascii", "replace")
        rel = rec[3:].decode("utf-8", "surrogateescape")
        if "R" in status or "C" in status:
            if i < len(items):
                i += 1
        tuples.add((status, rel))
        paths.add(rel)
    return tuples, paths


pre_tuples, pre_paths = parse(pre_file)
post_tuples, _post_paths = parse(post_file)
digests = {}
if os.path.exists(digest_file):
    with open(digest_file, encoding="utf-8", errors="surrogateescape") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if "\t" in line:
                digest, rel = line.split("\t", 1)
                digests[rel] = digest

tmp_rel = None
try:
    repo_real = os.path.realpath(repo)
    tmp_real = os.path.realpath(tmpdir)
    if tmp_real == repo_real:
        tmp_rel = "."
    elif tmp_real.startswith(repo_real + os.sep):
        tmp_rel = os.path.relpath(tmp_real, repo_real)
except OSError:
    tmp_rel = None


def under_tmp(rel):
    if tmp_rel is None:
        return False
    return rel == tmp_rel or rel.startswith(tmp_rel.rstrip("/") + "/")


def current_digest(rel):
    full = os.path.join(repo, rel)
    try:
        with open(full, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return "missing"


candidates = []
for status, rel in sorted(post_tuples, key=lambda item: item[1]):
    if under_tmp(rel):
        continue
    include = False
    if (status, rel) not in pre_tuples:
        include = True
    elif rel in pre_paths:
        include = current_digest(rel) != digests.get(rel, "")
    if include and rel not in candidates:
        candidates.append(rel)

with open(out_file, "wb") as fh:
    for rel in candidates:
        fh.write(rel.encode("utf-8", "surrogateescape") + b"\0")

sys.exit(0 if candidates else 1)
PY
