## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Use the existing Python authorization checker as the single policy boundary.

- Add `--trusted-root PATH` to `scripts/file-failure-report-cross-repo.sh`.
- Require `--mutation-context`, `--run-id`, and `--trusted-root` together for non-dry-run mutation paths.
- Forward all three values to `session check-live-mutation-auth`.
- Remove the circular `dirname(context_file)` derivation.
- Pass the authoritative session tmpdir and authoritative run ID from each trusted Python caller.
- Add `trusted_root=design_tmpdir` to the two `/design` checks that currently fail closed.
- Ensure the terminal Tier A helper receives the complete `--mutation-context` / `--run-id` / `--trusted-root` authorization triple.
- Keep `check_live_mutation_auth(...)` and `session check-live-mutation-auth` unchanged.
- Leave already-authoritative Python callers and operator-mode authorization unchanged.

## Files to modify/create

### UPDATED: scripts/file-failure-report-cross-repo.sh

- Extend the usage string and parser with `--trusted-root PATH`.
- Store the parsed trusted root separately from `--mutation-context`.
- Update `check_mutation_auth` to accept the context file, run ID, and trusted root.
- Refuse non-dry-run calls with a missing trusted root before any `gh` operation.
- Pass the caller-provided root to `python3 python/cli.py session check-live-mutation-auth --trusted-root`.
- Remove `--trusted-root "$(dirname "$context_file")"`.
- Preserve Bash 3.2 compatibility and the existing `FILE_FAILURE_REPORT_STATUS` and `FILE_FAILURE_REPORT_FALLBACK_REASON` grammar.

### UPDATED: python/larch/state/_report.py

- Add `--trusted-root str(tmpdir)` to the Tier B helper invocation in `_emit_chat_print_filing_status`.
- Add `--trusted-root str(tmpdir)` to the Tier A dedup helper invocation.
- Verify both invocations continue to forward their existing authoritative mutation context and run ID, so every non-dry-run helper call supplies the complete authorization triple.
- Keep the existing direct Python pre-checks and their `trusted_root=tmpdir` arguments unchanged.
- Preserve status normalization and fallback behavior.

### UPDATED: python/larch/design/design_terminal.py

- Pass `trusted_root=design_tmpdir` in `_reconcile_post_recovery_comment`.
- Add `--trusted-root str(design_tmpdir)` to the terminal Tier A shell-helper invocation.
- Add `--run-id str(_run_id)` to that same helper invocation, alongside its existing mutation context, so it receives the complete authorization triple.
- Pass `trusted_root=design_tmpdir` in the Tier A dedup authorization pre-check.
- Do not refactor terminal filing, reconciliation, or dedup routing beyond these authorization pins.

### UPDATED: scripts/test-file-failure-report-cross-repo.sh

- Update every non-dry-run harness invocation of the helper, including invalid-context, refusal-loop, test-denied, and copied-validator cases, to pass an explicit `--trusted-root`.
- Use the canonical live session directory as the trusted root for cases intended to exercise valid authorization, run-ID mismatch, denial, or downstream fallback behavior.
- Keep a distinct missing-`--trusted-root` refusal case.
- Add a distinct outside-root negative case where a valid-looking context file and matching run ID sit outside the caller-pinned canonical trusted root.
- Keep an in-root context with a wrong run ID to preserve run-identity refusal coverage independently of containment failure.
- Assert that refusal preserves the machine-readable status and performs no `gh` call.
- Keep dry-run authorization-free.
- Update the copied-validator invocation to use the complete new argument contract.

### UPDATED: python/tests/state/test_stall_recovery.py

- Assert both `_report.py` helper invokers include `--trusted-root` with the authoritative implement tmpdir.
- Assert the captured non-dry-run helper argv retains the required mutation context and run ID alongside the new trusted root.
- Retain assertions for prefix-aware bounded payload files.
- Verify the trusted root is not derived from the supplied context-file parent.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Capture authorization keyword arguments for reconciliation and Tier A dedup paths.
- Assert both direct checks receive `trusted_root=design_tmpdir`.
- Capture the terminal Tier A helper argv and assert it contains the complete `--mutation-context`, `--run-id str(_run_id)`, and `--trusted-root str(design_tmpdir)` authorization set.
- Preserve existing fallback-specific tests and machine status assertions.

### UPDATED: python/tests/state/test_session_env.py

- Add focused containment coverage for `check_live_mutation_auth`.
- Confirm a context file with valid authorization and matching run ID is rejected when its parent differs from the caller-pinned canonical session root.
- Keep the checker signature and CLI-required arguments unchanged.

### UPDATED: scripts/file-failure-report-cross-repo.md

- Document `--trusted-root PATH` as required for non-dry-run calls.
- State that trusted callers must pass their authoritative design or implement session tmpdir and matching live run ID.
- Explain that the context file must be an immediate child of that root.
- Update refusal and dry-run guidance without implying protection against a caller that controls all arguments and filesystem state.

### UPDATED: python/stall-recovery-report.md

- Document that Tier A and Tier B helper callers pin the authoritative session tmpdir with `--trusted-root` and provide the matching run ID.
- Clarify that helper authorization delegates containment and run-identity validation to the shared Python checker.
- Keep reporting tiers, payload allowlists, and status normalization unchanged.

### MAY_UPDATE: SECURITY.md

- Verify the existing live-run authorization boundary description remains accurate.
- Update it only if needed to state that the cross-repository helper uses caller-pinned trusted-root containment plus matching run identity.
- Do not expand the documented mutation surface set.

## Edge cases

- Missing context file, run ID, or trusted root must refuse before `gh`.
- A context file outside the pinned root must refuse even when its contents and run ID are valid.
- A context file under the pinned root with a mismatched run ID must refuse independently of containment.
- A context file under a non-canonical or attacker-selected directory must refuse.
- A mismatched or malformed run ID must continue to refuse through the shared checker.
- Symlink, non-regular, unreadable, and missing context files must remain fail closed.
- `LARCH_ISSUE_MUTATION_DENY=true` must remain an earlier refusal.
- `--dry-run` must require no authorization arguments and must make no `gh` calls.
- Tier A dedup lookup failures must retain their existing fail-open reporting semantics only after authorization succeeds.

## Failure modes

- Omitting any member of the `--mutation-context` / `--run-id` / `--trusted-root` triple at a helper caller converts a valid filing path into `mutation-refused`. Add argv assertions for every confirmed Python helper caller.
- Deriving the trusted root from `--mutation-context` would recreate the circular containment check. Tests must use distinct real and attacker-controlled directories.
- Passing a repository root or context-file parent instead of the authoritative session tmpdir may fail canonical-root validation or weaken caller intent.
- Harness cases that omit `--trusted-root` can accidentally test only the new missing-argument refusal. Pin a canonical root for all cases meant to test run identity, containment, denial, or fallback semantics.
- Changing refusal tokens could break machine consumers. Keep existing `KEY=value` output exact.
- Updating only the shell helper would leave the two `/design` direct checks fail closed. Cover both Python call sites explicitly.

## Testing strategy

Run changed-file tests and linters only:

- `bash scripts/test-file-failure-report-cross-repo.sh`
- Targeted `pytest` cases in `python/tests/state/test_stall_recovery.py`
- Targeted `pytest` cases in `python/tests/state/test_session_env.py`
- Targeted `pytest` cases in `python/tests/design/test_design_lifecycle.py`
- Python lint and type checks scoped to `python/larch/state/_report.py`, `python/larch/design/design_terminal.py`, and changed Python tests.
- `bash scripts/lint-bash32.sh` for the changed shell helper and harness.
- Grep the repository for `file-failure-report-cross-repo.sh` invocations and confirm every non-dry-run caller passes the full `--mutation-context` / `--run-id` / `--trusted-root` triple.
- Grep all `check_live_mutation_auth` callers and confirm only the two identified `/design` calls change, while authoritative and operator-mode callers remain untouched.
- Verify the helper usage text and both contract documents match the final argument requirements.

confidence: high
difficulty: HARD
diff_added: 165
diff_deleted: 25
mechanical_churn: false
diff_lines: 190
