### FINDING_1: Missing bash-absence skip for finalize parity module
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` lacks the bash-only module-level `pytestmark` used by merge parity tests, so bash-less environments can hard-fail or silently avoid meaningful finalize parity enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Verify-main matching diverges from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python verify-main logic does not match bash fallback semantics for PR-number suffix/substring handling and can mark admin or empty-title merge subjects unexpected when bash would verify them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_11: Postbump checkpoint corrupt handling diverges from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python treats symlinked or oversized `.postbump-phase` files as always corrupt, while bash may clear valid legacy tokens and continue, causing checkpoint parity failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: CI-fix rebase/pending path can force-push without bash-equivalent verification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-write-mutation-output.txt, dyn-force-push-safety-output.txt
- **Severity**: important
- **Concern**: Post-rebase and `CI_FIX_REBASE_PENDING` push paths can skip bash’s post-rebase verify gates, persist pending state too broadly, or force-push after empty/failing local verification cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-write-mutation-output.txt, dyn-force-push-safety-output.txt: Address the concern above.


### FINDING_15: Planned ship-layer tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` lacks plan-required coverage for postbump preflight refresh/blocking, failure stall routing, phase overwrite guards, sentinel behavior, and partial-cleanup flush behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: Recovery failure plumbing is not fully fail-closed in tests/API
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Recovery-failure paths lack integrated regression coverage, and `load_or_recover_manifest()` can return a manifest even when `recovery_ok` is false, allowing future callers to render or commit after failed recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: Missing test for non-rebase plain-push behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no explicit test asserting that non-rebase CI-fix pushes use plain `git push` and do not route through force-with-lease.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Finalize subprocess parity coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` only side-by-side compares a small subset of bash/Python behavior, leaving cleanup, verify-main, postbump force-push outcomes, and teardown rename branches free to drift from `implement-finalize.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_20: Behind-main probe catches `AssertionError` as success
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `stage_and_push` catches `AssertionError` from git probe helpers and substitutes success, which can skip defer-rebase and allow a plain push on divergent history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: Postbump exception mapping is too coarse
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Postbump maps all caught exceptions to `status=rebase-failed`, obscuring force-push, remote-check, or other phase-specific failures and misrouting retry/resume logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_24: `rebase_and_push` does not abort active rebase after initial fetch failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If a prior rebase left the repo mid-rebase and the next initial fetch fails, Python can continue in a dirty rebase state instead of aborting the in-progress rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_25: Finalize teardown does not kill session background processes
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python `teardown()` omits bash’s `kill_session_background_processes()` behavior, so Codex/Cursor/CI helper processes tied to `$IMPLEMENT_TMPDIR` can survive finalize cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_26: Successful-merge issue rename incorrectly requires OPEN state
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_rename_issue()` refuses non-OPEN issues for all rename branches, but bash only gates the stalled rename on OPEN and still attempts the successful `[DONE]` rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_3: Finalize parity gate is brittle and does not enforce skip contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity_gate.py` hardcodes an exact pass count and does not verify the intended bash-only skip behavior, so adding tests can break CI and broad skips can evade fail-closed parity enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_30: `_write_ship_state` preserves stale stall/bail keys
- **Reviewer(s)**: dyn-state-write-mutation-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` read-modifies-writes existing state and does not clear or synchronize several stall/bail keys, so a prior stalled/bailed run can leave misleading KVs alongside `PHASE=done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-write-mutation-output.txt: Address the concern above.


### FINDING_31: State boolean reads use first duplicate while writes use last duplicate
- **Reviewer(s)**: dyn-state-write-mutation-output.txt
- **Severity**: latent
- **Concern**: `_state_bool` returns the first matching key while `_write_ship_state` loads duplicate keys with last-wins semantics, so corrupted or edited state can hydrate differently than it rewrites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-write-mutation-output.txt: Address the concern above.


### FINDING_32: Resume counters are reset instead of hydrated
- **Reviewer(s)**: dyn-state-write-mutation-output.txt
- **Severity**: latent
- **Concern**: Pre-merge-loop `_write_ship_state` calls and in-memory loop initialization reset retry/rebase counters to zero even when pending state was hydrated from a resumed run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-write-mutation-output.txt: Address the concern above.


### FINDING_6: Force-push lease OID resolution is duplicated and can use stale refs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-force-push-safety-output.txt
- **Severity**: important
- **Concern**: Remote head/OID resolution before force-push is duplicated across finalize and CI-monitor paths, and `postbump()` can prefer stale local `origin/<branch>` data after a live remote check instead of resolving the current remote tip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-force-push-safety-output.txt: Address the concern above.


### FINDING_9: Finalize unit branch coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks plan-listed unit coverage for verify suffix/admin paths, postbump force-push outcomes, protected-branch behavior, teardown rename branches, cleanup outcomes, and log commit gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


