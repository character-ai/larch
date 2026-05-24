## Decision 1: Heredoc reality
- **Question**: Does the orchestrator actually emit a heredoc compose block, or is the issue premise wrong?
- **Resolution**: Verified — recent run `DDE4E370` (and 4 others sampled) emit a 38-line `cat > "$IMPLEMENT_TMPDIR/ship-pr-state.sh" << 'EOF'` block before `ship-pr.sh`. The premise is correct; argv-init extension is justified.
- **Source**: codebase (larch-logs/implement/*/session-transcript.jsonl)

## Decision 2: API shape
- **Question**: Individual flags per key vs single repeated `--init-state-kv KEY=VALUE`?
- **Resolution**: Individual flags per key (`--branch-name`, `--issue-number`, `--run-id`, `--manifest-path`, `--tool-label`, `--expected-session-id`, `--expected-tmpdir-basename-prefix`). Matches existing `--merge` / `--draft` / `--forked` style; type-safe per key; verbose but discoverable.
- **Source**: user

## Decision 3: Key parity
- **Question**: Does `write_initial_state()` need to be extended to emit all 38 keys the heredoc emits?
- **Resolution**: Yes. Add `BAIL_FAILURE_DETAIL_LOG=`, `NO_LOGS_COMMIT=`, `IMPLEMENT_TMPDIR=` (3 keys currently missing). Required for byte-identical replacement of the heredoc.
- **Source**: user

## Decision 4: Resume precedence
- **Question**: When `--state-file` already exists on disk and argv-init flags are also passed, who wins?
- **Resolution**: Existing on-disk state wins (matches issue body). Argv flags are silently ignored on resume. Preserves the current resume contract.
- **Source**: user

## Decision 5: Force-init flag
- **Question**: Include `--force-init-state` (used by stalled-run cleanup paths) in this PR?
- **Resolution**: Yes, include `--force-init-state` in this PR scope. Behaviour: when present + state file exists, overwrite (otherwise existing state wins).
- **Source**: user

## Decision 6: Legacy fallback
- **Question**: When new argv flags are NOT passed but state file is absent (test harness or legacy callers), preserve auto-derivation (git, env vars)?
- **Resolution**: Yes — keep auto-derivations as fallback when flags absent. Each new flag is opt-in; `write_initial_state()` falls back to current behaviour when the flag is empty.
- **Source**: user

## Decision 7: Resume regression test
- **Question**: Add explicit harness case that asserts existing on-disk state wins over argv-init flags?
- **Resolution**: Yes — add resume-precedence test case. Specifically asserts: state file pre-populated → ship-pr.sh invoked with conflicting `--branch-name` value → on-disk value preserved.
- **Source**: user

## Decision 8: SKILL.md prose
- **Question**: After argv-init switchover, what stays / goes in `skills/implement/SKILL.md` L1550-1559?
- **Resolution**: Drop the `Before invoking the script, write…` directive. Keep a brief informational comment listing which state keys ship-pr.sh's argv-init mode populates so operators know the on-disk shape.
- **Source**: user

## Decision 9: Harness file location
- **Question**: New dedicated file vs extension of existing harness?
- **Resolution**: Extend existing `scripts/test-ship-pr.sh`. Add fresh-init / resume-precedence / force-init test cases. Reuses existing `write_subject` + `write_stubs` scaffolding; no new make target needed.
- **Source**: user

## Decision 10: Hard constraints (must not break)
- **Resolution**: 
  - Existing resume semantics: state file on disk wins over argv (verified by harness case)
  - Backward compatibility: callers that compose heredoc + invoke `ship-pr.sh` (no new argv) continue to work — the new flags are opt-in
  - State-file format remains plain `KEY=value` text, never sourced (per `scripts/ship-pr.md` line 17)
  - All keys remain `^[A-Z_][A-Z0-9_]*=.*$` syntax (existing `validate_state_syntax` check)
  - `lib-quiet.sh` contract preserved (already used by ship-pr.sh)
  - Bash 3.2 portability (per `.claude/rules/shell-strict-mode.md`)
  - Sibling `.md` updated for both `scripts/ship-pr.md` and (if new key in `write_initial_state`) any harness `.md` files (per `.claude/rules/script-md-siblings.md`)

## Decision 11: Out-of-scope
- **Resolution**: From issue body — Step 0 consolidation (#2732 family), Step 7a body wrap, Rebase+Phantom consolidation. Plus deferred: changes to ship-pr.sh main loop, resume semantics beyond argv-init, or postbump/postmerge/teardown subcommand routing.
- **Source**: issue body
