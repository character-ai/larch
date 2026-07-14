## Review Phase Detail

No review rounds completed.

## Exec Issues and Warnings
Exec Issues (1):
  1. Step 5: self-review mode: Claude subagent review complete
Warnings (4):
  1. The diff widens the grandfathered complexity ratchet baseline, which G-Enf-2 says must only shrink.
  2. Deviation. `python/complexity-baseline.json` raises two existing `close_priors_main` rows: C901 `metric` 12 -> 13 and PLR0912 `metric` 14 -> 15. G-Enf-2 requires a graduated-defect baseline to be g...
  3. Mitigating context tied to the same diff: the growth adds no new grandfathered identity (the `close_priors_main` rows pre-exist), and it traces to a required integrity branch, the new `_issue_state...
  4. The rest of the diff conforms. The post-close and post-label re-verifications in `audit_runs.py`, `combine_issues.py`, and `oos_filer.py` implement G-Py-8 and G-Ext-2 with narrow, named exception h...

## Architectural invariants

The changed code adds post-mutation read-backs that confirm an issue actually reached the closed state, or a priority label actually landed, after each `gh` mutation; centralizes the reconcile-status and postcondition-unverified literals into named module constants; swaps a typed signal literal in for a bare string at the two sites that build the Codex gate detail; and reroutes Markdown fence detection in the assessment-kind parser through the shared balanced-fence scanner. The one touched ship-recovery path only substitutes those named constants for the same status strings it already emitted, finalizing a manually merged PR as merged, and introduces no new rebase, force-push, reopen, or other pre-merge mutation against a merged or closed PR.

None of these changed lines weakens a hard gate using inputs the gated entity itself authored, reuses a persisted step result against mismatched inputs, turns a missing required run-log artifact into a silent status string, embeds a session-tmpdir pointer into a committed run-log field, freezes a terminal outcome label onto an in-flight run, drops a reviewer or voter slot without a per-slot record, or emits machine-parsed output for evidence it never read. Where the new label read-back cannot confirm its postcondition, it records a durable tool-failure entry rather than a silent status. The changed code upholds every absolute invariant.

## Architectural guidelines

The changed code applies one consistent remedy: after a `gh` close or label mutation reports wrapper success, it re-reads the issue state or label set and treats an unconfirmed postcondition as a loud, fail-closed failure. That remedy lands at the three sites where a silently-open issue or a missing label would corrupt later selection: prior-audit close, combined-away and stale close, and OOS priority labeling. The read-backs go through the typed read and list wrappers, narrow to named exceptions only, annotate their status values, and return the fail-closed result on any unparseable or failed read. An existing sibling close site already carries this same read-back pattern, and the remaining untouched close sites are terminal disposition closes that do not re-enter a selection scan, so the class fix is applied where the hazard exists.

The newly introduced reconcile-status and postcondition-unverified wire literals are defined once as module-level constants and consumed by the ship-recovery and issue modules; the reconcile stdout stays byte-identical, pinned by a new test. Fence detection now reuses the shared balanced-fenced-block scanner behind a reason-annotated, function-level import that keeps the core layer off the design layer at import time, and the duplicated Codex gate signal strings are replaced by a typed literal with named members co-located with their dataclass and validated at the parse boundary.

Unlike the prior revision of this work, the current change no longer alters the grandfathered complexity ratchet baseline; it instead holds the affected function's branch count flat by extracting two small, typed, individually tested helper functions, so the earlier baseline-widening concern no longer applies. Every changed area traces to the task and is covered by an added or updated test. The changed code conforms to the written guidelines with no deviation.

## /implement run 8890DECA-FA59-4A8A-BBC1-EEA5B968AB5D: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 01:15:46
- **Cost**: 💰 TOTAL ~$34.03: Claude $33.32, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.71  |  Tokens: 39758k
- **Issue**: #7316: https://github.com/character-ai/larch/issues/7316
- **Plan review**: N/A
- **Plan coverage**: 0/0 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: N/A
- **Code review**: 1/1 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 1
- **Warnings**: 4
- **Run logs**: `larch-logs/implement/8890DECA-FA59-4A8A-BBC1-EEA5B968AB5D/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 53.1.3

<!-- larch:run-summary v=1 -->
