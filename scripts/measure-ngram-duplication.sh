#!/usr/bin/env bash
# measure-ngram-duplication.sh - Find repeated markdown shingles in prompt-loaded files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
OUT_DIR="$REPO_ROOT/larch-logs/measure-ngram-duplication"
STAMP="${LARCH_MEASURE_DATE:-$(date +%Y-%m-%d)}"
OUT_FILE="$OUT_DIR/$STAMP.txt"

mkdir -p "$OUT_DIR"

python3 - "$REPO_ROOT" "$OUT_FILE" <<'PY'
import collections
import os
import pathlib
import re
import subprocess
import sys
import tempfile

repo = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
ngram_size = int(os.environ.get("LARCH_MEASURE_NGRAM_SIZE", "6"))
min_files = int(os.environ.get("LARCH_MEASURE_NGRAM_MIN_FILES", "3"))
limit = int(os.environ.get("LARCH_MEASURE_NGRAM_LIMIT", "50"))

def tracked(pattern):
    data = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z", pattern])
    return [p.decode("utf-8") for p in data.split(b"\0") if p]

def claude_roots():
    roots = ["CLAUDE.md"]
    claude = repo / "CLAUDE.md"
    if claude.exists():
        for line in claude.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                target = stripped[1:].split()[0]
                if target.endswith(".md") and not target.startswith("/"):
                    roots.append(target)
    return roots

files = []
seen = set()
for rel in claude_roots() + tracked("skills/*/SKILL.md") + tracked(".claude/skills/*/SKILL.md"):
    if rel not in seen and (repo / rel).is_file():
        seen.add(rel)
        files.append(rel)

word_re = re.compile(r"[A-Za-z0-9_./$:-]+")
occurrences = collections.Counter()
file_hits = collections.defaultdict(set)

for rel in files:
    text = (repo / rel).read_text(encoding="utf-8", errors="replace").lower()
    words = word_re.findall(text)
    for idx in range(0, max(0, len(words) - ngram_size + 1)):
        shingle = " ".join(words[idx:idx + ngram_size])
        occurrences[shingle] += 1
        file_hits[shingle].add(rel)

ranked = []
for shingle, count in occurrences.items():
    file_count = len(file_hits[shingle])
    if file_count >= min_files:
        ranked.append((count * ngram_size, count, file_count, shingle))
ranked.sort(key=lambda row: (-row[0], -row[1], row[3]))

out_path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".tmp.measure-ngram-duplication.", dir=str(out_path.parent), text=True)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("score\toccurrences\tfiles\tshingle\n")
    for score, count, file_count, shingle in ranked[:limit]:
        fh.write(f"{score}\t{count}\t{file_count}\t{shingle}\n")
os.replace(tmp_name, out_path)
PY

printf 'WROTE\t%s\n' "${OUT_FILE#"$REPO_ROOT"/}"
