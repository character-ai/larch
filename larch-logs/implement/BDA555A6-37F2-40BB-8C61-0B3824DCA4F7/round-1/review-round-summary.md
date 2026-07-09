# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: design publish reachability ignores durable publish evidence
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-runlog-gate
- **Severity**: major
- **Concern**: `_design_publish_reached` and the related transcript-reachability checks still key publish evidence off `session-transcript.jsonl` or `.completed` sentinels, but normal design log-publish strips `.completed` and can leave only durable publish artifacts like `manifest.json` and `final-summary.md`. That can let `design log-publish` → `run-log commit` miss required transcript/final-summary rows and commit a silent transcript omission unless a committed execution-issue waiver names it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
  - From dyn-dyn-runlog-gate: Key design publish/transcript reachability off published-tree evidence such as `final-summary.md` (and/or other durable publish artifacts), not `.completed` sentinels; add a regression where `manifest.json` + `final-summary.md` without `session-transcript.jsonl` fails unless committed `execution-issues.md` names the transcript.


### FINDING_6: scrub/pre-scrub tests need manifest.json fixtures
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: existing scrub/pre-scrub integration tests seed run directories without `manifest.json`, but the new completeness gate now fails those fixtures before scrub logic runs, so the tests no longer model the behavior they intend to cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add minimal manifest.json to fixtures or monkeypatch verify_run_log_completeness in scrub-only tests.


