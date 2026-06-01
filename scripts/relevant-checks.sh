#!/usr/bin/env bash
# Run validation checks relevant to modified files on the current branch.
# Delegates to pre-commit for file-type routing and linting.
# Consumer-repo script invoked by scripts/run-relevant-checks-captured.sh.
# Note: -e intentionally omitted — pre-commit exit code is captured explicitly
# (PRE_COMMIT_EXIT) rather than aborting, so later checks can still run.
set -uo pipefail
PHASES_RUN=0

# ---------------------------------------------------------------------------
# Pre-flight: ensure pre-commit is installed
# ---------------------------------------------------------------------------
command -v pre-commit >/dev/null 2>&1 || {
    echo "ERROR: pre-commit not found. Run: pip install pre-commit (or: make setup)"
    exit 1
}

REPO_ROOT="$(git rev-parse --show-toplevel)" || { echo "ERROR: not inside a git repository"; exit 1; }
cd "$REPO_ROOT" || exit 1

# ---------------------------------------------------------------------------
# Shared post-check function: agent-lint
# ---------------------------------------------------------------------------
run_post_checks() {
    if command -v agent-lint >/dev/null 2>&1; then
        echo ""
        echo "=== Running agent-lint ==="
        agent-lint --pedantic "$REPO_ROOT"
        local rc=$?
        PHASES_RUN=$((PHASES_RUN + 1))
        return "$rc"
    else
        echo ""
        echo "WARNING: agent-lint not found on PATH — skipping"
        return 0
    fi
}

append_target_once() {
    local target="$1"
    case " $DIRECT_TARGETS " in
        *" $target "*) ;;
        *) DIRECT_TARGETS="${DIRECT_TARGETS}${DIRECT_TARGETS:+ }$target" ;;
    esac
}

maybe_append_py_lint_target() {
    local missing="" tool=""
    for tool in ruff pylint pyright; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing="${missing}${missing:+ }$tool"
        fi
    done

    if [ -n "$missing" ]; then
        PY_LINT_SKIPPED=1
        if [ "${PY_LINT_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: Python lint tools not found on PATH ($missing) — skipping py-lint direct relevant target"
            PY_LINT_SKIP_WARNED=1
        fi
        return 0
    fi

    append_target_once py-lint
}

maybe_append_py_test_target() {
    if ! command -v pytest >/dev/null 2>&1; then
        PY_TEST_SKIPPED=1
        if [ "${PY_TEST_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: pytest not found on PATH — skipping py-test direct relevant target"
            PY_TEST_SKIP_WARNED=1
        fi
        return 0
    fi

    append_target_once py-test
}

run_direct_relevant_targets() {
    local f=""
    DIRECT_TARGETS=""
    PY_LINT_SKIP_WARNED=0
    PY_TEST_SKIP_WARNED=0
    PY_LINT_SKIPPED=0
    PY_TEST_SKIPPED=0
    PYTHON_PY_CHANGED=0
    while IFS= read -r f; do
        case "$f" in
            scripts/test-step0b-router-flag-recovery.sh|scripts/test-step0b-router-flag-recovery.md|scripts/write-run-params.sh|skills/design/scripts/design-init-runparams.sh|skills/design/scripts/design-init-runparams.md)
                append_target_once test-step0b-router-flag-recovery
                ;;
            skills/design/scripts/design-route.sh|skills/design/scripts/design-route.md)
                append_target_once test-design-structure
                ;;
            skills/design/scripts/design-publish.sh|skills/design/scripts/design-publish.md|skills/design/scripts/test-design-publish.sh|skills/design/scripts/test-design-publish.md)
                append_target_once test-design-publish
                append_target_once test-design-structure
                ;;
        esac
        case "$f" in
            skills/design/SKILL.md|skills/design/references/*.md)
                append_target_once test-design-structure
                append_target_once test-design-publish
                append_target_once test-render-cost-line-callsites
                ;;
            skills/upgrade-larch/scripts/upgrade-larch.sh|skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh)
                append_target_once test-upgrade-larch-retention
                ;;
        esac
        case "$f" in
            skills/design/scripts/snapshot-plan-round.sh|skills/design/scripts/snapshot-plan-round.md|skills/design/scripts/test-snapshot-plan-round.sh|skills/design/scripts/test-snapshot-plan-round.md)
                append_target_once test-snapshot-plan-round
                ;;
        esac
        case "$f" in
            skills/design/scripts/dispatch-plan-assessors.sh|skills/design/scripts/dispatch-plan-assessors.md|skills/design/scripts/test-dispatch-plan-assessors.sh|skills/design/scripts/test-dispatch-plan-assessors.md)
                append_target_once test-dispatch-plan-assessors
                ;;
        esac
        case "$f" in
            skills/shared/scripts/render-assessor-prompt.sh|skills/shared/scripts/render-assessor-prompt.md|skills/shared/scripts/test-render-assessor-prompt.sh|skills/shared/scripts/test-render-assessor-prompt.md)
                append_target_once test-render-assessor-prompt
                ;;
        esac
        case "$f" in
            skills/design/scripts/tally-plan-assessor.sh|skills/design/scripts/tally-plan-assessor.md|skills/design/scripts/test-tally-plan-assessor.sh|skills/design/scripts/test-tally-plan-assessor.md)
                append_target_once test-tally-plan-assessor
                ;;
        esac
        case "$f" in
            skills/design/scripts/assess-plan-round.sh|skills/design/scripts/assess-plan-round.md|skills/design/scripts/test-assess-plan-round.sh|skills/design/scripts/test-assess-plan-round.md)
                append_target_once test-assess-plan-round
                ;;
        esac
        case "$f" in
            skills/design/scripts/render-final-summary.sh|skills/design/scripts/render-final-summary.md|skills/design/scripts/test-render-final-summary.sh|skills/design/scripts/test-render-final-summary.md|scripts/test-render-final-summary-bash32.sh|scripts/test-render-final-summary-bash32.md)
                append_target_once test-render-final-summary
                append_target_once test-render-final-summary-bash32
                ;;
        esac
        case "$f" in
            skills/design/scripts/plan-review-loop.sh|skills/design/scripts/plan-review-loop.md|skills/design/scripts/test-plan-review-loop.sh|skills/design/scripts/dedup-plan-lines.py|skills/design/scripts/dedup-plan-lines.md)
                append_target_once test-plan-review-loop
                append_target_once test-design-multi-round-integration
                ;;
        esac
        case "$f" in
            skills/design/scripts/revise-plan-with-waterfall.sh|skills/design/scripts/revise-plan-with-waterfall.md|scripts/test-revise-plan-with-waterfall.sh)
                append_target_once test-revise-plan-with-waterfall
                ;;
        esac
        case "$f" in
            scripts/degraded-tools-gate.sh|scripts/degraded-tools-gate.md|scripts/test-degraded-tools-gate.sh)
                append_target_once test-degraded-tools-gate
                ;;
        esac
        case "$f" in
            scripts/design-log-publish.sh|scripts/test-design-log-publish.sh|scripts/test-design-multi-round-integration.sh|scripts/test-design-multi-round-integration.md)
                append_target_once test-design-log-publish
                append_target_once test-design-multi-round-integration
                ;;
        esac
        case "$f" in
            scripts/lib-design-round-artifacts.sh|scripts/lib-design-round-artifacts.md|scripts/test-lib-design-round-artifacts.sh)
                append_target_once test-lib-design-round-artifacts
                append_target_once test-design-multi-round-integration
                append_target_once test-design-log-publish
                ;;
        esac
        case "$f" in
            scripts/check-contains-pins.sh|scripts/check-contains-pins.md|scripts/test-check-contains-pins.sh|scripts/test-check-contains-pins.md|scripts/test-design-structure.sh|scripts/test-design-structure.md)
                append_target_once test-check-contains-pins
                ;;
        esac
        case "$f" in
            scripts/test-design-structure.sh|scripts/test-design-structure.md)
                append_target_once test-design-structure
                ;;
        esac
        case "$f" in
            skills/*/SKILL.md|skills/*/references/*.md)
                append_target_once test-check-contains-pins
                ;;
        esac
        case "$f" in
            scripts/lint-readability-preamble.tsv|scripts/lint-readability-preamble.tsv.md)
                append_target_once test-lint-readability-preamble
                ;;
        esac
        case "$f" in
            scripts/collect-agent-results.sh|scripts/test-collect-agent-results.sh) # lint-foreground-markers: ok relevant-checks case pattern
                append_target_once test-collect-agent-results
                ;;
        esac
        case "$f" in
            scripts/lib-design-tmpdir.sh|scripts/test-lib-design-tmpdir.sh|scripts/lib-design-tmpdir.md|scripts/test-lib-design-tmpdir.md)
                append_target_once test-lib-design-tmpdir
                ;;
        esac
        case "$f" in
            scripts/lib-net.sh|scripts/lib-net.md|scripts/test-lib-net.sh|scripts/test-lib-net.md)
                append_target_once test-lib-net
                ;;
        esac
        case "$f" in
            python/*.py)
                PYTHON_PY_CHANGED=1
                maybe_append_py_lint_target
                maybe_append_py_test_target
                ;;
            python/pyproject.toml|python/ruff.toml|python/pyrightconfig.json|python/.pylintrc|python/requirements-dev.txt|python/requirements-test.txt)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                ;;
        esac
    done <<< "$MODIFIED_FILES"

    if [ "$PYTHON_PY_CHANGED" -eq 1 ]; then
        if [ "$PY_LINT_SKIPPED" -eq 1 ] || [ "$PY_TEST_SKIPPED" -eq 1 ]; then
            echo "ERROR: python/*.py changed but Python lint/test tools are missing from PATH — install python/requirements-dev.txt and python/requirements-test.txt (Node required for pyright)"
            return 1
        fi
    fi

    if [ -n "$DIRECT_TARGETS" ]; then
        local targets=()
        local target=""
        for target in $DIRECT_TARGETS; do
            targets+=("$target")
        done
        echo ""
        echo "=== Running direct relevant make target(s): $DIRECT_TARGETS ==="
        make "${targets[@]}"
        local rc=$?
        PHASES_RUN=$((PHASES_RUN + 1))
        return "$rc"
    fi
    return 0
}

exit_with_phase_check() {
    local rc="$1"

    if [ "$PHASES_RUN" -eq 0 ]; then
        echo ""
        echo "ERROR: no validation phases ran — pre-commit had no eligible files (no changes, or no regular files for pre-commit) and agent-lint was unavailable or skipped."
        exit 2
    fi

    exit "$rc"
}

# ---------------------------------------------------------------------------
# Determine changed files (union of branch diff + staged + unstaged + untracked)
# ---------------------------------------------------------------------------
# Only fall back to origin/main if local main is truly unavailable, not if the
# diff is just empty (which happens on a new branch with no commits yet — when
# there are no branch commits, main...HEAD returns empty, and we rely on the
# staged/unstaged/untracked diffs to capture working tree changes).
if git rev-parse --verify main >/dev/null 2>&1; then
    branch_diff="$(git diff --name-only main...HEAD 2>/dev/null || true)"
elif git rev-parse --verify origin/main >/dev/null 2>&1; then
    branch_diff="$(git diff --name-only origin/main...HEAD 2>/dev/null || true)"
else
    branch_diff=""
fi

# Staged changes (files added to index but not yet committed)
staged_diff="$(git diff --cached --name-only 2>/dev/null || true)"

# Unstaged changes (modified but not yet staged)
unstaged_diff="$(git diff --name-only 2>/dev/null || true)"

# Untracked files (newly created, not yet staged — e.g., files written by Claude)
untracked="$(git ls-files --others --exclude-standard 2>/dev/null || true)"

# Union and deduplicate
MODIFIED_FILES="$(printf '%s\n%s\n%s\n%s' "$branch_diff" "$staged_diff" "$unstaged_diff" "$untracked" | sort -u | grep -v '^$' || true)"

if [ -z "$MODIFIED_FILES" ]; then
    echo "No modified files detected — running full-repo post-checks if available."
    run_post_checks
    exit_with_phase_check "$?"
fi

# ---------------------------------------------------------------------------
# Build file array, filtering to existing regular files via [ -f ]. This drops
# deleted paths (would cause pre-commit to fail with file-not-found errors),
# directories (pre-commit expects file paths), and other non-regular paths.
# Uses a portable while-read loop instead of mapfile for macOS Bash 3.2 compat.
# ---------------------------------------------------------------------------
files=()
while IFS= read -r f; do
    if [ -f "$f" ]; then
        files+=("$f")
    fi
done <<< "$MODIFIED_FILES"

# ---------------------------------------------------------------------------
# If files[] is empty but MODIFIED_FILES is non-empty, every modified path was
# rejected by the [ -f ] regular-file filter — typically deletions, but also
# directories or other non-regular-file path categories. Pre-commit has
# nothing to lint, but agent-lint is exactly what we want: deletions are the
# most likely cause of structural regressions (deleted referenced scripts,
# removed SKILL.md, etc.), and directory-only changes still benefit from
# repo-wide structural checks. Run agent-lint before exiting.
# ---------------------------------------------------------------------------
if [ ${#files[@]} -eq 0 ]; then
    echo "No existing regular files to pass to pre-commit."
    run_post_checks
    exit_with_phase_check "$?"
fi

# ---------------------------------------------------------------------------
# Run pre-commit on changed files. Pre-commit handles file-type routing via
# the types/files fields in .pre-commit-config.yaml — no manual gating needed.
# ---------------------------------------------------------------------------
echo "=== Running pre-commit on ${#files[@]} changed file(s) ==="
pre-commit run --files "${files[@]}"
PRE_COMMIT_EXIT=$?

if [ "$PRE_COMMIT_EXIT" -ne 0 ]; then
    exit "$PRE_COMMIT_EXIT"
fi

PHASES_RUN=$((PHASES_RUN + 1))

run_direct_relevant_targets
DIRECT_EXIT=$?
if [ "$DIRECT_EXIT" -ne 0 ]; then
    exit "$DIRECT_EXIT"
fi

# ---------------------------------------------------------------------------
# Verify contains-style test pins against their target files before the final
# structural sweep. Guard on file existence, not executable bit, so a missing
# chmod cannot silently disable the backstop.
# ---------------------------------------------------------------------------
PINS_SCRIPT="$REPO_ROOT/scripts/check-contains-pins.sh"
if [ -f "$PINS_SCRIPT" ]; then
    _tmp_changed="$(mktemp)"
    printf '%s\n' "$MODIFIED_FILES" > "$_tmp_changed"
    bash "$PINS_SCRIPT" --changed-files "$_tmp_changed"
    PINS_EXIT=$?
    rm -f "$_tmp_changed"
    PHASES_RUN=$((PHASES_RUN + 1))
    if [ "$PINS_EXIT" -ne 0 ]; then
        exit "$PINS_EXIT"
    fi
else
    echo "WARNING: scripts/check-contains-pins.sh not found — pin verification skipped"
fi

# ---------------------------------------------------------------------------
# Pre-commit succeeded — run agent-lint on the full repo.
# This catches structural regressions (frontmatter, references, dead scripts,
# etc.) that pre-commit's file-type linters cannot detect. Mirrors the same
# linter invoked by CI's agent-lint job, so developers can catch regressions
# locally before pushing.
# ---------------------------------------------------------------------------
run_post_checks
exit_with_phase_check "$?"
