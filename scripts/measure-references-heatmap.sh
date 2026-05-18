#!/usr/bin/env bash
# measure-references-heatmap.sh - Count markdown Read tool calls in session logs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
OUT_DIR="$REPO_ROOT/larch-logs/measure-references-heatmap"
STAMP="${LARCH_MEASURE_DATE:-$(date +%Y-%m-%d)}"
OUT_FILE="$OUT_DIR/$STAMP.tsv"

mkdir -p "$OUT_DIR"

python3 - "$REPO_ROOT" "$OUT_FILE" <<'PY'
import collections
import json
import os
import pathlib
import re
import sys
import tempfile

repo = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
counts = collections.Counter()

cache_re = re.compile(r"/larch/[^/]+/(.+)$")

def normalize_path(raw):
    if not isinstance(raw, str) or not raw.endswith(".md"):
        return None
    path = raw
    if path.startswith("<"):
        return None
    if path.startswith(str(repo) + "/"):
        path = path[len(str(repo)) + 1:]
    else:
        match = cache_re.search(path)
        if match:
            path = match.group(1)
    if path.startswith("/") or path.startswith("../") or "/../" in path:
        return None
    return path

def iter_tool_uses(obj):
    message = obj.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            yield item

for transcript in sorted((repo / "larch-logs").glob("*/*/session-transcript.jsonl")):
    with transcript.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            for tool in iter_tool_uses(obj):
                if tool.get("name") != "Read":
                    continue
                tool_input = tool.get("input")
                if not isinstance(tool_input, dict):
                    continue
                rel = normalize_path(tool_input.get("file_path"))
                if rel:
                    counts[rel] += 1

rows = []
for rel, count in counts.items():
    file_path = repo / rel
    size = file_path.stat().st_size if file_path.is_file() else 0
    rows.append((rel, count, size))
rows.sort(key=lambda row: (-row[1], -row[2], row[0]))

out_path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".tmp.measure-references-heatmap.", dir=str(out_path.parent), text=True)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("references_path\treads_observed\tbytes\n")
    for rel, count, size in rows:
        fh.write(f"{rel}\t{count}\t{size}\n")
os.replace(tmp_name, out_path)
PY

printf 'WROTE\t%s\n' "${OUT_FILE#"$REPO_ROOT"/}"
