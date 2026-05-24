### FINDING_1: Plan contradicts itself on `require_key` enumeration
- **Reviewer(s)**: 11 reviewers (cursor-arch, cursor-edge, cursor-pragmatic, cursor-requirements, cursor-dyn-plan-coherence ×3, cursor-dyn-harness-integration, cursor-dyn-state-key-enumeration, cursor-innovation ×2, codex-arch, codex-pragmatic, codex-edge, codex-innovation, codex-requirements, codex-dyn-plan-coherence)
- **Severity**: important
- **Focus area**: correctness
- **Concern**: The UPDATED `scripts/ship-pr.sh` section instructs: "After the heredoc, append `BAIL_FAILURE_DETAIL_LOG` to the existing `require_key` enumeration in `main()` (the loop at L2438-2445) ... `NO_LOGS_COMMIT` and `IMPLEMENT_TMPDIR` ... add them to the loop for completeness alongside `BAIL_FAILURE_DETAIL_LOG`." Then Failure modes #2 reverses: "the safer path is: emit the 3 new keys from `write_initial_state` but do NOT add them to the L2438-2445 `require_key` enumeration in this PR — leaving the validation surface unchanged keeps backward-compat for hand-written legacy state files. I'll go with this safer approach." An implementer cannot tell which path is normative. The first directive would break legacy state files; the second would leave validation incomplete.
- **Suggested revision**: Delete the contradictory half. Pick ONE normative direction in the UPDATED `scripts/ship-pr.sh` section (recommend the safer "do NOT extend require_key" path, since the issue body's Constraints section requires "existing callers ... continue to work unchanged"). Remove the "After the heredoc, append..." sentence. Reword Failure modes #2 to record the analysis but not flip the decision.


### FINDING_2: DECISION_2 promises a shared ordered key-list constant; implementation steps don't create one
- **Reviewer(s)**: 8 reviewers (cursor-dyn-plan-coherence ×3, cursor-dyn-state-key-enumeration, cursor-pragmatic, cursor-requirements ×2, codex-arch, codex-innovation, codex-pragmatic, codex-requirements, codex-dyn-plan-coherence)
- **Severity**: important
- **Focus area**: architecture
- **Concern**: The Approach section asserts DECISION_2 voted: "one ordered key-list constant inside `ship-pr.sh` shared by `write_initial_state()` and `require_key` validation." The UPDATED `scripts/ship-pr.sh` section then describes only individual `printf` line edits and a manual `require_key` append — no single ordered constant is actually introduced. The ship-pr.md update text claims "the in-script ordered key list (consumed by both `write_initial_state` and `require_key`) is the single source of truth." That document text would be inaccurate.
- **Suggested revision**: Either (a) explicitly add a `LARCH_SHIP_PR_STATE_KEYS=( ... )` Bash 3.2-compatible indexed array near the top of `scripts/ship-pr.sh`, used by both `write_initial_state()` (loop over the array) and the `require_key` enumeration (same loop), and update the ship-pr.md prose accordingly — OR (b) downgrade the DECISION_2 outcome description: keep the inline printf approach in `write_initial_state()` (because DECISION_3 declined the dedicated lib) and remove the "shared by both" claim from both Approach and ship-pr.md. Recommendation: (b), because the dialectic voted against the dedicated lib precisely on grounds that one consumer doesn't justify shared infrastructure.


### FINDING_3: Plan asserts "38-key heredoc parity" but the actual count is 39
- **Reviewer(s)**: 5 reviewers (cursor-dyn-plan-coherence ×3, cursor-dyn-state-key-enumeration, codex-dyn-plan-coherence, codex-dyn-state-key-enumeration)
- **Severity**: important
- **Focus area**: correctness
- **Concern**: The plan repeatedly references a 38-key target. A precise count: current `write_initial_state()` emits 36 keys (per `scripts/ship-pr.sh:260-296`); the SKILL.md L1550-1559 bullet list enumerates 39 distinct keys (including DESIGN_ONLY_DONE, EXPECTED_SESSION_ID, EXPECTED_TMPDIR_BASENAME_PREFIX in addition to the three plan-mentioned BAIL_FAILURE_DETAIL_LOG / NO_LOGS_COMMIT / IMPLEMENT_TMPDIR); the orchestrator's observed heredoc (in run DDE4E370 transcript) writes 38 keys. After adding the 3 new keys to `write_initial_state()`, it emits 39 keys.
- **Suggested revision**: Replace every "38-key" / "38 keys" occurrence in the plan with the verified count "39 keys" (post-update state). State explicitly that this matches the SKILL.md L1550-1559 spec, NOT the older orchestrator-runtime heredoc count.


### FINDING_4: Empty argv values (`--branch-name ""`) are silently treated as omitted; conflicts with heredoc semantics
- **Reviewer(s)**: 5 reviewers (codex-dyn-plan-coherence, codex-edge, codex-pragmatic, codex-requirements ×2)
- **Severity**: important
- **Focus area**: correctness
- **Concern**: Approach says argv-init flags either pass values or are omitted. Edge cases says: "a caller passing `--branch-name ""` (explicit empty) is treated identically to omitting the flag — the auto-derivation fallback runs. This matches the orchestrator's heredoc behaviour where empty values produce empty state keys (e.g. `NEW_VERSION=`)." The latter claim is wrong: the orchestrator's heredoc writes `NEW_VERSION=` (literal empty value, NOT auto-derived); but the proposed `${INIT_BRANCH_NAME:-$branch}` pattern would substitute `$branch` (the git-derived value) when `INIT_BRANCH_NAME` is empty. The two paths diverge for empty values, breaking the documented byte-for-byte parity claim.
- **Suggested revision**: Distinguish "flag omitted from argv" from "flag passed with empty value." Recommended pattern: a separate `INIT_BRANCH_NAME_SET=false` companion variable set to `true` when the flag is parsed (regardless of value); `write_initial_state` checks the `_SET` flag, not the value-emptiness. When `_SET=true`, emit the value (even if empty); when `_SET=false`, fall back to derivation. Document this pattern in the Edge cases section.


### FINDING_5: New harness cases wired under "`make test-ship-pr-state`" but harness has no `test_*` dispatcher
- **Reviewer(s)**: 4 reviewers (cursor-dyn-harness-integration, cursor-innovation ×2, cursor-requirements, codex-pragmatic)
- **Severity**: important
- **Focus area**: risk-integration
- **Concern**: The plan proposes new test cases as named functions (`test_init_state_from_argv_fresh`, etc.) and claims they "run under `make test-ship-pr-state`." But `scripts/test-ship-pr.sh` uses inline blocks under a `section=state` dispatch guard (around L840-1184), not a named `test_*` function dispatcher. The plan's wire-up step is unspecified.
- **Suggested revision**: Either (a) reword the test cases as inline blocks inside the existing `section=state` guard, matching the existing pattern — OR (b) introduce a `test_*` function dispatcher in `test-ship-pr.sh` as part of this PR. Recommend (a). Update the testing strategy bullet to say "add new cases under the existing `section=state` guard at scripts/test-ship-pr.sh:840-1184" instead of naming them as functions.


### FINDING_6: `usage()` location cited at L80-100 is wrong
- **Reviewer(s)**: 3 reviewers (cursor-innovation ×2, cursor-pragmatic, cursor-requirements)
- **Severity**: nit
- **Focus area**: code-quality
- **Concern**: The plan says "Update the usage banner (`usage()` function, around L80-100 — read to confirm location)." Actual `usage()` is around L32-37 in `scripts/ship-pr.sh` (per Cursor reviewers who read the file). The "— read to confirm location" hedge is fine for an implementer but the cited line range is misleading.
- **Suggested revision**: Replace "around L80-100 — read to confirm location" with "(actual location around L32-37; verify via `grep -n '^usage()' scripts/ship-pr.sh`)."


### FINDING_8: CR/LF test covers 2 of 7 flags while claiming "validation covers all 7"
- **Reviewer(s)**: 3 reviewers (codex-arch, codex-innovation, cursor-requirements)
- **Severity**: nit
- **Focus area**: code-quality
- **Concern**: `test_init_state_argv_rejects_cr_lf` is described as testing `--branch-name`, then "Repeat for one other flag (e.g., `--issue-number`) to confirm the validation covers all 7." Testing 2 of 7 inputs doesn't confirm validation covers the other 5.
- **Suggested revision**: Either (a) parameterize the case to loop over all 7 flag names with a fixed CR-bearing sentinel value, asserting each rejection, OR (b) reword the comment to "spot-check that the validation pattern works for two representative flags; the other 5 use the same `case "$INIT_*" in *$'\r'*|*$'\n'*) ...` boilerplate." Recommend (a) since the loop is trivial in Bash 3.2.


### FINDING_9: NO_LOGS_COMMIT in state is parity-only, not behavioural — clarify this
- **Reviewer(s)**: 2 reviewers (codex-pragmatic, cursor-innovation ×2)
- **Severity**: important
- **Focus area**: correctness
- **Concern**: Plan adds `NO_LOGS_COMMIT` to the state file but `ship-pr.sh` consumes it from argv (`--no-logs-commit`) via `NO_LOGS_COMMIT` variable, not by reading state. Adding it to state doesn't change resume behaviour. The Approach makes it sound like adding the key is functional; it's observational only (for log-rendering parity with the orchestrator's heredoc).
- **Suggested revision**: Add a short note in the Approach or Failure modes section: "Adding `NO_LOGS_COMMIT` to the state file is for observability/heredoc-parity only — `ship-pr.sh` already consumes the value from `--no-logs-commit` on every invocation. Resume runs read from argv, not from state, so `NO_LOGS_COMMIT` in state is informational."


