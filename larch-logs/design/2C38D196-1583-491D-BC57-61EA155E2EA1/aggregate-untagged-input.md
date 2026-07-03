### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/core/architectural_guidelines.py:154-177
- **Concern**: The plan adds a new git subprocess call in a production module but does not account for the subprocess-via-runner ratchet.. Scenario: `materialize_implementation_diff` already has two grandfathered direct `subprocess.run` occurrences. Adding the HEAD `rev-parse` as another direct call creates a new unbaselined lint finding, so `make py-lint` or `python3 python/cli.py lint subprocess-via-runner` can fail after implementation.
- **Proposed resolution**: Revise the plan to route the new HEAD resolution through the existing `larch.core.proc.run` seam, or explicitly include the required narrow subprocess-via-runner exemption/baseline update and corresponding lint check.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/core/architectural_guidelines.py:168-188
- **Concern**: Adding a third direct subprocess.run in materialize_implementation_diff conflicts with the subprocess-via-runner ratchet. Scenario: The plan adds HEAD resolution as another subprocess.run in a production module where only the two existing materialize_implementation_diff occurrences are grandfathered, so python3 python/cli.py lint subprocess-via-runner and relevant checks can fail on the proposed diff
- **Proposed resolution**: Use the existing larch.core.proc.run seam for the HEAD, merge-base, and diff calls in this helper, or otherwise avoid adding a new direct subprocess occurrence; update the focused test to monkeypatch that seam rather than adding baseline churn

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:427-596; python/larch/state/closeout.py:225-259
- **Concern**: Plan freezes a private HEAD snapshot inside materialize_implementation_diff but does not bind live-diff materialization to the caller's expected head.. Scenario: Closeout resolves current_head, then pin_note_from_staged_for_current_head materializes after a HEAD advance and can write current_head into durable metadata while storing a fingerprint for the later HEAD. note_fingerprint_stale has the same gap against durable HEAD_SHA when its live fallback runs.
- **Proposed resolution**: Thread a frozen expected head into _materialize_live_diff or materialize_implementation_diff for closeout and note_fingerprint_stale, or recheck HEAD before the live fallback and skip or fail closed when it differs.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/core/architectural_guidelines.py:168-192
- **Concern**: Plan adds another direct subprocess.run in materialize_implementation_diff without covering the subprocess-via-runner ratchet.. Scenario: The new HEAD rev-parse would create a third direct-call occurrence in this production function. python/cli.py lint subprocess-via-runner will leave that occurrence unbaselined, so CI python-lint can fail even when the planned pytest and ruff commands pass.
- **Proposed resolution**: Use larch.core.proc.run for the new HEAD resolution, or include the required inline suppression or baseline update and verify with make py-lint-checks-fast.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:685-708
- **Concern**: The plan explicitly leaves `note_fingerprint_stale` unchanged, but the feature names its live-diff fallback as a distinct residual race from `materialize_implementation_diff` internal atomicity. Freezing whatever `HEAD` the helper sees during fallback does not pin the stale check to the durable note's `HEAD_SHA`.. Scenario: If the durable note is consumable for H1, then the stored snapshot is missing or mismatched, and `HEAD` advances to H2 before the fallback live diff runs, the fallback can fingerprint H2 and drive the stale-note/drop path even though the note was valid for H1.
- **Proposed resolution**: Revise the plan so `note_fingerprint_stale` performs its fallback against a frozen expected head from durable metadata, for example by passing `HEAD_SHA` into a narrowly extended materialization helper, and add a focused test that the fallback diffs `<base_sha>..<durable HEAD_SHA>` rather than live `HEAD`.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-Git Snapshot Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:15-27,34-46; python/larch/core/architectural_guidelines.py:427-437,555-596,685-708
- **Concern**: Plan freezes a fresh live HEAD inside materialize instead of the head already pinned by closeout or durable-note metadata. Scenario: Closeout can resolve H1, then helper materialization can observe H2, while _pin_note_from_live_diff writes durable HEAD_SHA=H1 with an H2 fingerprint. note_fingerprint_stale also reads durable metadata but its live fallback calls _live_fingerprint without the note HEAD, so post-consumable drift can still mark a valid H1 note stale.
- **Proposed resolution**: Thread the existing pinned head through the shared path. Let materialize_implementation_diff accept an optional frozen head SHA, or add an equivalent internal helper. Have pin_note_from_staged_for_current_head pass its head_sha and note_fingerprint_stale pass durable HEAD_SHA. Keep default live HEAD for CLI callers.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-Git Snapshot Correctness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:36-43,91-95; python/larch/core/architectural_guidelines.py:168-183; docs/linting.md:18; python/subprocess-via-runner-baseline.json:150-162
- **Concern**: Plan adds a third git subprocess in a production function without a runner or baseline step. Scenario: materialize_implementation_diff currently has two grandfathered direct subprocess.run occurrences. Adding rev-parse before merge-base creates another occurrence, while the documented linter rejects direct subprocess calls outside core/proc unless handled. The proposed focused ruff lint will miss this, so py-lint or CI can fail after implementation.
- **Proposed resolution**: Resolve HEAD through larch.core.proc.run or another existing compliant runner seam, and update the unit test to patch that seam. If direct subprocess.run is intentionally kept, include the required lint baseline or justified suppression and run py-lint.
