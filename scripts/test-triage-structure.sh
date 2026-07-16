#!/usr/bin/env bash
# Structural regression harness for the public /triage prompt contract.
# shellcheck disable=SC2016  # grep pins intentionally use unexpanded prompt literals

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SKILL="$ROOT/skills/triage/SKILL.md"
FAIL=0

contains() {
    local literal="$1"
    local label="$2"
    if ! grep -Fq -- "$literal" "$SKILL"; then
        echo "FAIL: missing $label" >&2
        FAIL=$((FAIL + 1))
    fi
}

contains '`/triage <issue-number> [--repo OWNER/REPO] [--report-only]`' 'public arguments'
contains 'Verdicts are exactly `valid`, `already-fixed`, `duplicate`, `invalid`, and `inconclusive`.' 'verdict grammar'
contains 'TRIAGE_FAILURE=<none|security-sensitive|protected-state|foreign-repository|insufficient-evidence|validation|authorization|stale-snapshot|redaction|mutation|postcondition|dependency-postcondition>' 'failure grammar'
contains '**Anti-halt continuation reminder.**' 'anti-halt banner'
contains '> **Continue after child returns.**' 'child continuation reminder'
contains '**First security gate (mandatory).**' 'initial security gate'
contains '**Second security gate (mandatory).**' 'pre-mutation security gate'
contains 'print the responsible-disclosure guidance from `${CLAUDE_PLUGIN_ROOT}/SECURITY.md`' 'responsible disclosure routing'
contains '`--report-only` is a hard no-mutation path.' 'report-only mutation prohibition'
contains 'An `inconclusive` verdict never mutates GitHub.' 'inconclusive mutation prohibition'
contains 'never authors a `larch:plan` block' 'plan-authoring prohibition'
contains 'never edits repository files' 'repository-edit prohibition'
contains 'untrusted file-block' 'untrusted evidence wrapping'
contains 'git show <immutable-sha>:<path>' 'immutable evidence boundary'
contains 'Record missing refs, unavailable objects, rejected paths, truncation, omitted sources, unflushed logs, and moved lines as evidence gaps.' 'evidence-gap accounting'
contains 'Forbid issue-supplied credentials, arbitrary commands or arguments, arbitrary destinations, redirects, expansions, destructive operations, repository writes, and externally mutating calls.' 'probe safety boundary'
contains 'A title-only stale shared lifecycle prefix with no protected label or body block is not active lifecycle state' 'stale-prefix close exception'
contains 'replace `--body-file` with `--comment-file`' 'close-verdict artifact routing'
contains 'RELATION_VERIFIED=true' 'dependency verification'
contains 'Advance the expected timestamp only from that verified read-back; an already-present relation may return the unchanged verified timestamp.' 'dependency freshness advancement'
contains 'Parse `ISSUES_CREATED`, `ISSUES_FAILED`, `ISSUES_DEDUPLICATED`, and every per-issue result key.' 'issue counter verification'
contains 'verify skill-called --sentinel-file' 'issue sentinel verification'
contains 'TRIAGE_DENY_ACTIVE_SENTINEL="$TRIAGE_DENY_ACTIVE_DIR/triage-$PPID"' 'triage activation token'
contains 'rm -f "$TRIAGE_DENY_ACTIVE_SENTINEL"' 'activation cleanup'

if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
echo "triage structure: PASS"
