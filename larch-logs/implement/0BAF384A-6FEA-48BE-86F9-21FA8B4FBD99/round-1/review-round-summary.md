# Review Round 1

- Mode: `diff`
- 9 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing restart signal for stale active cache root
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `upgrade_larch` no longer emits `LARCH_RESTART_REQUIRED=true` when `CLAUDE_PLUGIN_ROOT` points at an older cache-shaped version directory while installed metadata verifies as latest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: /issue helper pytest parity is incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `issue_create` lacks pytest coverage for fetch-issue-details success and validation semantics, cleanup-failed orphan closing, parser edge cases, add-blocked-by failures and retries, allocation bounds, and create-one redaction exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: upgrade marketplace and install failures can be swallowed
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `upgrade_larch` can continue or return success after marketplace refresh or install mutation failures, potentially leaving larch uninstalled or stale without the old recovery diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_13: CLI registry entries lack full resolution smoke tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not verify all new CLI registry domain and verb entries resolve, so broken migrated commands can ship silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Missing quiet stdout and stderr parity in upgrade-larch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `upgrade_larch` does not initialize quiet logging or restore operator-facing stdout the way the bash helper did, so subprocess noise can leak into captured release output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: parse-input body writes can traceback and emit partial stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `issue_create parse-input` does not catch `OSError` while writing body files, so disk or permission failures can produce a traceback and unreliable partial `ITEM_*` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Deleted issue SKILL structural guards lack pytest replacements
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted harnesses for `--blocked-by-issue`, intra-batch dependencies, and related `skills/issue/SKILL.md` prose contracts were not replaced with equivalent pytest guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Forked-repo setup harness parity is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `forked_repo` setup has little coverage for remote rewrite, push-disable, rollback, mirror guard, submodule, and verify-failure paths after the bash harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Forked-repo rollback stops before later post-rewrite failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `forked_repo` restores remote state only inside `phase_remotes`; later submodule or verify failures can leave origin/upstream and pushurl state half-mutated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


