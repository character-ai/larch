### OOS_1: [OUT_OF_SCOPE] acceptance greps for deduped boilerplate not enrolled in CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Acceptance greps for deduped boilerplate are not enrolled in CI. Future edits can reintroduce the long `--run-id` phrase or telemetry triple without failing automated checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional follow-up: add a lightweight harness or lint rule pinning zero hits for the targeted strings.

### OOS_2: [OUT_OF_SCOPE] shared/implement-wrapper paths outside ngram measurement corpus
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Shared and implement-wrapper paths are outside the ngram measurement corpus. Wrapper/shared dedup cannot be regression-tested via measure-ngram-duplication in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept grep-only verification for those paths or extend the corpus if ongoing ratchet is desired.

### OOS_3: [OUT_OF_SCOPE] design Step 0a matches plan (no regression)
- **Reviewer(s)**: dyn-dyn-skill-contracts
- **Severity**: nit
- **Concern**: Design Step 0a matches the plan template: shared cite, retained `design step0-session` Bash block, and full parse/bind list for `SESSION_TMPDIR`, `SESSION_ID`, and reviewer keys. No regression found there.

### OOS_4: [OUT_OF_SCOPE] acceptance grep #4 does not verify retained shortened invocation
- **Reviewer(s)**: dyn-dyn-skill-contracts
- **Severity**: nit
- **Concern**: Acceptance grep #4 (`session setup --prefix` absent from research/review) passes after command removal, but it does not verify that a shortened invocation still exists. That gap let the research/review regressions slip through grep-only validation.

### OOS_5: [OUT_OF_SCOPE] dedup anchors and closure baseline otherwise align with plan
- **Reviewer(s)**: dyn-dyn-skill-contracts
- **Severity**: nit
- **Concern**: `--run-id` long-phrase dedup, six implement-wrapper telemetry cites, and new `skills/shared/run-id-flag.md` / `skills/shared/session-setup-output.md` anchors otherwise align with the plan; `python/skill-closure-baseline.json` token deltas look like expected mechanical fallout from shorter `skills/design/SKILL.md` prose.

