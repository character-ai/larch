#!/usr/bin/env bash
# scrub-log-secrets.sh — pre-flush secret gate for committed larch run logs.
#
# Given a directory (the run-log tree staged for a flush commit), this script
# scans EVERY file under it — with NO path exclusions — for secret-shaped
# values, scrubs any it finds IN PLACE, and emits a VERY loud warning when it
# redacts anything. The flush then proceeds with the redacted content (the
# scrub is what makes the flush safe), so the gate exits 0 even when it fires;
# it exits non-zero only when it cannot guarantee a clean tree (fail-closed).
#
# Why this exists (incident): a Cursor API key (`crsr_…`, captured from a
# `cursor agent --api-key crsr_… --workspace …` command line) reached committed
# larch-logs because the per-file redaction filter `redact-secrets.sh` has no
# Cursor pattern, the `/design` flush historically committed with `[skip ci]`
# (so CI's gitleaks/trufflehog did not run on it), and `.gitleaks.toml`
# historically allowlisted `larch-logs/`. This gate is larch's own scrubber/linter, invoked
# right before every log flush, so it does not depend on any third-party
# scanner being installed in consumer repos.
#
# Coverage:
#   - Cursor API keys: crsr_… and key_… (the incident class).
#   - Slack, Google API, Stripe live, and GitLab PAT prefixes.
#   - As a BACKSTOP, the families redact-secrets.sh already covers
#     (sk-/sk-ant-, GitHub tokens, AWS AKIA, JWT, PEM private keys) — so the
#     gate still catches them if a future flush path bypasses per-file
#     redaction. Base families are scrubbed by piping through redact-secrets.sh;
#     the extra families are scrubbed by an additional sed pass derived from the
#     same regex table used for detection (single source of truth).
#
# Files that contain no secret-shaped value are left byte-for-byte untouched
# (no newline normalization), so the gate never produces spurious diffs or
# spurious warnings.
#
# Usage:
#   scrub-log-secrets.sh <dir>
#
# Output (FD 3 contract stream via emit_kv; diagnostics on stderr via larch_err):
#   LARCH_SECRET_SCRUB_VIOLATIONS=<total occurrences scrubbed>
#   LARCH_SECRET_SCRUB_FILES=<number of files scrubbed>
#
# Exit codes:
#   0 — scan complete; tree is clean (0 violations) or was scrubbed clean.
#   2 — usage / setup error (bad argument, redact-secrets.sh unavailable).
#   3 — fail-closed: a file could not be scrubbed, or a detected secret
#       survived scrubbing. The caller MUST abort the flush rather than commit.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# This is a redaction/scrub helper in the same family as redact-secrets.sh:
# keep stdout as the contract plane and do NOT spawn a per-process quiet log
# (which would otherwise be published as an extra run-log breadcrumb on every
# flush). With quiet disabled, emit_kv writes the contract to stdout and
# larch_err writes the (redacted) warning to stderr.
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

REDACT_SECRETS="$SCRIPT_DIR/redact-secrets.sh"

usage() {
    larch_err "Usage: scrub-log-secrets.sh <dir>"
}

DIR="${1:-}"
if [ -z "$DIR" ]; then
    usage
    exit 2
fi
if [ ! -d "$DIR" ]; then
    larch_err "scrub-log-secrets: not a directory: $DIR"
    exit 2
fi
if [ ! -x "$REDACT_SECRETS" ]; then
    larch_err "scrub-log-secrets: redaction helper missing or not executable: $REDACT_SECRETS"
    exit 2
fi

# Secret families and their EREs. The regex column is the single source of
# truth for BOTH detection (grep -E) and, for the extra families, scrubbing
# (sed -E s/<regex>/<REDACTED-TOKEN>/g). Two TAB-separated columns: name<TAB>ERE.
#
# Extra families: NOT covered by redact-secrets.sh. Each is a high-precision
# prefixed pattern with a generous minimum body length to avoid matching
# ordinary identifiers. `crsr_` is the confirmed Cursor prefix; `key_{32,}`
# (longer body) is the hedge for Cursor admin keys without false-positiving on
# `key_` identifiers, which carry underscores and rarely run 32 unbroken
# alphanumerics.
EXTRA_FAMILIES='cursor-api-key	(crsr_[A-Za-z0-9]{20,}|key_[A-Za-z0-9]{32,})
slack-token	xox[baprs]-[A-Za-z0-9-]{10,}
google-api-key	AIza[0-9A-Za-z_-]{35}
stripe-live-key	(sk|rk)_live_[0-9A-Za-z]{16,}
gitlab-pat	glpat-[0-9A-Za-z_-]{20,}'

# Base families: byte-for-byte the EREs in redact-secrets.sh. Detected here so
# the gate is a true backstop; scrubbed by piping through redact-secrets.sh
# (which also handles the multi-line PEM case). Keep in sync with
# redact-secrets.sh if its patterns change.
BASE_FAMILIES='anthropic-openai-key	sk-(ant-)?[A-Za-z0-9_-]{20,}
github-token	(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}
aws-akia	AKIA[0-9A-Z]{16}
jwt	eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}
pem-private-key	-----BEGIN [A-Z ]*PRIVATE KEY-----'

ALL_FAMILIES="$BASE_FAMILIES
$EXTRA_FAMILIES"

# Combined ERE (every family regex joined with top-level alternation) used for
# the fast "does this file contain any secret?" probe and the post-scrub
# verification re-probe.
COMBINED=""
while IFS="$(printf '\t')" read -r _name _re; do
    [ -n "$_re" ] || continue
    if [ -z "$COMBINED" ]; then
        COMBINED="$_re"
    else
        COMBINED="$COMBINED|$_re"
    fi
done <<EOF
$ALL_FAMILIES
EOF

# sed -E arguments that scrub the EXTRA families, derived from the same regex
# table (single source of truth). Base families are handled by redact-secrets.sh.
EXTRA_SED_ARGS=()
while IFS="$(printf '\t')" read -r _name _re; do
    [ -n "$_re" ] || continue
    EXTRA_SED_ARGS+=(-e "s/${_re}/<REDACTED-TOKEN>/g")
done <<EOF
$EXTRA_FAMILIES
EOF

# Count secret occurrences in a file using the combined regex (pipefail-safe).
count_occurrences() {
    local file="$1" n
    set +e
    n=$(grep -oE "$COMBINED" "$file" 2>/dev/null | wc -l)
    set -e
    printf '%s' "$n" | tr -cd '0-9'
}

# Space-separated list of family names that match the file (for the warning).
matching_families() {
    local file="$1" names="" name re
    while IFS="$(printf '\t')" read -r name re; do
        [ -n "$re" ] || continue
        if grep -qE "$re" "$file" 2>/dev/null; then
            names="$names${names:+,}$name"
        fi
    done <<EOF
$ALL_FAMILIES
EOF
    printf '%s' "$names"
}

# Produce the scrubbed bytes of "$1" on stdout: base families via
# redact-secrets.sh, then the extra families via sed.
scrub_stream() {
    local file="$1"
    "$REDACT_SECRETS" <"$file" | sed -E ${EXTRA_SED_ARGS[@]+"${EXTRA_SED_ARGS[@]}"}
}

files_list=$(mktemp "${TMPDIR:-/tmp}/scrub-log-secrets-files.XXXXXX") || {
    larch_err "scrub-log-secrets: cannot allocate temp file list"
    exit 3
}
scrub_tmp=""
# shellcheck disable=SC2317,SC2329  # invoked indirectly via the EXIT trap below.
cleanup() {
    rm -f "${files_list:-}" "${scrub_tmp:-}" 2>/dev/null || true
}
trap cleanup EXIT

if ! find "$DIR" -type f -print0 >"$files_list" 2>/dev/null; then
    larch_err "scrub-log-secrets: failed to enumerate files under $DIR"
    exit 3
fi

total_violations=0
files_scrubbed=0
report=""   # newline-delimited "<relpath>\t<count>\t<families>" rows

while IFS= read -r -d '' file; do
    [ -f "$file" ] || continue
    [ -L "$file" ] && continue
    if ! grep -qE "$COMBINED" "$file" 2>/dev/null; then
        continue
    fi

    occ=$(count_occurrences "$file")
    [ -n "$occ" ] || occ=0
    fams=$(matching_families "$file")

    scrub_tmp=$(mktemp "${TMPDIR:-/tmp}/scrub-log-secrets-scrub.XXXXXX") || {
        larch_err "scrub-log-secrets: cannot allocate scrub temp for $file"
        exit 3
    }
    if ! scrub_stream "$file" >"$scrub_tmp"; then
        larch_err "scrub-log-secrets: redaction pipeline failed for $file"
        exit 3
    fi
    # Fail-closed: a detected secret must not survive scrubbing.
    if grep -qE "$COMBINED" "$scrub_tmp" 2>/dev/null; then
        larch_err "scrub-log-secrets: FATAL — secret survived scrubbing in $file; refusing to flush"
        exit 3
    fi
    if ! cat "$scrub_tmp" >"$file"; then
        larch_err "scrub-log-secrets: cannot write scrubbed content back to $file"
        exit 3
    fi
    rm -f "$scrub_tmp"
    scrub_tmp=""

    rel=${file#"$DIR"/}
    report="$report$rel	$occ	$fams
"
    total_violations=$((total_violations + occ))
    files_scrubbed=$((files_scrubbed + 1))
done <"$files_list"

emit_kv LARCH_SECRET_SCRUB_VIOLATIONS "$total_violations"
emit_kv LARCH_SECRET_SCRUB_FILES "$files_scrubbed"

if [ "$files_scrubbed" -gt 0 ]; then
    larch_err ""
    larch_err "################################################################################"
    larch_err "##  ⚠  SECRETS DETECTED AND SCRUBBED FROM RUN LOGS BEFORE FLUSH  ⚠"
    larch_err "################################################################################"
    larch_err "## scrub-log-secrets.sh redacted ${total_violations} secret-shaped value(s) across ${files_scrubbed} file(s)"
    larch_err "## in the run-log tree staged for commit:"
    larch_err "##   ${DIR}"
    larch_err "##"
    larch_err "## The flush PROCEEDS with redacted content, but a real credential was almost"
    larch_err "## certainly present in this run's session/transcript. TREAT IT AS COMPROMISED:"
    larch_err "##   1. ROTATE the affected credential(s) NOW."
    larch_err "##   2. Check whether the same value reached chat, PRs, or other artifacts."
    larch_err "##"
    larch_err "## Files (path : occurrences : families):"
    while IFS="$(printf '\t')" read -r rel cnt fams; do
        [ -n "$rel" ] || continue
        larch_err "##   ${rel} : ${cnt} : ${fams}"
    done <<EOF
$report
EOF
    larch_err "################################################################################"
    larch_err ""
fi

exit 0
