#!/usr/bin/env bash
# lint-mermaid-fences.sh — run Mermaid CLI over Markdown Mermaid fences.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    REPO_ROOT="$git_root"
else
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

changed_only=false
files=()

fail_usage() {
    echo "ERROR: $1" >&2
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --changed-only)
            changed_only=true; shift ;;
        --*)
            fail_usage "unknown flag: $1" ;;
        *)
            files+=("$1"); shift ;;
    esac
done

resolve_mmdc() {
    if [ -x "$REPO_ROOT/node_modules/.bin/mmdc" ]; then
        printf '%s\n' "$REPO_ROOT/node_modules/.bin/mmdc"
        return 0
    fi
    if command -v mmdc >/dev/null 2>&1; then
        command -v mmdc
        return 0
    fi
    return 1
}

changed_files() {
    local range=""
    if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
        git fetch --no-tags --prune --depth=1 origin "$GITHUB_BASE_REF" >/dev/null 2>&1 || true
        range="origin/${GITHUB_BASE_REF}...HEAD"
    elif [ "${GITHUB_EVENT_NAME:-}" = "push" ]; then
        if [ -n "${GITHUB_EVENT_BEFORE:-}" ] && [ -n "${GITHUB_SHA:-}" ]; then
            range="${GITHUB_EVENT_BEFORE}..${GITHUB_SHA}"
        else
            range="HEAD~1..HEAD"
        fi
    else
        if git rev-parse --verify origin/main >/dev/null 2>&1; then
            range="origin/main...HEAD"
        else
            echo "INFO: origin/main unavailable; no changed Mermaid files linted" >&2
            return 0
        fi
    fi
    git diff --name-only --diff-filter=ACMR "$range" -- '*.md' 2>/dev/null || true
}

if [ "$changed_only" = true ]; then
    [ "${#files[@]}" -eq 0 ] || fail_usage "--changed-only does not accept file arguments"
    while IFS= read -r f; do
        [ -n "$f" ] && files+=("$f")
    done < <(changed_files)
fi

[ "${#files[@]}" -gt 0 ] || {
    echo "INFO: no Markdown files to lint"
    exit 0
}

MMDC="$(resolve_mmdc)" || {
    echo "ERROR: missing Mermaid CLI (install @mermaid-js/mermaid-cli or run npm install)" >&2
    exit 2
}

tmpdir="$(mktemp -d -t mermaid-lint-XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT

supports_parse_only=false
if "$MMDC" --help 2>&1 | grep -q -- '--parseOnly'; then
    supports_parse_only=true
fi

extract_fences() {
    local src=$1 outdir=$2
    local in_outer=false outer_len=0 outer_mermaid=false fence_count=0 line opener rest len
    # shellcheck disable=SC2016 # literal backtick regex; no shell expansion intended.
    local fence_re='^(`{3,})([^`]*)$'
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ $fence_re ]]; then
            opener="${BASH_REMATCH[1]}"
            rest="${BASH_REMATCH[2]}"
            len=${#opener}
            if [ "$in_outer" = false ]; then
                if [[ "$rest" =~ ^[[:space:]]*mermaid[[:space:]]*$ ]]; then
                    fence_count=$((fence_count + 1))
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=true
                    : > "$outdir/fence-$fence_count.mmd"
                    continue
                else
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=false
                fi
            else
                if [ "$len" -ge "$outer_len" ] && [[ "$rest" =~ ^[[:space:]]*$ ]]; then
                    in_outer=false
                    outer_len=0
                    outer_mermaid=false
                    continue
                fi
            fi
        fi
        if [ "$in_outer" = true ] && [ "$outer_mermaid" = true ]; then
            printf '%s\n' "$line" >> "$outdir/fence-$fence_count.mmd"
        fi
    done < "$src"
    printf '%s\n' "$fence_count"
}

failures=0
for path in "${files[@]}"; do
    [ -f "$path" ] || continue
    case "$path" in
        *.md) ;;
        *) continue ;;
    esac
    # Use mktemp -d so each path gets a unique subdir; previously
    # `tr '/ ' '__'` mapped both '/' and ' ' to '_', so paths like
    # `docs/foo/bar.md` and `docs/foo bar.md` collided into the same
    # subdir and the second file's extracted fences overwrote the
    # first's, yielding false passes / false fails (closes #1426
    # follow-up FINDING_4).
    file_tmp="$(mktemp -d -p "$tmpdir" file-XXXXXX)"
    count="$(extract_fences "$path" "$file_tmp")"
    i=1
    while [ "$i" -le "$count" ]; do
        input="$file_tmp/fence-$i.mmd"
        if [ "$supports_parse_only" = true ]; then
            if ! "$MMDC" --parseOnly -i "$input" >/dev/null; then
                echo "ERROR: Mermaid parse failed: $path fence $i" >&2
                failures=$((failures + 1))
            fi
        else
            output="$file_tmp/fence-$i.svg"
            if ! "$MMDC" -i "$input" -o "$output" >/dev/null; then
                echo "ERROR: Mermaid render failed: $path fence $i" >&2
                failures=$((failures + 1))
            fi
        fi
        i=$((i + 1))
    done
done

[ "$failures" -eq 0 ] || exit 1
exit 0
