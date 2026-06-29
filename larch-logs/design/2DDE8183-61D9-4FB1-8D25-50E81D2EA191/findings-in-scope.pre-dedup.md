### FINDING_1:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: blocking
- **Focus area**: security
- **Location**: scripts/hook-bg-poll-guard.sh:560-566,692-696
- **Concern**: Step 4 gets a foreground-probe allowlist, but the mutation-deny path still only protects step-3, step-5c, step-final-summary, and step-8.. Scenario: A live `design-step4-tail` marker can be spoofed by a Bash write to `.completed/step-4`, which would release the guard without the wrapper actually finishing.
- **Proposed resolution**: Add `step-4` to `bash_attempts_terminal_sentinel_mutation` and extend the hook tests to deny writes to `.completed/step-4` while `design-step4-tail` is live.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:412-480
- **Concern**: The relevant-check routing update only adds the new lint/test files, not the shell implementation files that actually arm and release the new markers.. Scenario: Changes to `scripts/hook-bg-poll-guard.sh`, `scripts/hook-no-progress-guard.sh`, `skills/design/scripts/design-step3b-tail.sh`, or `skills/implement/scripts/step-6-entry.sh` can land without selecting the new hook or structure harnesses, so the bg-wait coverage stays unverified on the files it protects.
- **Proposed resolution**: Add direct-target rules for the edited shell sources so the hook and structure tests run when those files change, not just when the new lint or test files change.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:191-360; python/larch/implement/dispatch_commit_route.py:722-930; skills/implement/scripts/step-6-entry.sh:1-40
- **Concern**: New marker writers never bootstrap `.completed/` before writing terminal sentinels. Scenario: On the self-review path, or any reused tmpdir where `.completed/` is still absent, the step-5-self-review, step-6, or step-7a sentinel write can no-op, so the hooks never observe completion and the bg-wait stays live until timeout
- **Proposed resolution**: Create `.completed` inside each new marker helper or EXIT trap before writing `.completed/step-5-self-review-terminal`, `.completed/step-6-terminal`, or `.completed/step-7a-terminal`



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:1-84
- **Concern**: design-step4-tail never resets its probe-denial counter on entry. Scenario: A relaunch in the same tmpdir, or a prior clamp left behind by a premature notification, can make the first sanctioned `[ -f "$DESIGN_TMPDIR/.completed/step-4" ] && echo DONE || echo WAIT` probe deny immediately, so the documented recovery path is no longer usable
- **Proposed resolution**: Clear `bg-poll-guard-probe-denials.step-4.count` when arming `design-step4-tail`, alongside the no-progress sidecars, just as step-8-ship clears its rc probe counter



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation Phase2
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:500-503; skills/implement/references/extracted-script-registry.md:22; python/larch/implement/dispatch_commit_route.py:783-868
- **Concern**: 1) The plan puts the Step 5 resume marker on `checks-step5-resume` and leaves the documented `skills/implement/scripts/step-5-resume.sh --record-only` fence optional. That wrapper is still a `run_in_background: true` launch, so the new lint will reject the current tree and the real terminal-stall background job stays marker-less.. Scenario: Step 5 resume still runs without `.bg-wait-active` on the `--record-only` path, so Monitor and TaskOutput denial plus no-progress clamping remain inert there.
- **Proposed resolution**: Add the marker to `skills/implement/scripts/step-5-resume.sh` itself, or make the wrapper delegate to a marker-owning entrypoint before any background work. Also add that wrapper to the lint mapping instead of treating it as optional.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:191-260; python/larch/implement/dispatch_commit_route.py:721-814
- **Concern**: New Python-owned bg-wait entry points do not pre-create the completion directory or reset inherited no-progress state before writing the marker.. Scenario: If a fresh tmpdir has no `.completed/` yet, or a prior run left `no-progress-turns.count` or `no-progress-circuit-breaker-armed` behind, the first sentinel write can fail or the next `UserPromptSubmit` can be blocked immediately. That leaves the new Step 3, Step 5 self-review, Step 5 resume, and Step 7a waits unable to release cleanly.
- **Proposed resolution**: Add a shared pre-marker helper for the new Python-owned waiters that `mkdir -p "$tmpdir/.completed"` and clears `no-progress-turns.count` plus `no-progress-circuit-breaker-armed` before writing `.bg-wait-active`, matching the existing shell wrapper setup.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic Phase2
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:412-420
- **Concern**: The new relevant-check routing only names the lint, Makefile, and pre-commit files. It never adds the top-level hook scripts or their test harnesses.. Scenario: Edits to `scripts/hook-bg-poll-guard.sh` and `scripts/hook-no-progress-guard.sh` can slip through `checks run-relevant` without running `test-hook-bg-poll-guard` or `test-hook-no-progress-guard`, so the new marker and clamp behavior can regress unverified.
- **Proposed resolution**: Add direct-target rules for `scripts/hook-bg-poll-guard.sh`, `scripts/hook-no-progress-guard.sh`, and their `scripts/test-hook-*.sh` harnesses so those tests are selected whenever the hook files change.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/checks-repair-loop.md:77-81; skills/implement/SKILL.md:537-540
- **Concern**: Step 6 re-entry is not protected against a stale terminal sentinel. Scenario: The plan adds `.completed/step-6-terminal` for the new `implement-step6-checks` marker, but it never clears or freshness-gates that sentinel before the next `step-6-entry.sh --force-checks true` retry. The existing Step 6 repair contract explicitly reruns the same composite in the same tmpdir, so an old sentinel would make the next run look complete immediately and bypass the new bg-wait guard.
- **Proposed resolution**: Remove or freshness-gate the old `.completed/step-6-terminal` before arming the new marker, or use a run-specific sidecar like the Step 3 pattern so retries cannot inherit completion from a prior attempt



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:420-460
- **Concern**: Relevant-check routing misses the hook-contract files this PR changes. Scenario: A run that touches only `scripts/hook-bg-poll-guard.sh`, `scripts/hook-no-progress-guard.sh`, or `skills/shared/design-background-wait.md` will not automatically run `test-hook-bg-poll-guard` or `test-hook-no-progress-guard`, so the new marker allowlist and circuit-breaker behavior can regress without the required validation
- **Proposed resolution**: Add direct-target rules for those files to `checks_run_relevant.py` and route them to the hook harnesses; keep the new lint route for the bg-wait coverage files



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:721-800; skills/implement/scripts/step-6-entry.sh:45-48; skills/design/scripts/design-step3b-tail.sh:90-150; python/larch/implement/step_7a.py:178-331
- **Concern**: Marker entry plan does not clear the step terminal sentinel before arming .bg-wait-active. Scenario: A retry of Step 3, Step 5 self-review, Step 5 resume, Step 6, Step 7a, or design Step 4 can start with the previous .completed sentinel still present. marker_step_completed/is_step_completed then treat the fresh marker as already complete, so Monitor/TaskOutput denial and the no-progress breaker are disabled for that rerun.
- **Proposed resolution**: Before writing each new marker, best-effort remove only that step's terminal sentinel and its probe-clamp counter when applicable, then write the sentinel again in cleanup before removing the marker.



### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-Hook Coverage Reviewer Phase2
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/hook-bg-poll-guard.sh:559-566; scripts/test-hook-bg-poll-guard.sh:316-330,643-655
- **Concern**: New bg-wait sentinels are released only by sentinel presence, but the plan never extends the terminal-sentinel forgery deny path to the new `.completed/step-4` and implement release files.. Scenario: A live `design-step4-tail` or new implement wait can be completed early by `touch`, truncation, or redirecting into the sentinel path, which clears the marker before the background job actually finishes.
- **Proposed resolution**: Extend `bash_attempts_terminal_sentinel_mutation` to cover `.completed/step-4` plus the new implement terminal sentinels, and add matching forgery assertions alongside the existing step-3 and step-8 cases in `scripts/test-hook-bg-poll-guard.sh`.



