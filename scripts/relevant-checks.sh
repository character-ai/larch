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
    if ! command -v python3 >/dev/null 2>&1 || ! python3 - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    then
        if [ "${PY_LINT_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: python3 >= 3.11 not found — skipping py-lint direct relevant target"
            PY_LINT_SKIP_WARNED=1
        fi
        return 0
    fi
    for tool in ruff pylint pyright; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing="${missing}${missing:+ }$tool"
        fi
    done

    if [ -n "$missing" ]; then
        if [ "${PY_LINT_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: Python lint tools not found on PATH ($missing) — skipping py-lint direct relevant target"
            PY_LINT_SKIP_WARNED=1
        fi
        return 0
    fi

    append_target_once py-lint
}

maybe_append_py_test_target() {
    if ! command -v python3 >/dev/null 2>&1 || ! python3 - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    then
        if [ "${PY_TEST_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: python3 >= 3.11 not found — skipping py-test direct relevant target"
            PY_TEST_SKIP_WARNED=1
        fi
        return 0
    fi
    if ! python3 -m pytest --version >/dev/null 2>&1; then
        if [ "${PY_TEST_SKIP_WARNED:-0}" -eq 0 ]; then
            echo "WARNING: python3 pytest not found — skipping py-test direct relevant target"
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
    while IFS= read -r f; do
        case "$f" in
            scripts/read-result-env.sh|scripts/read-result-env.md)
                append_target_once test-read-result-env
                append_target_once test-design-structure
                ;;
            scripts/test-read-result-env.sh|scripts/test-read-result-env.md)
                append_target_once test-read-result-env
                ;;
            skills/design/scripts/parse-design-argv.sh|skills/design/scripts/parse-design-argv.md)
                append_target_once test-parse-design-argv
                append_target_once test-design-structure
                ;;
            skills/design/scripts/test-parse-design-argv.sh)
                append_target_once test-parse-design-argv
                ;;
            skills/design/scripts/design-init-runparams.md)
                append_target_once test-design-structure
                ;;
        esac
        case "$f" in
            scripts/test-step0b-router-flag-recovery.sh|scripts/test-step0b-router-flag-recovery.md|python/session_env.py|skills/design/scripts/design-init-runparams.sh|skills/design/scripts/design-init-runparams.md)
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
                ;;
            python/upgrade_larch.py|python/test_upgrade_larch.py)
                append_target_once py-test
                ;;
        esac
        case "$f" in
            skills/design/scripts/plan-review-continuation.sh|skills/design/scripts/plan-review-continuation.md|skills/design/scripts/test-step3-review-cap.sh|skills/design/scripts/test-step3-review-cap.md)
                append_target_once test-step3-review-cap
                ;;
        esac
        case "$f" in
            skills/design/scripts/persist-retally-step3-env.sh|skills/design/scripts/persist-retally-step3-env.md|skills/design/scripts/test-persist-retally-step3-env.sh|skills/design/scripts/test-persist-retally-step3-env.md)
                append_target_once test-persist-retally-step3-env
                ;;
        esac
        case "$f" in
            skills/design/scripts/design-step3-state.sh|skills/design/scripts/design-step3-state.md|skills/design/scripts/test-design-step3-state.sh|skills/design/scripts/test-design-step3-state.md)
                append_target_once test-design-step3-state
                ;;
        esac
        case "$f" in
            skills/design/scripts/design-step2b-drafter.sh|skills/design/scripts/design-step2b-drafter.md|skills/design/scripts/test-design-step2b-drafter.sh|skills/design/scripts/test-design-step2b-drafter.md|scripts/launch-codex-drafter.sh|scripts/launch-codex-drafter.md|scripts/test-launch-codex-drafter.sh|scripts/test-launch-codex-drafter.md|scripts/parse-drafter-output.py|scripts/parse-drafter-output.md|scripts/test-parse-drafter-output.sh|scripts/test-parse-drafter-output.md)
                append_target_once test-design-step2b-drafter
                append_target_once test-launch-codex-drafter
                append_target_once test-parse-drafter-output
                ;;
        esac
        case "$f" in
            skills/design/scripts/auto-fix-plan-commands.sh|skills/design/scripts/auto-fix-plan-commands.md|skills/design/scripts/test-auto-fix-plan-commands.sh)
                append_target_once test-auto-fix-plan-commands
                ;;
        esac
        case "$f" in
            python/agents.py|python/test_agents.py)
                append_target_once test-launch-codex-exec
                append_target_once test-launch-codex-ci
                append_target_once test-launch-cursor-ci
                append_target_once test-parse-codex-usage
                append_target_once test-token-vendor-scrapers
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
            python/agents.py|python/test_agents.py)
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
            scripts/lib-scope-anchor-handoff.sh)
                append_target_once test-plan-review-loop
                append_target_once test-run-step3-review
                append_target_once test-launch-claude-subprocess
                append_target_once test-lib-scope-anchor-handoff
                ;;
        esac
        case "$f" in
            python/issue_wire.py|python/test_issue_wire.py|python/redact.py|python/gh.py|python/rendering.py|python/test_rendering.py|.claude/rules/gh-body-file.md|AGENTS.md|SECURITY.md|agent-lint.toml|docs/issue-anchored-plan.md|docs/linting.md|skills/design/scripts/test-design-publish.sh|skills/design/scripts/test-plan-review-scope-anchor.sh|skills/design/scripts/test-design-pause-resume.sh|scripts/test-legacy-title-prefix-literals-scope.sh)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                append_target_once test-design-structure
                append_target_once test-review-structure
                append_target_once test-research-structure
                ;;
        esac
        case "$f" in
            scripts/lib-net.sh|scripts/lib-net.md|scripts/test-lib-net.sh|scripts/test-lib-net.md)
                append_target_once test-lib-net
                ;;
        esac
        case "$f" in
            scripts/resolve-upstream-larch-repo.sh|scripts/resolve-upstream-larch-repo.md|scripts/test-resolve-upstream-larch-repo.sh|scripts/test-resolve-upstream-larch-repo.md)
                append_target_once test-resolve-upstream-larch-repo
                ;;
            scripts/file-failure-report-cross-repo.sh|scripts/file-failure-report-cross-repo.md|scripts/test-file-failure-report-cross-repo.sh|scripts/test-file-failure-report-cross-repo.md)
                append_target_once test-file-failure-report-cross-repo
                ;;
            skills/implement/scripts/stall-recovery-report.sh|skills/implement/scripts/stall-recovery-report.md|skills/implement/scripts/stall-recovery-report-allowlists.tsv|skills/implement/scripts/test-stall-recovery-report.sh|skills/implement/scripts/test-stall-recovery-report.md|skills/implement/references/stall-recovery.md)
                append_target_once test-stall-recovery-report
                ;;
        esac
        case "$f" in
            scripts/ship-pr.sh|scripts/ship-pr.md|scripts/test-ship-pr-rebase.sh|scripts/test-ship-pr-rebase.md)
                append_target_once test-ship-pr-rebase
                ;;
        esac
        case "$f" in
            scripts/lib-external-launcher-common.sh|scripts/lib-external-launcher-common.md|scripts/test-lib-external-launcher-common.sh|scripts/test-lib-external-launcher-common.md)
                append_target_once test-lib-external-launcher-common
                ;;
        esac
        case "$f" in
            python/agents.py|python/test_agents.py)
                append_target_once test-run-external-agent
                ;;
        esac
        case "$f" in
            python/blocker.py|python/test_blocker.py)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                append_target_once test-blocker
                ;;
            python/issue_query.py|python/test_issue_query.py)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                append_target_once test-issue-query
                ;;
            python/admission.py|python/test_admission.py)
                append_target_once test-implement-admission
                ;;
            python/dirty_tree.py|python/test_dirty_tree.py)
                append_target_once test-check-mid-run-dirty-tree
                append_target_once test-check-scope-reduction-marker
                ;;
            python/bootstrap.py|python/test_bootstrap.py)
                append_target_once test-implement-bootstrap
                append_target_once test-implement-bootstrap-invoke
                append_target_once test-parse-bootstrap-routing-envelope
                ;;
            scripts/implement-preflight.sh|scripts/implement-preflight.md|scripts/test-implement-preflight.sh|scripts/test-implement-preflight.md)
                append_target_once test-implement-preflight
                ;;
            scripts/implement-finalize.sh|scripts/implement-finalize.md|scripts/test-implement-finalize.sh)
                append_target_once test-implement-finalize
                ;;
        esac
        case "$f" in
            python/oos.py|python/test_oos.py)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                ;;
            python/*.py)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                ;;
            python/fixtures/**)
                maybe_append_py_test_target
                ;;
            skills/report-tokens/SKILL.md|skills/report-tokens/scripts/plot-cost-over-time.py|skills/report-tokens/scripts/plot-cost-over-time.md|docs/run-logs.md)
                append_target_once py-test
                ;;
            python/migrated-scripts.tsv)
                append_target_once lint-retired-scripts
                maybe_append_py_test_target
                ;;
            skills/review/scripts/emit-tally.sh|skills/review/scripts/emit-tally.md|skills/review/scripts/test-emit-tally.sh|skills/review/scripts/test-emit-tally.md)
                append_target_once test-emit-tally
                ;;
            skills/review/scripts/tally-code-votes.sh|skills/review/scripts/tally-code-votes.md|skills/review/scripts/test-tally-code-votes.sh|skills/review/scripts/test-tally-code-votes.md)
                append_target_once test-tally-code-votes
                ;;
            skills/review-and-fix/scripts/review-and-fix.sh|skills/review-and-fix/scripts/review-and-fix.md|skills/review-and-fix/scripts/test-review-and-fix.sh|skills/review-and-fix/scripts/test-review-and-fix.md)
                append_target_once test-review-and-fix
                ;;
            python/pyproject.toml|python/ruff.toml|python/pyrightconfig.json|python/.pylintrc|python/requirements-dev.txt|python/requirements-test.txt)
                maybe_append_py_lint_target
                maybe_append_py_test_target
                ;;
        esac
    done <<< "$MODIFIED_FILES"

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
