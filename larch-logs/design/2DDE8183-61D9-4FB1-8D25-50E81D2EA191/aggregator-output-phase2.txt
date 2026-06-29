### FINDING_1: New terminal sentinels can be forged during live bg-wait markers
- **Reviewer(s)**: Cursor-Arch Phase2, Cursor-dyn-Hook Coverage Reviewer Phase2
- **Severity**: blocking
- **Concern**: The marker release path recognizes new sentinels, but the Bash mutation-deny path does not protect all of those sentinel files. A write, touch, truncation, or redirect can spoof completion and release the guard before the wrapped job finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch Phase2: Add `step-4` to `bash_attempts_terminal_sentinel_mutation` and extend the hook tests to deny writes to `.completed/step-4` while `design-step4-tail` is live.
  - From Cursor-dyn-Hook Coverage Reviewer Phase2: Extend `bash_attempts_terminal_sentinel_mutation` to cover `.completed/step-4` plus the new implement terminal sentinels, and add matching forgery assertions alongside the existing step-3 and step-8 cases in `scripts/test-hook-bg-poll-guard.sh`.

### FINDING_2: Relevant-check routing misses hook and marker source files
- **Reviewer(s)**: Cursor-Arch Phase2, Cursor-Pragmatic Phase2, Codex-Requirements
- **Severity**: important
- **Concern**: The run-relevant routing covers the new lint or harness files, but not all source files whose edits change marker, hook, or circuit-breaker behavior. Those edits can land without selecting the hook and structure harnesses that validate the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch Phase2: Add direct-target rules for the edited shell sources so the hook and structure tests run when those files change, not just when the new lint or test files change.
  - From Cursor-Pragmatic Phase2: Add direct-target rules for `scripts/hook-bg-poll-guard.sh`, `scripts/hook-no-progress-guard.sh`, and their `scripts/test-hook-*.sh` harnesses so those tests are selected whenever the hook files change.
  - From Codex-Requirements: Add direct-target rules for those files to `checks_run_relevant.py` and route them to the hook harnesses; keep the new lint route for the bg-wait coverage files

### FINDING_3: New marker writers do not initialize completion and no-progress state
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: blocking
- **Concern**: New marker helpers can write terminal sentinels before ensuring `.completed/` exists, and Python-owned waiters can inherit stale no-progress sidecars. Fresh or reused tmpdirs can fail to release the marker cleanly or can be blocked immediately by the no-progress guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Create `.completed` inside each new marker helper or EXIT trap before writing `.completed/step-5-self-review-terminal`, `.completed/step-6-terminal`, or `.completed/step-7a-terminal`
  - From Codex-Innovation: Add a shared pre-marker helper for the new Python-owned waiters that `mkdir -p "$tmpdir/.completed"` and clears `no-progress-turns.count` plus `no-progress-circuit-breaker-armed` before writing `.bg-wait-active`, matching the existing shell wrapper setup.

### FINDING_4: Reused tmpdirs can inherit stale sentinels or probe counters
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements Phase2, Codex-Generic
- **Severity**: blocking
- **Concern**: New marker entry paths do not consistently clear or freshness-gate prior terminal sentinels and probe-clamp counters. A retry or relaunch in the same tmpdir can look complete immediately, disabling the bg-wait guard or denying the documented foreground probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Clear `bg-poll-guard-probe-denials.step-4.count` when arming `design-step4-tail`, alongside the no-progress sidecars, just as step-8-ship clears its rc probe counter
  - From Cursor-Requirements Phase2: Remove or freshness-gate the old `.completed/step-6-terminal` before arming the new marker, or use a run-specific sidecar like the Step 3 pattern so retries cannot inherit completion from a prior attempt
  - From Codex-Generic: Before writing each new marker, best-effort remove only that step's terminal sentinel and its probe-clamp counter when applicable, then write the sentinel again in cleanup before removing the marker.

### FINDING_5: Step 5 resume remains marker-less on the record-only wrapper path
- **Reviewer(s)**: Cursor-Innovation Phase2
- **Severity**: blocking
- **Concern**: The Step 5 resume marker is attached to the wrong boundary, while the documented `step-5-resume.sh --record-only` wrapper can still launch as a background fence without owning `.bg-wait-active`. That leaves Monitor and TaskOutput denial plus no-progress clamping inactive on that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation Phase2: Add the marker to `skills/implement/scripts/step-5-resume.sh` itself, or make the wrapper delegate to a marker-owning entrypoint before any background work. Also add that wrapper to the lint mapping instead of treating it as optional.
