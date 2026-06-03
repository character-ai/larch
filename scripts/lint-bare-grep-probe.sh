#!/usr/bin/env bash
# lint-bare-grep-probe.sh - reject bare top-level grep in orchestrator markdown fences.
#
# In a Claude Code Bash tool block, `grep` resolves to a wrapper shell function
# that exec-subshells into the `claude` CLI in ugrep mode. When that subshell
# exits non-zero at the top level of the script, the harness terminates the
# whole Bash tool block — even with `|| true`, `if grep ...; then`, or
# `{ grep ...; } || X` guards. See `BASH_AUTHORING.md` §1 and issue #3104.
#
# Safe forms: `command grep PATTERN file || X` (preferred) or
# `( grep PATTERN file ) || X` (explicit subshell wrap).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0

usage() {
    printf 'Usage: %s [--root PATH]\n' "$(basename "$0")" >&2
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --root)
            if [[ "$#" -lt 2 || -z "${2:-}" ]]; then
                usage
                exit 2
            fi
            ROOT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

if [[ ! -d "$ROOT" ]]; then
    printf 'lint-bare-grep-probe: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-bare-grep-probe-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

# Orchestrator-facing markdown surfaces only: SKILL.md, references/, shared/,
# .claude/skills/, and .claude/rules/. Documentation under docs/ and top-level
# *.md (README, release notes, BASH_AUTHORING) is excluded — those are not executed
# as Bash tool blocks by the orchestrator.
list_markdown_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- \
            'skills/**/*.md' '.claude/skills/**/*.md' '.claude/rules/*.md' \
            | while IFS= read -r -d '' rel; do
                case "$rel" in
                    larch-logs/*) continue ;;
                esac
                printf '%s\0' "$rel"
            done
    else
        (
            cd "$ROOT"
            find skills .claude/skills .claude/rules \
                \( -path '*/larch-logs/*' \) -prune -o \
                -type f -name '*.md' -print 2>/dev/null \
                | sed 's#^\./##' \
                | LC_ALL=C sort \
                | while IFS= read -r path; do
                    printf '%s\0' "$path"
                done
        )
    fi
}

# Within fenced bash/sh/shell blocks, flag lines whose first command-word is
# `grep` (preceded only by leading whitespace). Catches `grep ... || X`,
# `grep ... > file`, and bare-statement forms. Also flags `if grep ...; then`
# and `if ! grep ...; then` because the harness kills the block before the
# branch decision runs. Lines containing `command grep` or an opening `(`
# before `grep` are accepted as safe. Same-line `# lint-bare-grep-probe: ok`
# pragmas suppress fixture lines.
scan_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    set +e
    awk -v rel="$rel" '
        BEGIN {
            in_fence = 0
        }
        function report(reason) {
            printf("lint-bare-grep-probe: %s:%s: bare top-level grep in bash fence (%s); use `command grep` or `( grep ... )`\n", rel, FNR, reason) > "/dev/stderr"
            violations = 1
        }
        {
            line = $0

            if (line ~ /^[[:space:]]*```[[:space:]]*(bash|sh|shell)[[:space:]]*$/) {
                in_fence = 1
                next
            }
            if (in_fence && line ~ /^[[:space:]]*```[[:space:]]*$/) {
                in_fence = 0
                next
            }
            if (!in_fence) next

            # Skip same-line pragma suppression.
            if (line ~ /#[[:space:]]*lint-bare-grep-probe:[[:space:]]*ok([[:space:]]|$)/) next
            # Skip full-line comments.
            if (line ~ /^[[:space:]]*#/) next

            # Bare top-level grep: `grep ...`.
            if (line ~ /^[[:space:]]*grep[[:space:]]/) {
                report("bare grep statement")
                next
            }
            # if grep ... / if ! grep ...
            if (line ~ /^[[:space:]]*if[[:space:]]+!?[[:space:]]*grep[[:space:]]/) {
                report("if grep ... ; then")
                next
            }
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

list_markdown_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    scan_file "$rel"
done < "$TMP_FILES"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0
