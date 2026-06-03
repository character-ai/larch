# Review Round 4

- Mode: `diff`
- 4 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_11: Tmpdir resolver dropped dual-read for `.bump-version-armed`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `lib-resolve-implement-tmpdir.sh` (lines 42–43) renamed the eligibility sentinel from `.bump-version-armed` to `.release-armed` without accepting the legacy file. Pre-Phase-5 interrupted `/implement` runs that armed `.bump-version-armed` via `check-bump-version.sh` may no longer resolve after upgrade; Stop/SessionStart hooks can fail open without recovery guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Relocated classify-bump harness dropped CHANGELOG idempotency fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/test-classify-bump.sh` (lines 55–89) removed CHANGELOG-transparent idempotency fixtures while `classify-bump.sh` and `classify-bump.md` still implement and document that walk. A regression breaking transparent “Update CHANGELOG” commit detection could pass `make test-classify-bump` and mis-classify `/release` on legacy bump-pipeline commit stacks (including CHANGELOG-only transparency and CHANGELOG-subject spoofing over `skills/**`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: classify-bump idempotency walk uses HEAD when `--head` is set
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: In `classify-bump.sh` (lines 176–188), the idempotency walk anchors on symbolic `HEAD` rather than `HEAD_COMPARE` when `--head` is supplied without a matching base semantics. Standalone `--head` callers can get `BUMP_TYPE=NONE` while the diff still shows public-surface changes. `/release` is safe when `--base` is mandatory; direct harness or CLI callers are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: agent-lint S030 exclusions reference deleted or typo paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Phase 5 churn in `agent-lint.toml` (lines 1015–1018, 1400) pins non-existent S030 exclusion paths, including `scripts/test-git-stage.sh` and a typo filename `scripts/test-auto-resolve-release notes.md`. Contributors treating exclusions as authoritative may reference missing files; orphan detection for real harnesses can be misconfigured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


