### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:275-284
- **Concern**: The plan requires RESUME_HINT=none but never says how to preserve it through classify()'s unconditional _resume_hint_for() call.. Scenario: After the guard sets klass=operator-action, line 284 still runs _resume_hint_for(). operator-action is not in the early none set, postmerge-flush sanitizes to unknown, and phase=postmerge falls through to step8-shippr at line 119. The planned tests would still fail and the spurious reship path remains.
- **Proposed resolution**: In the expected-postmerge branch set hint="none" directly and skip _resume_hint_for(), or add operator-action to the early none return set in _resume_hint_for(). Document the chosen approach in the _classify.py plan section.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:UPDATED
- **Concern**: The postmerge guard predicate lists only positive checks for preterminal-outcome; it does not exclude active post-merge flush failure evidence.. Scenario: Stale preterminal-outcome from an earlier pre-push refresh can remain in classifier evidence while a real postmerge-flush stall occurs. With the same phase, stall_step, and terminal MERGE_RESULT, substring presence of preterminal-outcome would still match and return operator-action/none, hiding redaction-failed or manifest-recovery-failed failures the plan says must stay on normal classification.
- **Proposed resolution**: Add explicit guard exclusions for post-merge flush failure tokens (at least redaction-failed, post-merge-refresh-failed, manifest-recovery-failed, and commit-failed) even when preterminal-outcome is present; add a negative fixture with both strings in evidence. The plan is narrowly scoped and addresses the round-1 broad-guard concerns well. Two correctness gaps remain in the proposed classifier work. **`_resume_hint_for` override.** The plan targets `operator-action` / `none` / `postmerge-flush-expected`, but `classify()` always recomputes the hint at line 284. `operator-action` is not in the early non-resumable set, `postmerge-flush` sanitizes to `unknown`, and `phase=postmerge` still falls through to `step8-shippr` — the same reship path the bug reports. **Evidence predicate too permissive.** Requiring `preterminal-outcome` in evidence matches the false-positive route, but stale preterminal text from an earlier pre-push refresh can coexist with a real `postmerge-flush` failure. Without explicit exclusions for post-merge flush failure tokens (`redaction-failed`, `manifest-recovery-failed`, etc.), the guard can hide real failures the plan’s edge cases say must stay on normal classification. Everything else in the plan (ordering after `short_circuit`, same-cause handling, token allowlist, tests, and skipping the unreachable `ship_pr.py` branch) looks aligned with the issue scope.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:275-296
- **Concern**: The prior accepted guard narrowing remains incomplete because the predicate treats any evidence containing `preterminal-outcome` as benign, even when the same evidence contains a current unexpected failure. Scenario: The classifier aggregates persistent state evidence. Stale `preterminal-outcome` text can coexist with a current `redaction-failed`, recovery, or commit failure. The proposed guard would return `operator-action` and hide the real post-merge failure, contrary to the plan's preservation contract
- **Proposed resolution**: Make unexpected failure evidence take precedence over the benign guard, and add one mixed-evidence negative test containing both `preterminal-outcome` and an unexpected post-merge failure reason

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:97-119,284
- **Concern**: Plan omits load-bearing RESUME_HINT binding for operator-action. Scenario: classify() always recomputes hint via _resume_hint_for() after the guard tuple; operator-action is not in the early non-resumable set and postmerge-flush sanitizes to unknown, so phase=postmerge still falls through to step8-shippr at line 119. Acceptance requires RESUME_HINT=none and no reship, but the described guard alone cannot emit that.
- **Proposed resolution**: In _classify.py, add operator-action to the _resume_hint_for() early none set and/or bind hint=none when MATCHED_CLASSIFIER_PATTERN=postmerge-flush-expected instead of discarding the guard hint; add a regression asserting RESUME_HINT=none for the positive fixture.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:144-182
- **Concern**: Expected-postmerge guard lacks exclusion for concurrent real flush-failure tokens. Scenario: The predicate only requires preterminal-outcome substring in combined evidence. Earlier flush_logs_pre output can leave that text in state or logs while a current postmerge-flush stall carries redaction-failed, manifest-recovery-failed, or post-merge-refresh-failed from flush_logs_post. The guard would still return operator-action/none and hide a real failure the plan edge cases require to stay on normal classification.
- **Proposed resolution**: Require the guard to fail when evidence contains unexpected post-merge flush failure markers (at least redaction-failed, post-merge-refresh-failed, manifest-recovery-failed, commit-failed) even if stale preterminal-outcome is present; add a negative test with both preterminal-outcome and redaction-failed in evidence.
