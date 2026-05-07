#!/usr/bin/env bash
# token-claude-source.sh — Resolve the live Claude transcript for this repo.

set -euo pipefail

unavailable() {
    printf 'STATUS=unavailable\n'
    printf 'REASON=%s\n' "$1"
    exit 1
}

# Short-circuit on a sticky snapshot file written once at /implement Step 0
# (or any caller) BEFORE concurrent Claude sessions can race the resolver.
# When `LARCH_CLAUDE_SOURCE_FILE` is set to a readable file, parse and
# replay it. The snapshot SHOULD contain TRANSCRIPT_PATH=/SESSION_DIR=/
# SESSION_UUID= lines (this script's normal stdout). Any line that fails
# to parse as that grammar is silently skipped; a snapshot missing
# TRANSCRIPT_PATH falls through to the live resolver below as if the env
# var were unset, so a corrupted snapshot does not lock callers out.
if [[ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" && -r "$LARCH_CLAUDE_SOURCE_FILE" ]]; then
    snap_transcript=""
    snap_session_dir=""
    snap_session_uuid=""
    while IFS= read -r line; do
        case "$line" in
            TRANSCRIPT_PATH=*) snap_transcript="${line#TRANSCRIPT_PATH=}" ;;
            SESSION_DIR=*)     snap_session_dir="${line#SESSION_DIR=}" ;;
            SESSION_UUID=*)    snap_session_uuid="${line#SESSION_UUID=}" ;;
        esac
    done < "$LARCH_CLAUDE_SOURCE_FILE"
    if [[ -n "$snap_transcript" && -f "$snap_transcript" ]]; then
        printf 'TRANSCRIPT_PATH=%s\n' "$snap_transcript"
        printf 'SESSION_DIR=%s\n'     "$snap_session_dir"
        printf 'SESSION_UUID=%s\n'    "$snap_session_uuid"
        exit 0
    fi
fi

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

# Selection precedence:
#   1. $LARCH_CLAUDE_SESSION_ID matching `<id>.jsonl` in $project_dir.
#      This is an opt-in override an operator (or a future Step 0 hook
#      that learns Claude's actual session UUID) can set to bind the
#      ledger to a specific transcript.
#   2. $LARCH_TOKEN_SESSION_ID matching `<id>.jsonl` (legacy / convenience
#      override — same semantic). NOTE: /implement's Step 0 currently
#      sets this from the larch-side uuidgen value, which is NOT the
#      Claude transcript UUID, so this branch normally does NOT fire on
#      a default /implement run; it is here so an operator who manually
#      points it at a real Claude UUID is honored.
#   3. Newest-by-mtime jsonl in $project_dir. Documented limitation:
#      with concurrent Claude sessions in the same checkout this can
#      attribute tokens to the wrong run; a Step 0 transcript-snapshot
#      hook is the right durable fix and is tracked separately.
latest=""
# Restrict env-var session IDs to a safe charset before interpolating into a
# filesystem path. Values like `../foo` or paths containing slashes could
# otherwise resolve outside `~/.claude/projects/<encoded-repo>/`, letting an
# operator who exports a malformed session ID (typo, pasted UUID with
# slashes, untrusted env) attach token reporting to a transcript outside
# the intended directory. Allowed grammar: hex / underscore / hyphen, 1-128
# chars (covers UUIDv4 36-char, dashed-or-undashed; rejects empty, `..`,
# `/`, whitespace, control bytes). Names that don't match are silently
# skipped — same observable behavior as if the env var were unset, falling
# through to the mtime resolver.
for env_id in "${LARCH_CLAUDE_SESSION_ID:-}" "${LARCH_TOKEN_SESSION_ID:-}"; do
    if [[ -n "$env_id" ]]; then
        if [[ "$env_id" =~ ^[A-Za-z0-9_-]{1,128}$ ]]; then
            candidate="$project_dir/${env_id}.jsonl"
            if [[ -f "$candidate" ]]; then
                latest="$candidate"
                break
            fi
        fi
    fi
done

if [[ -z "$latest" ]]; then
    latest=$(
        for f in "${transcripts[@]}"; do
            mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || printf '0')
            printf '%s\t%s\n' "$mtime" "$f"
        done | sort -nr | awk -F '\t' 'NR==1 { print $2 }'
    ) || true
fi

[[ -n "$latest" && -f "$latest" ]] || unavailable "no Claude transcript jsonl files found"

base=${latest##*/}
uuid=${base%.jsonl}
session_dir="$project_dir/$uuid"

printf 'TRANSCRIPT_PATH=%s\n' "$latest"
printf 'SESSION_DIR=%s\n' "$session_dir"
printf 'SESSION_UUID=%s\n' "$uuid"
