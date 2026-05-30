#!/usr/bin/env bash
# lint-mermaid-fences.sh — run Mermaid CLI over Markdown Mermaid fences.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    REPO_ROOT="$git_root"
else
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

changed_only=false
files=()

fail_usage() {
    larch_err "ERROR: $1"
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
    if [ -x "$REPO_ROOT/mermaid-lint/node_modules/.bin/mmdc" ]; then
        printf '%s\n' "$REPO_ROOT/mermaid-lint/node_modules/.bin/mmdc"
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
    local in_ci="false"
    if [ -n "${GITHUB_EVENT_NAME:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
        in_ci="true"
    fi
    if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
        # Fail closed in CI if the base ref is unreachable: the workflow
        # uses fetch-depth: 0 so origin/<base> should already exist
        # locally; if it doesn't, the symmetric diff would be empty and
        # the lint would silently skip (round-2 follow-up D).
        if ! git rev-parse --verify "origin/${GITHUB_BASE_REF}" >/dev/null 2>&1; then
            git fetch --no-tags --prune origin "$GITHUB_BASE_REF" >/dev/null 2>&1 || true
        fi
        if ! git rev-parse --verify "origin/${GITHUB_BASE_REF}" >/dev/null 2>&1; then
            larch_err "ERROR: cannot resolve origin/${GITHUB_BASE_REF} for --changed-only diff range"
            return 2
        fi
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
        elif [ "$in_ci" = "true" ]; then
            # In CI: fail closed instead of silently skipping. Outside
            # CI we keep the friendly no-op (developers may run
            # --changed-only locally without origin/main reachable).
            larch_err "ERROR: origin/main unavailable in CI; refusing to silently skip Mermaid lint"
            return 2
        else
            larch_err "INFO: origin/main unavailable; no changed Mermaid files linted"
            return 0
        fi
    fi
    if ! git diff --name-only --diff-filter=ACMR "$range" -- '*.md' 2>/dev/null; then
        if [ "$in_ci" = "true" ]; then
            larch_err "ERROR: git diff $range failed in CI"
            return 2
        fi
        larch_err "INFO: git diff $range failed; no changed Mermaid files linted"
        return 0
    fi
}

if [ "$changed_only" = true ]; then
    [ "${#files[@]}" -eq 0 ] || fail_usage "--changed-only does not accept file arguments"
    # Capture changed_files's exit status so a CI fail-closed return (2)
    # propagates instead of being swallowed by process substitution
    # (round-2 follow-up D).
    set +e
    cf_out="$(changed_files)"
    cf_rc=$?
    set -e
    if [ "$cf_rc" -ne 0 ]; then
        exit "$cf_rc"
    fi
    while IFS= read -r f; do
        case "$f" in
            larch-logs/*) ;;  # runtime artifact files excluded from mermaid lint
            "") ;;
            *) files+=("$f") ;;
        esac
    done <<<"$cf_out"
fi

lint_files=()
for f in "${files[@]}"; do
    case "$f" in
        larch-logs/*|"") ;;  # runtime artifact files are not authoring-quality docs
        *) lint_files+=("$f") ;;
    esac
done
if [ "${#lint_files[@]}" -gt 0 ]; then
    files=("${lint_files[@]}")
else
    files=()
fi

[ "${#files[@]}" -gt 0 ] || {
    emit "INFO: no Markdown files to lint"
    exit 0
}

MMDC="$(resolve_mmdc)" || {
    larch_err "ERROR: missing Mermaid CLI (install @mermaid-js/mermaid-cli or run: cd mermaid-lint && npm ci)"
    exit 2
}

tmpdir="$(mktemp -d -t mermaid-lint-XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT

# Pass --no-sandbox to Chromium so the SVG-render fallback works on
# Ubuntu 23.10+ runners with restricted unprivileged user namespaces.
# Local mmdc 11.x does not expose --parseOnly, so the lint always falls
# back to renderMermaid which spawns Chromium via Puppeteer; without
# --no-sandbox the runner aborts with "No usable sandbox!" before any
# Mermaid syntax is checked. The puppeteer config is repository-pinned
# at scripts/lint-mermaid-puppeteer.json so the workaround is auditable.
PPTR_CONFIG="$REPO_ROOT/scripts/lint-mermaid-puppeteer.json"
if [ -f "$PPTR_CONFIG" ]; then
    MMDC_RENDER_ARGS=(--puppeteerConfigFile "$PPTR_CONFIG")
else
    MMDC_RENDER_ARGS=()
fi

supports_parse_only=false
if "$MMDC" --help 2>&1 | grep -q -- '--parseOnly'; then
    supports_parse_only=true
fi

extract_fences() {
    local src=$1 outdir=$2
    local in_outer=false outer_len=0 outer_mermaid=false fence_count=0 line opener rest len
    # shellcheck disable=SC2016 # literal backtick regex; no shell expansion intended.
    # Accept up to 3 leading spaces of indentation per GFM/CommonMark
    # fenced-code-block grammar; without this the scanner would skip
    # indented mermaid fences and the sanitizer / lint chain would
    # silently bypass them (round-2 follow-up SECURITY).
    local fence_re='^[[:space:]]{0,3}(`{3,})([^`]*)$'
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
                larch_err "ERROR: Mermaid parse failed: $path fence $i"
                failures=$((failures + 1))
            fi
        else
            output="$file_tmp/fence-$i.svg"
            if ! "$MMDC" "${MMDC_RENDER_ARGS[@]}" -i "$input" -o "$output" >/dev/null; then
                larch_err "ERROR: Mermaid render failed: $path fence $i"
                failures=$((failures + 1))
            fi
        fi
        i=$((i + 1))
    done
done

[ "$failures" -eq 0 ] || exit 1
exit 0
