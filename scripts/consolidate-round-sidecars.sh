#!/usr/bin/env bash
# consolidate-round-sidecars.sh — retroactive sweep: convert committed round
# directories from individual sidecar files to round-meta.json and pool
# reviewer-dyn-*.md archetypes.
#
# This script is idempotent: rounds already converted (round-meta.json present,
# individual sidecar files absent) are skipped. Run once after deploying the
# Phase 3c code changes to eliminate the historical sidecar file backlog.
#
# Usage:
#   scripts/consolidate-round-sidecars.sh [--dry-run] [--log-root DIR]
#
# Options:
#   --dry-run     Print what would be done without modifying files.
#   --log-root D  Path to the committed larch-logs tree (default: larch-logs/).
#
# The script must be run from the repository root (or pass --log-root).
# After running, commit the result:
#   git add larch-logs/
#   git commit -m "chore(larch-logs): Phase 3c retroactive sidecar consolidation"

set -euo pipefail

DRY_RUN=false
LOG_ROOT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 1 ;;
    esac
done

if [ -z "$LOG_ROOT" ]; then
    LOG_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)/larch-logs" || LOG_ROOT="larch-logs"
fi

[ -d "$LOG_ROOT" ] || { printf 'log root not found: %s\n' "$LOG_ROOT" >&2; exit 1; }

POOL_DIR="$LOG_ROOT/shared/archetypes"

if [ "$DRY_RUN" = false ]; then
    mkdir -p "$POOL_DIR"
fi

rounds_converted=0
archetypes_pooled=0
sidecars_removed=0

larch_sha256() {
    local file="$1"
    if command -v shasum >/dev/null 2>&1; then
        LC_ALL=C shasum -a 256 "$file" | awk '{ print $1 }'
    else
        LC_ALL=C sha256sum "$file" | awk '{ print $1 }'
    fi
}

# --- Convert each round directory ---
while IFS= read -r round_dir; do
    # Skip if already converted (round-meta.json exists)
    [ -f "$round_dir/round-meta.json" ] && continue

    # Determine which sidecar files are present
    has_sidecar=false
    for s in review-tally.env collector-results.env collect-agent-results.log \
              review-summary.json coder.env coder-codex.wrapper.log coder-cursor.wrapper.log; do
        [ -f "$round_dir/$s" ] && { has_sidecar=true; break; }
    done
    has_archetype=false
    for a in "$round_dir"/reviewer-dyn-*.md; do
        [ -f "$a" ] && { has_archetype=true; break; }
    done

    [ "$has_sidecar" = true ] || [ "$has_archetype" = true ] || continue

    if [ "$DRY_RUN" = true ]; then
        printf 'dry-run: would convert %s\n' "$round_dir"
        rounds_converted=$((rounds_converted + 1))
        continue
    fi

    # Compose round-meta.json using python3
    meta_tmp="$(mktemp "${TMPDIR:-/tmp}/consolidate-round-meta.XXXXXX")"
    python3 - "$round_dir" > "$meta_tmp" <<'PYEOF'
import json, os, sys

src = sys.argv[1]
out = {}

def read_kv(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                d[k.strip()] = v.strip()
    return d

def read_raw(path):
    with open(path) as f:
        return f.read()

def read_json(path):
    with open(path) as f:
        try:
            return json.load(f)
        except Exception:
            return f.read()

for key, fname, kind in [
    ('tally',       'review-tally.env',          'kv'),
    ('collector',   'collector-results.env',      'raw'),
    ('collect_log', 'collect-agent-results.log',  'raw'),
    ('summary',     'review-summary.json',        'json'),
    ('coder',       'coder.env',                  'kv'),
]:
    path = os.path.join(src, fname)
    if not os.path.isfile(path):
        continue
    if kind == 'kv':
        out[key] = read_kv(path)
    elif kind == 'raw':
        out[key] = read_raw(path)
    else:
        out[key] = read_json(path)

wl = {}
for tool, fname in [('cursor', 'coder-cursor.wrapper.log'), ('codex', 'coder-codex.wrapper.log')]:
    path = os.path.join(src, fname)
    if os.path.isfile(path):
        wl[tool] = read_raw(path)
if wl:
    out['wrapper_logs'] = wl

if out:
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + '\n')
PYEOF

    if [ -s "$meta_tmp" ]; then
        mv -f "$meta_tmp" "$round_dir/round-meta.json"
    else
        rm -f "$meta_tmp"
    fi

    # Remove individual sidecar files
    for s in review-tally.env collector-results.env collect-agent-results.log \
              review-summary.json coder.env coder-codex.wrapper.log coder-cursor.wrapper.log; do
        if [ -f "$round_dir/$s" ]; then
            rm -f "$round_dir/$s"
            sidecars_removed=$((sidecars_removed + 1))
        fi
    done

    # Pool reviewer-dyn-*.md archetypes and update panel-manifest.ndjson
    refs_tmp="$(mktemp "${TMPDIR:-/tmp}/consolidate-archetype-refs.XXXXXX")"
    for arch_file in "$round_dir"/reviewer-dyn-*.md; do
        [ -f "$arch_file" ] || continue
        sha12="$(larch_sha256 "$arch_file" | cut -c1-12)"
        [ -n "$sha12" ] || continue
        pool_path="$POOL_DIR/$sha12.md"
        if [ ! -f "$pool_path" ]; then
            cp "$arch_file" "$pool_path"
            archetypes_pooled=$((archetypes_pooled + 1))
        fi
        arch_name="$(basename "$arch_file")"
        printf '%s\t%s\n' "$arch_name" "$sha12" >> "$refs_tmp"
        rm -f "$arch_file"
        sidecars_removed=$((sidecars_removed + 1))
    done

    # Update panel-manifest.ndjson with archetype_ref
    if [ -f "$round_dir/panel-manifest.ndjson" ] && [ -s "$refs_tmp" ]; then
        pm_new="$(mktemp "${TMPDIR:-/tmp}/consolidate-pm.XXXXXX")"
        python3 - "$round_dir/panel-manifest.ndjson" "$refs_tmp" > "$pm_new" <<'PYEOF'
import json, sys

pm_path, refs_path = sys.argv[1], sys.argv[2]
refs = {}
with open(refs_path) as f:
    for line in f:
        line = line.strip()
        if '\t' in line:
            fname, sha12 = line.split('\t', 1)
            if fname.startswith('reviewer-dyn-') and fname.endswith('.md'):
                slot = 'dyn-' + fname[len('reviewer-dyn-'):-len('.md')]
                refs[slot] = sha12
lines = []
with open(pm_path) as f:
    for line in f:
        stripped = line.rstrip('\n')
        if not stripped.strip():
            lines.append(line)
            continue
        try:
            obj = json.loads(stripped)
            slot = obj.get('slot', '')
            if slot in refs and 'archetype_ref' not in obj:
                obj['archetype_ref'] = refs[slot]
            lines.append(json.dumps(obj, ensure_ascii=False) + '\n')
        except (json.JSONDecodeError, ValueError):
            lines.append(line)
sys.stdout.write(''.join(lines))
PYEOF
        if [ -s "$pm_new" ]; then
            mv -f "$pm_new" "$round_dir/panel-manifest.ndjson"
        else
            rm -f "$pm_new"
        fi
    fi
    rm -f "$refs_tmp"

    rounds_converted=$((rounds_converted + 1))

done < <(find "$LOG_ROOT" -name "round-*" -type d | LC_ALL=C sort)

if [ "$DRY_RUN" = true ]; then
    printf 'dry-run complete: %d round(s) would be converted\n' "$rounds_converted"
else
    printf 'converted %d round(s), removed %d sidecar file(s), pooled %d new archetype(s)\n' \
        "$rounds_converted" "$sidecars_removed" "$archetypes_pooled"
    if [ "$rounds_converted" -gt 0 ]; then
        printf 'next: git add larch-logs/ && git commit -m "chore(larch-logs): Phase 3c retroactive sidecar consolidation"\n'
    fi
fi
