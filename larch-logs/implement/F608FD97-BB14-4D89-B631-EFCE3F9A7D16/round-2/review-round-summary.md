# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Failure-slice reference is classified as eager instead of conditional
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-load-closure
- **Severity**: major
- **Concern**: The failure-slice reference `finalize-step5-failures.md` is loaded or classified as eager on the default design path rather than being restricted to failure branches. This defeats the intended lazy-load/token behavior and conflicts with the closure test and baseline expectations. The mandatory-read wording should be made recognizable as conditional, then the live closure baseline should be regenerated and verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reword clarify branches to When/If conditionals the scanner recognizes, verify the file is conditional-only in scan_skill output, and regenerate python/skill-closure-baseline.json.
  - From codex-specialist-edge-cases: Place mandatory reads inside concrete failed-* branches or make the central wording classifier-recognized conditional; regenerate the baseline after the slice is conditional.
  - From codex-specialist-testing: Make the directive syntactically conditional for the closure scanner, regenerate the baseline, and run the focused closure test.
  - From dyn-dyn-load-closure: Reword the clarify failure directives so the closure linter’s conditional patterns match (e.g. lead with `When … fails,` / `Only when …`), regenerate the baseline with `python3 python/cli.py lint skill-closure-growth --write`, and keep the pytest asserting `finalize-step5-failures.md` is conditional-only.
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_2: Gate re-entry bypasses the Step 3 runtime read
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-load-closure
- **Severity**: major
- **Concern**: Gate A and Gate C re-entry instructions route directly to `design-step3-entry.sh --reentry` without requiring `plan-review-runtime.md` to be loaded first. This can bypass the Step 3 load-order contract and cause preview, timing, snapshot, or routing behavior to run without the runtime authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-load-closure: Add an explicit “MANDATORY READ `plan-review-runtime.md` before `design-step3-entry.sh`” line to both gate-slice re-entry bullets (or require re-entering the Step 3 section through its breadcrumb + runtime read), and pin that wording in `scripts/test-design-structure.sh` / `skills/design/scripts/test-step3-orchestrator-fence.sh`.
