### FINDING_1: Step 18b failure logs are empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `append_failure_best_effort` creates failure log paths but does not redirect failing helper stdout/stderr into them, so execution issues can point to empty logs after `token-report.sh` or `write-final-report.sh` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] `STEP17_EMITTED_PRESENT` is parsed but unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 18b parses `STEP17_EMITTED_PRESENT`, but orchestration prose/guards do not use it; reviewers disagree whether this is in scope, but the shared risk is a dead KV being mistaken for load-bearing state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Step 18b can abort before emitting tail KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.sh` uses `set -euo pipefail` without an ERR trap or guaranteed tail emission, so unexpected helper/session rehydration failures can leave the orchestrator without `EMIT_BODY` / `WFR_RC`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: `validate_ship_pr_state` rejects key-empty state files and changes classify behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: Adding a `saw_key` / empty-file rejection to `validate_ship_pr_state` makes existing blank or comment-only `ship-pr-state.sh` files cause `classify` and other existing callers to exit 3 instead of falling back to session-env behavior as before.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt: Address the concern above.

### FINDING_5: State validation parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check_ship_pr_state_format` duplicates parsing logic from `validate_ship_pr_state`, creating drift risk for future format-rule changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] `stall-recovery-report.sh` is growing large
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The already-large multi-subcommand `stall-recovery-report.sh` continues to grow, increasing maintenance cost, though the reviewer marked this as not blocking the extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `clear-stall` treats absent disk state as failed clear
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: `clear-stall` emits `CLEARED=false` when `ship-pr-state.sh` is absent, so a successful recovery from a session-only/in-memory stall can be routed to terminal failure instead of creating a minimal cleared state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt: Address the concern above.

### FINDING_8: `seed-terminal-state` mishandles empty-but-present state files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A zero-byte or comment-only existing `ship-pr-state.sh` is treated as malformed instead of absent/fresh, blocking durable terminal stall seeding and `[STALLED]` rename behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: `rewrite_ship_pr_state_keys` interpolates unescaped values into dynamic awk
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` builds awk source by embedding file/CLI values directly; values containing quotes, backslashes, newlines, or awk metacharacters can corrupt rewrites and may enable command execution under some awk implementations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_10: Missing empty/comment-only state-file harness cases for clear/seed paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The stall-recovery harness lacks dedicated blank/comment-only `ship-pr-state.sh` cases for `clear-stall` and `seed-terminal-state`, so regressions around those edge cases could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Step 18 KV parsing with `awk -F=` truncates embedded equals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 18 parses wrapper KVs with `awk -F= print $2`, which would truncate future values containing `=`, though current boolean KVs are safe and one reviewer marked this pre-existing/out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Step 18b harness misses session-env and plugin-root fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-step-18b-final-report.sh` stubs helper behavior without exercising production `session-env.sh` rehydration or `plugin-root.env` fallback, so regressions in load-bearing env wiring may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_13: MV-failure tests do not assert disk state remains unchanged
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `clear-stall` / `seed-terminal-state` mv-failure harness cases check emitted KVs but not that on-disk `STALL_TRACKING` and file contents remain unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: E1 KV-before-exit testing only covers mv failures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not cover temp-read or destination-read assertion failures, so helpers might abort without the promised `CLEARED=false` / `SEEDED=false` KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Structural pin omits `STEP17_EMITTED_PRESENT` parse requirement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh` does not require the Step 18 prose to keep parsing `STEP17_EMITTED_PRESENT`, so that wrapper-emitted KV could be dropped without structural lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: `.step17-emitted` non-write sentinel is only checked in one harness case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Later Step 18b harness cases could regress and write `.step17-emitted` without failing CI because the absence/unchanged sentinel is only asserted in the first case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Step 18b E2 harness uses stubs instead of real renderers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The E2 harness stubs `write-final-report` / `token-report`, so real renderer/env interactions are not cross-tested here; reviewer marked this out of scope because renderer authority remains elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: `clear-stall` and `seed-terminal-state` lack tmpdir boundary validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: These subcommands do not use sibling `validate_tmpdir_path` / canonical directory checks, so a symlink or outside writable `--implement-tmpdir` could redirect atomic state writes outside the intended session boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `plugin-root.env` sourcing can redirect helper execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Malicious tmpdir content could alter `PLUGIN_ROOT` and cause attacker-controlled helper execution, but the reviewer marked this as the pre-existing Step 18 trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] `record-attempt` writes unsanitized argv into attempts file
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-attempt` prints unsanitized `--class` / `--signature` values into attempts state, allowing crafted CLI args to corrupt attempts format; reviewer marked it outside this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Missing prebody snapshot can make `cmp` report changed body
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-teardown-boundary-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: If `.step18-prebody` is missing while `.step17-emitted` exists, `cmp` can treat an unchanged report as changed and trigger a full body re-emit; some reviewers marked this as pre-existing/out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-teardown-boundary-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Step 18 no longer has `--print-stdout` as a Bash-output backstop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt
- **Severity**: latent
- **Concern**: Removing `--print-stdout` means the collapsible Bash duplicate no longer backs up summary body visibility; reviewers describe this as an intentional/documented trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt: Address the concern above.

### FINDING_23: Failed mv can leave temp-file orphans
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` / `seed-terminal-state` mv failures can leave `ship-pr-state.sh.tmp.*` files behind in `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `SEEDED=false` terminal path lacks retry/abort guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If seed-fresh fails when no prior state exists, the orchestrator may proceed to bug-comment behavior without durable `STALL_TRACKING`; reviewer marked this pre-existing ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] `read-session-env-key.sh` lacks explicit trailing `exit 0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The script relies on the last emit succeeding rather than ending with an explicit `exit 0`; reviewer marked this as a clarity issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: Structural test omits non-empty `summary-final.md` emit guard pin
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-implement-structure.sh` does not pin the planned `EMIT_BODY && WFR_RC=0 && -s summary-final.md` guard, so orchestration prose could drop the non-empty summary check while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Operational-failure KV emission is implemented and tested
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the planned `CLEARED=false` / `SEEDED=false` emission on operational failures and related guards are implemented/tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] NEVER #20 non-write boundaries are preserved
- **Reviewer(s)**: dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewers report the wrapper does not emit `summary-final.md` or write `.step17-emitted`, preserving prompt-side ownership of the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt: Address the concern above.

### FINDING_29: Step 18b command substitution hides emitted KVs from tool stdout
- **Reviewer(s)**: dyn-teardown-boundary-output.txt
- **Severity**: important
- **Concern**: The Step 18 Bash fence captures `step-18b-final-report.sh` output in `_step18b_out` and parses it internally but does not re-print it, so the LLM orchestrator may not see `EMIT_BODY` / `WFR_RC` even though NEVER #20 depends on them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-boundary-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `EMIT_BODY` gate is stricter than prior inline flag
- **Reviewer(s)**: dyn-teardown-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the new `EMIT_BODY` gate correctly requires `WFR_RC=0` and non-empty `summary-final.md`, hardening the old path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-boundary-output.txt: Address the concern above.

### FINDING_31: Unused `token_rc` variable in Step 18b
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never read or emitted, adding reviewer noise and possible future confusion about whether a KV exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Bash 3.2 constructs appear acceptable
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the branch does not introduce forbidden Bash 4+ constructs and uses patterns already present in the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Round 1 already tightened state handling and plugin-root rebinding
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes prior round changes already tightened empty/comment-only state handling and fixed `PLUGIN_ROOT` rebinding after `plugin-root.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_34: Step 18b contract doc contradicts rooted-path requirement
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.md` says helper paths must be rooted under `$IMPLEMENT_TMPDIR`, but its emit-decision section still shows cwd-relative `summary-final.md`, `.step18-prebody`, and `cmp` examples, risking reintroduction of the rooted-path bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.
