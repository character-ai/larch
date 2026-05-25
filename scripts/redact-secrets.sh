#!/usr/bin/env bash
# redact-secrets.sh — Deterministic defense-in-depth secret scrubber.
#
# Reads arbitrary text on stdin, applies a fixed set of regex replacements,
# and writes the redacted text to stdout. Intended as the outbound choke
# point for content that /issue's create-one.sh publishes as a public
# GitHub issue title or body, complementing prompt-level sanitization in
# skills/implement/SKILL.md and skills/issue/SKILL.md. See SECURITY.md
# ("Untrusted GitHub Issue Content") for the dual-layer trust model.
#
# Covered families (each replaced with <REDACTED-TOKEN> unless noted):
#   - Anthropic / OpenAI sk-* and sk-ant-* keys
#   - GitHub PATs and fine-grained tokens: ghp_, gho_, ghu_, ghs_, ghr_, github_pat_
#   - AWS long-term access key IDs (AKIA[0-9A-Z]{16})
#   - Generic JWT (eyJ…header.payload.signature)
#   - PEM-encoded private key blocks → <REDACTED-PRIVATE-KEY> (multi-line,
#     tolerates leading whitespace and markdown blockquote prefixes on the
#     BEGIN/END markers). If a BEGIN marker appears without a matching END
#     before EOF, the tail of the body is dropped (fail-closed) and a
#     visible `[content truncated — unterminated PEM block…]` marker is
#     emitted on stdout plus a WARN line on stderr.
#
# Explicit non-coverage (not matched; operators must treat this as partial
# defense-in-depth, not comprehensive secret detection):
#   - AWS STS temporary credentials (ASIA* prefix)
#   - Payment-provider live keys (Stripe, Square, etc.)
#   - Opaque bearer tokens without a distinctive prefix
#   - Database connection strings, private hostnames, PII
#
# Idempotence: placeholders (<REDACTED-TOKEN>, <REDACTED-PRIVATE-KEY>) are
# crafted so no covered pattern matches within them; re-running the filter
# on already-redacted output is a no-op.
#
# Portability: uses `sed -E` (BSD and GNU) and `awk` (POSIX). Does NOT
# depend on perl or GNU-specific sed features.
#
# Usage:
#   printf '%s' "$TEXT" | redact-secrets.sh
#   cat body.txt | redact-secrets.sh > redacted.txt
#
# Exit codes:
#   0 — success
#   non-zero — sed or awk failed (propagated via pipefail)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --streaming + --state-file=PATH: process stdin line-by-line with PEM state
# persisted in PATH across invocations (Bash 3.2-safe). Does not source
# lib-quiet — stdout must remain the data plane for filters.
if [[ "${1:-}" == "--streaming" ]]; then
    shift
    state_file=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --state-file=*)
                state_file="${1#--state-file=}"
                shift
                ;;
            --state-file)
                state_file="${2:?--state-file requires a value}"
                shift 2
                ;;
            *)
                printf 'redact-secrets.sh: unknown streaming option: %s\n' "$1" >&2
                exit 2
                ;;
        esac
    done
    [[ -n "$state_file" ]] || {
        printf 'redact-secrets.sh: --streaming requires --state-file\n' >&2
        exit 2
    }
    if [[ ! -f "$state_file" ]]; then
        printf 'in_pem=0\n' >"$state_file" || {
            printf 'redact-secrets.sh: cannot create state file\n' >&2
            exit 2
        }
    fi
    # shellcheck disable=SC1090
    source "$state_file" 2>/dev/null || {
        printf 'in_pem=0\n' >"$state_file"
        in_pem=0
    }
    larch_rs_stream_write_state() {
        printf 'in_pem=%s\n' "$in_pem" >"${state_file}.new" && mv -f "${state_file}.new" "$state_file"
    }
    larch_rs_line_sed() {
        # shellcheck disable=SC2016
        printf '%s\n' "$1" | sed -E \
            -e 's/sk-(ant-)?[A-Za-z0-9_-]{20,}/<REDACTED-TOKEN>/g' \
            -e 's/(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}/<REDACTED-TOKEN>/g' \
            -e 's/AKIA[0-9A-Z]{16}/<REDACTED-TOKEN>/g' \
            -e 's/eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/<REDACTED-TOKEN>/g'
    }
    while IFS= read -r rs_line || [[ -n "${rs_line:-}" ]]; do
        if [[ "$in_pem" == 1 ]]; then
            if printf '%s\n' "$rs_line" | grep -Eq '^[[:space:]>]*-----END [A-Z ]*PRIVATE KEY-----'; then
                in_pem=0
                larch_rs_stream_write_state
            fi
            continue
        fi
        if printf '%s\n' "$rs_line" | grep -Eq '^[[:space:]>]*-----BEGIN [A-Z ]*PRIVATE KEY-----'; then
            printf '%s\n' '<REDACTED-PRIVATE-KEY>'
            in_pem=1
            larch_rs_stream_write_state
            continue
        fi
        larch_rs_line_sed "$rs_line" || exit 1
        larch_rs_stream_write_state
    done
    if [[ "$in_pem" == 1 ]]; then
        printf '%s\n' '[content truncated — unterminated PEM block; tail of body dropped for safety]' >&2
        printf '%s\n' 'WARN: redact-secrets.sh: unterminated PEM block (streaming)' >&2
    fi
    exit 0
fi

LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# Single sed -E invocation collapsing all line-local families into one pass.
# Patterns are byte-for-byte ports of the vetted regexes from the deleted
# scripts/create-oos-issues.sh (see commit 9cb59f5). The character classes
# use [A-Za-z0-9_-] rather than \w so the script runs on BSD sed without
# GNU-only extensions.
#
# Then awk handles the multi-line PEM case that sed cannot: awk walks the
# stream line-by-line, and when it sees a BEGIN marker it swallows lines
# until the matching END marker, emitting a single placeholder for the
# whole block. Non-PEM lines pass through unchanged.
sed -E \
    -e 's/sk-(ant-)?[A-Za-z0-9_-]{20,}/<REDACTED-TOKEN>/g' \
    -e 's/(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}/<REDACTED-TOKEN>/g' \
    -e 's/AKIA[0-9A-Z]{16}/<REDACTED-TOKEN>/g' \
    -e 's/eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/<REDACTED-TOKEN>/g' \
    | awk '
        # Allow leading whitespace and markdown blockquote prefixes (> ) so
        # PEM blocks wrapped in `    -----BEGIN ...` (code-block indent) or
        # `> -----BEGIN ...` (blockquote) are still matched. The prefix
        # characters are dropped from the emitted placeholder.
        /^[[:space:]>]*-----BEGIN [A-Z ]*PRIVATE KEY-----/ {
            print "<REDACTED-PRIVATE-KEY>"
            in_pem = 1
            next
        }
        in_pem {
            if (/^[[:space:]>]*-----END [A-Z ]*PRIVATE KEY-----/) {
                in_pem = 0
            }
            next
        }
        { print }
        # Fail-closed: on EOF while still inside a PEM block (a BEGIN line
        # without matching END), the tail after BEGIN has already been
        # swallowed to avoid leaking key material. Emit a visible marker so
        # the truncation is not silent and issue authors notice the body is
        # incomplete. Also signal to stderr for log visibility.
        END {
            if (in_pem) {
                print "[content truncated — unterminated PEM block; tail of body dropped for safety]"
                print "WARN: redact-secrets.sh: unterminated PEM block; body tail dropped" > "/dev/stderr"
            }
        }
    '
