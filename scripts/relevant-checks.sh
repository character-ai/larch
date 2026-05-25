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
# Mermaid fence lint uses repo-local mmdc (package.json). CI runs `npm ci`
# before `lint-mermaid-fences`; mirror that here when Markdown is in scope so
# pre-commit does not fail with a missing CLI on fresh checkouts.
# ---------------------------------------------------------------------------
ensure_mermaid_cli() {
    if [ ! -f "$REPO_ROOT/package.json" ]; then
        return 0
    fi
    if [ -f "$REPO_ROOT/node_modules/.bin/mmdc" ]; then
        return 0
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "ERROR: npm not found; cannot install Mermaid CLI for lint-mermaid-fences. Install Node.js or run: npm ci"
        exit 1
    fi
    echo "=== Installing Node devDependencies (Mermaid CLI; npm ci) ==="
    (cd "$REPO_ROOT" && npm ci) || {
        echo "ERROR: npm ci failed"
        exit 1
    }
    if [ ! -f "$REPO_ROOT/node_modules/.bin/mmdc" ]; then
        echo "ERROR: npm ci finished but node_modules/.bin/mmdc is missing (check package-lock.json / @mermaid-js/mermaid-cli)"
        exit 1
    fi
}

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

markdown_in_scope=false
for f in "${files[@]}"; do
    case "$f" in
        *.md|*.markdown|*.mdown|*.mkdn) markdown_in_scope=true; break ;;
    esac
done
if [ "$markdown_in_scope" = true ]; then
    ensure_mermaid_cli
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

# ---------------------------------------------------------------------------
# Pre-commit succeeded — run agent-lint on the full repo.
# This catches structural regressions (frontmatter, references, dead scripts,
# etc.) that pre-commit's file-type linters cannot detect. Mirrors the same
# linter invoked by CI's agent-lint job, so developers can catch regressions
# locally before pushing.
# ---------------------------------------------------------------------------
run_post_checks
exit_with_phase_check "$?"
