## Decision 1: Cleanup scope
- **Question**: Should cleanup extend beyond `skills/design/SKILL.md` literal?
- **Resolution**: Clean `skills/design/SKILL.md` + `skills/design/references/*.md` + `skills/design/scripts/tally-plan-review.sh` + `skills/design/scripts/test-tally-plan-review.sh` + `scripts/test-design-structure.sh` (only the assertion on /design Step 0 argv shape). Leave `scripts/session-setup.sh` and other top-level helpers alone — `--caller-env` remains live for `/review` and `/implement`.
- **Source**: user (Step 1c question 1 — initial choice 'everything' narrowed after push-back to '/design subtree only')

## Decision 2: Anti-pattern entries to remove
- **Question**: Remove both Anti-pattern #4 and #7, or only #4?
- **Resolution**: Remove both #4 (NEVER pass --caller-env when SESSION_ENV_PATH empty) and #7 (NEVER emit step breadcrumbs when SESSION_ENV_PATH non-empty), and renumber the remaining anti-patterns. Both triggers are now unreachable.
- **Source**: user (Step 1c question 2)

## Decision 3: Conditional simplification approach
- **Question**: Keep conditional structure and hard-code to standalone, or remove conditionals plus dead branches entirely?
- **Resolution**: Remove conditionals plus their dead branches. For `if SESSION_ENV_PATH non-empty: A else: B` patterns, keep only the standalone (B) branch.
- **Source**: user (Step 1c question 3)

## Decision 4: Hard constraint — per-Bash-block prelude must keep the source line
- **Question**: Does removing the awk LARCH_CLAUDE_PLUGIN_ROOT recovery snippet break any non-nested execution path?
- **Resolution**: No. The remaining prelude line `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh` sources CLAUDE_PLUGIN_ROOT from the design source-env written by Step 0's `write-design-current-env.sh`. The awk recovery snippet was a defensive nested-mode fallback for when CLAUDE_PLUGIN_ROOT was unset; per #2588's env-var fix, the symlink-keyed source-env is now the canonical recovery path. The single source-line prelude is the issue's explicit acceptance criterion.
- **Source**: codebase (`scripts/write-design-current-env.sh` writes CLAUDE_PLUGIN_ROOT into the source-env; current-design-env-$PPID.sh symlink already populates it)

## Decision 5: Hard constraint — token-ledger rehydration in Step 3, 3.5, 3b
- **Question**: The `read-session-env-key.sh --key LARCH_TOKEN_SESSION_ID` blocks in Step 3 / 3.5 / 3b rehydrate token-ledger state from SESSION_ENV_PATH. If those branches are removed, does the token ledger break for standalone /design?
- **Resolution**: No. `token-ledger.sh mark` falls back to its own resolution when `LARCH_TOKEN_SESSION_ID` is unset. Standalone /design has no parent token session to rehydrate from; the rehydration calls are pure dead code in standalone-only mode. Remove them.
- **Source**: codebase (`scripts/token-ledger.sh` — `mark` accepts empty session id)

## Decision 6: Test fixture for /larch:relevant-checks smoke test
- **Question**: What runs as the end-to-end smoke test acceptance gate?
- **Resolution**: `make lint` (which exercises `bash scripts/relevant-checks.sh` plus the design-structure / tally tests) plus a structural verification that `grep -c SESSION_ENV_PATH skills/design/SKILL.md == 0` and `grep -c -- '--caller-env' skills/design/SKILL.md == 0`. No live `/design --trivial <issue>` end-to-end run is required during plan execution; verification is offline.
- **Source**: codebase (issue acceptance says "`/larch:relevant-checks` passes; `/design --trivial <issue>` runs end-to-end on a smoke test" — the literal /design end-to-end smoke is captured in the existing `scripts/test-design-structure.sh` and `skills/design/scripts/test-*.sh` harnesses that `make lint` exercises)

## Decision 7: Non-goals (what we explicitly do NOT change)
- **Question**: What stays untouched?
- **Resolution**:
  - `scripts/session-setup.sh` (still in use by `/review` and `/implement`)
  - `scripts/test-session-setup-presence-defaults.sh` / `scripts/test-session-setup-repo-fallback.sh` (test session-setup, not /design)
  - `skills/shared/external-reviewers.md` / `skills/shared/subskill-invocation.md` (document --caller-env for other callers)
  - `skills/review/SKILL.md` / `skills/implement/SKILL.md` (still use --caller-env legitimately)
  - The single-line prelude `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ...` — kept as-is in every Bash block.
- **Source**: codebase (grep evidence from Step 1c)
