# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing stale scout-manifest cleanup coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` does not test that stale `scout-plan-manifest.json` and temp scout files are removed after plan rewrite paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness cases that pre-seed scout-plan-manifest.json, invoke postplan/apply paths (--site gate-b, discussion-round2, inline retry), and assert manifest and temp scout files are removed.


### FINDING_2: Missing Step 5 scout argv eligibility tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-run-step5-review.sh` lacks argv coverage for missing or empty pre-scout sidecars and for `step2-spawn-coder.txt` without the eligibility marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add argv spy tests: marker present + missing scout file still passes --pre-scouted-manifest; spawn-coder.txt only still forces --dynamic-archetypes 0 and omits pre-scout.


### FINDING_21: Plan review loop lacks dynamic-slot manifest coverage
- **Reviewer(s)**: dyn-integration-completeness-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` asserts scout is not called but does not pre-seed `scout-plan-manifest.json` to verify dynamic-slot dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-integration-completeness-output.txt: Add cases that write a filtered `scout-plan-manifest.json` before `run_loop`, assert `dyn-cursor-plan-*` / `dyn-codex-plan-*` rows in `plan-review-slots.ndjson`, and add a companion case with no manifest asserting static-only dispatch.


### FINDING_3: Missing launcher-level scout filter tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-codex-drafter.sh` does not cover launcher wiring for scout cap, duplicate, or reserved-slug filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add drafter stub modes emitting over-cap, duplicate, or reserved-slug scout JSON; assert normalized scout-plan-manifest.json after launch.


### FINDING_7: Token vendor scraper tests omit required scout manifest argv
- **Reviewer(s)**: dyn-contract-boundaries-output.txt
- **Severity**: important
- **Concern**: `scripts/test-token-vendor-scrapers.sh` invokes implement launchers without required `--scout-manifest-path`, so the smoke test can exit before exercising vendor token recording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-boundaries-output.txt: Pass `--scout-manifest-path "$(dirname "$MF")/scout-coder-manifest.json"` (or an equivalent sibling path under the same parent as `--manifest-path`) in both launcher invocations, and audit any other non-`step2-implement.sh` callers the same way.


