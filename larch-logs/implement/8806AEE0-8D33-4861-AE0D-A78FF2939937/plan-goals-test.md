## Goal
Convert ~50+ remaining scripts in scripts/ and skills/implement/scripts/ to use lib-quiet.sh

## Implementation Plan
## Implementation Plan: Quiet-by-default scripts — Phase 4b

### Goal
Convert all remaining scripts in `scripts/` and `skills/implement/scripts/` to use the quiet-by-default library (`lib-quiet.sh`). After conversion, each script sources `lib-quiet.sh`, calls `larch_quiet_init`, and routes all contract-emitting stdout through `emit`/`emit_kv`/`emit_breadcrumb`. All other stdout/stderr automatically routes to the log file.

### Conversion Pattern

**For `scripts/*.sh`:**
```bash
# After set -euo pipefail, add SCRIPT_DIR if not present, then:
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
```

SCRIPT_DIR definition (only if not already present):
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

**For `skills/implement/scripts/*.sh`:**
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
```
(Add after `set -euo pipefail`; PLUGIN_ROOT can be merged with existing SCRIPT_DIR if one exists.)

**Emit conversion rules:**
- `echo "KEY=$VAR"` → `emit_kv KEY "$VAR"`
- `echo "KEY=literal"` → `emit_kv KEY "literal"`
- `printf 'KEY=%s\n' "$VAR"` → `emit_kv KEY "$VAR"`
- `printf 'KEY=VALUE\n'` → `emit_kv KEY "VALUE"`
- `echo "plain message"` → `emit "plain message"` (only for contract-shaped plain output consumed by callers)
- Stderr output (`>&2`) stays unchanged; after larch_quiet_init it goes to the log
- Internal echo/printf that are NOT part of the script's stdout contract (e.g., inside functions writing to temp files, or clearly internal) do NOT need conversion

**Key exception:** `read-session-env-key.sh` outputs to stdout (its whole purpose is to print a value). Its `printf '%s\n' "$VALUE"` and `printf '%s\n' "$DEFAULT"` are the contract — convert to `emit`.

**Sourced libraries (audit only, no larch_quiet_init):**
- `scripts/lib-*.sh` — grep for `^[[:space:]]*\(echo\|printf\) ` in non-stderr positions; if none or only internal use, leave alone
- `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` — sourced, audit only

### Commit Groups (one commit per group for reviewability)

**Group A — skills/implement/scripts/**
Files: check-review-changes.sh, hook-post-design.sh, hook-stop-fail-close.sh, oos-file-conflict-deps.sh, oos-issue-cap.sh, post-design-boundary.sh, step2-implement.sh
Use PLUGIN_ROOT pattern. step2-implement.sh is 828 lines — focus on contract stdout lines only.

**Group B — Session + identity (scripts/)**
Files: session-setup.sh, session-entry-gate.sh, write-session-env.sh, write-session-id.sh, read-session-env-key.sh
session-setup.sh has many `echo "KEY=$VAR"` → `emit_kv KEY "$VAR"` conversions. session-entry-gate.sh has `printf 'ENTRY_GATE=...'` and `printf 'SKIP_BRANCH_CHECK=...'`.

**Group C — External-agent launchers (scripts/)**
Files: launch-codex-implement.sh, launch-cursor-implement.sh, launch-gemini-implement.sh
These likely have minimal stdout (they spawn subprocesses); audit each for contract output.

**Group D — Ledgers / reports (scripts/)**
Files: timing-ledger.sh, timing-report.sh, token-ledger.sh, token-report.sh, token-claude-source.sh, token-tally.sh
All have contract stdout. token-report.sh and timing-report.sh are ~500 lines each.

**Group E — Tracking-issue infrastructure (scripts/)**
Files: tracking-issue-read.sh, tracking-issue-summary.sh

**Group F — Git wrappers (scripts/)**
Files: git-commit.sh, git-current-branch.sh, git-rebase-abort.sh, git-amend-add.sh, git-checkout-ours.sh, git-show-stage.sh, git-stage.sh, git-sync-local-main.sh
git-current-branch.sh: `echo "BRANCH=$BRANCH"` → `emit_kv BRANCH "$BRANCH"`

**Group G — GH + branch + PR (scripts/)**
Files: gh-pr-checks.sh, create-branch.sh, check-remote-branch.sh, implement-fork-env.sh, extract-closes-issue-from-pr.sh

**Group H — Misc state probes / pre-flight (scripts/)**
Files: capture-session-transcript.sh, check-mid-run-dirty-tree.sh, check-phantom-dirty.sh, check-step-token-budget.sh, check-generators.sh, gather-branch-context.sh, get-issue-context.sh, get-issue-info.sh, get-issue-state.sh, round-trip-detect.sh, preflight.sh

**Group I — Tmpdir + cleanup (scripts/)**
Files: cleanup-tmpdir.sh

**Group J — Other scripts (scripts/)**
Files: agent-model-args.sh, classify-diff-mode.sh, compose-architecture-sketch.sh, compose-pr-summary.sh, compose-plan-goals-test.sh, cursor-auth-flags.sh, cursor-wrap-prompt.sh, drop-bump-commit.sh, false-positive-keywords.sh, generate-codex-implementer.sh, generate-cursor-implementer.sh, generate-gemini-implementer.sh, generate-reviewer-code-robustness-agent.sh, generate-reviewer-plan-fidelity-agent.sh, generate-topology-docs.sh, preflight.sh, promote-release.sh, read-claude-model.sh, read-plugin-version.sh, sleep-seconds.sh, snapshot-untracked.sh, sessionstart-health.sh, ci-rerun-failed.sh, check-changelog-present.sh, lint-mermaid-fences.sh, pre-commit-shellcheck.sh

### Acceptance Criteria
1. Every targeted script sources `lib-quiet.sh` and calls `larch_quiet_init`
2. All contract-shaped stdout uses `emit`/`emit_kv`/`emit_breadcrumb`
3. `make test` passes
4. .md sibling files note FAILURE_LOG=<path> on non-zero exit where applicable

### Key Implementation Notes
- For scripts that already define SCRIPT_DIR, add the source block after the existing SCRIPT_DIR line
- For scripts in skills/implement/scripts/, SCRIPT_DIR goes to `"$(dirname "${BASH_SOURCE[0]}")"` and PLUGIN_ROOT = `$SCRIPT_DIR/../../..`
- The `emit_kv` signature is `emit_kv KEY VALUE` — no quotes around KEY
- Fallback stubs (larch_quiet_init() { :; } etc.) are NOT needed for scripts/ path since lib-quiet.sh is always adjacent. The 3-way fallback in check-bump-version.sh is a special case for scripts that may run from plugin cache paths.
- For most scripts, just the simple `source "$SCRIPT_DIR/lib-quiet.sh"` suffices
- preflight.sh already has SCRIPT_DIR; just add the source line after it
- session-setup.sh already has SCRIPT_DIR; just add the source line after it


## Test plan
Run `make test` after all groups are committed. The existing test-*.sh harnesses test contract output parsing; if tests pass, the emit conversion is correct.
