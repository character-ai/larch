### OOS_1: [OUT_OF_SCOPE] Digest feature implementation matches plan wiring, limits {envelope ordering, and test coverage}
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Shared `_write_failure_digest_from_redacted` is wired from both redacted failure exits in `_finish_logged_result` (`no-validation-phases` and generic `checks-failed`). Digest is built only from the redacted log, capped at 8192 UTF-8 bytes with record-boundary truncation, written mode `0600`, and omitted (without turning check failure into structural failure) when digest write fails. `checks_run_relevant_main` and `_checks_relay_line` emit `DIGEST_FILE` before `REDACTED_LOG_FILE`. Skill/reference/docs updates tell orchestrators to full-scan folded composite stdout and prefer the digest for diagnosis while keeping `REDACTED_LOG_FILE` as repair-loop input. Tests cover builder parsing, truncation, DEFECT attribution, integration paths, envelope ordering, and Step 6 composite relay; failure recovery is sound: digest creation failure degrades to the existing `REDACTED_LOG_FILE`-only envelope; structural failures (`redaction-failed`, etc.) still emit no digest; repair-loop input is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] SECURITY.md still documents REDACTED_LOG_FILE-only failure consumption
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: risk-integration `SECURITY.md:238` — The Relevant-checks captured logs paragraph still says orchestrators should read only `REDACTED_LOG_FILE` on failure. `docs/linting.md` and the skills were updated for `DIGEST_FILE`-first consumption, but the security contract doc was not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Pre-commit banner chosen as first_error for typical hook failures
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: correctness `python/larch/implement/checks_run_relevant.py:775-788` — For typical pre-commit failures, first_error is taken from the first marker line, which is often the hook banner (`ruff...Failed`) rather than the lint message on the next line. first_location still carries the useful file:line, and skills allow fallback to the full redacted log, so repair behavior is not blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Space-containing paths break whitespace KV failure envelope parsing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: risk-integration `python/larch/implement/dispatch_commit_route.py:138-141` — Failure envelopes join paths with space-separated KVs; paths containing spaces would break `_parse_whitespace_kv_line`. This predates `DIGEST_FILE` and affects `REDACTED_LOG_FILE` equally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] No unit test for unknown log shape (check=unknown fallback)
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: risk-integration `python/tests/implement/test_checks.py` — The plan's edge case for unknown log shape (`check=unknown` when parsing finds no recognizable checks) has no unit test. A parser regression would still leave `REDACTED_LOG_FILE` as fallback, so repair behavior is safe; only digest usefulness would degrade.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Digest write failure path untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: risk-integration `python/tests/implement/test_checks.py` — The documented "digest write fails → emit `REDACTED_LOG_FILE` only" path in `_write_failure_digest_from_redacted` is untested. The implementation returns `None` and does not convert check failure to structural failure, but nothing locks that contract in.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Structure harnesses do not pin DIGEST_FILE-first consumer contract
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: risk-integration `scripts/test-implement-structure.sh`, `scripts/test-review-structure.sh` — Neither harness pins the new `DIGEST_FILE`-first consumer contract in skill prose. The edits are present in this PR, but future skill edits could drop digest-first guidance without a mechanical CI failure; only the relay/envelope Python paths are tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

---

**Merge notes (for voters, not machine output):**

- **FINDING_1** and input **FINDING_11** describe the same pre-commit banner behavior; kept separate because the edge-cases source tagged **FINDING_11** `[OUT_OF_SCOPE]` while correctness tagged it in-scope.
- **FINDING_3** merges input **FINDING_3** and **FINDING_17** (same `DEFECTS=0` regex false positive).
- **FINDING_4** merges input **FINDING_4, 5, 7, 8, 9** (plan-conformance observations, not distinct fixes).
- Input **FINDING_6** kept as **FINDING_5** (distinct attribution behavior).
- All six inventory slots appear in at least one `- **Reviewer(s)**:` line; `cursor-specialist-testing` appears only in `[OUT_OF_SCOPE]` blocks.

