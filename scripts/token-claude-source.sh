#!/usr/bin/env bash
# token-claude-source.sh — Resolve the live Claude transcript for this repo.

set -euo pipefail

unavailable() {
    printf 'STATUS=unavailable\n'
    printf 'REASON=%s\n' "$1"
    exit 1
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || unavailable "not inside a git repository"
repo_root=$(cd "$repo_root" 2>/dev/null && pwd -P) || unavailable "cannot canonicalize repo root"

encoded=$(printf '%s' "$repo_root" | sed 's#/#-#g')
project_dir="${HOME:-}/.claude/projects/$encoded"
[[ -n "${HOME:-}" ]] || unavailable "HOME is not set"
[[ -d "$project_dir" ]] || unavailable "Claude project directory not found"

shopt -s nullglob
transcripts=("$project_dir"/*.jsonl)
shopt -u nullglob
[[ "${#transcripts[@]}" -gt 0 ]] || unavailable "no Claude transcript jsonl files found"

latest=$(
    for f in "${transcripts[@]}"; do
        mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || printf '0')
        printf '%s\t%s\n' "$mtime" "$f"
    done | sort -nr | awk -F '\t' 'NR==1 { print $2 }'
) || true

[[ -n "$latest" && -f "$latest" ]] || unavailable "no Claude transcript jsonl files found"

base=${latest##*/}
uuid=${base%.jsonl}
session_dir="$project_dir/$uuid"

printf 'TRANSCRIPT_PATH=%s\n' "$latest"
printf 'SESSION_DIR=%s\n' "$session_dir"
printf 'SESSION_UUID=%s\n' "$uuid"
