### FINDING_1: [OUT_OF_SCOPE] Allowlist TSV is not a runtime source of truth
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `stall-recovery-report-allowlists.tsv` is lint-only while `compose_body_content` is hardcoded, so newly allowlisted fields can pass docs/lint updates but still be omitted from public bug bodies or comments at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_2: Duplicate tmpdir path validators risk inconsistent containment
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Multiple tmpdir path validators repeat canonicalization, symlink, prefix, and regular-file checks. Future path-rule changes could be applied unevenly across failure-detail-log, body-file, and attempts-file handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Retry policy table lacks full doc/code parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The markdown retry-cap table can drift from `retry_cap_for` / `retry_delay_for`; current harness coverage only samples some classes, so documented retry limits may disagree with runtime behavior while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Classification evidence reads uncapped state files
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When no validated detail log is provided, classification reads full `ship-pr-state.sh` and `session-env.sh`, allowing unusually large or stale state content to slow or skew evidence matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Classification file is not confined to IMPLEMENT_TMPDIR
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bug-body` / `bug-comment --classification-file` can read a file outside `$IMPLEMENT_TMPDIR` or through a symlink, weakening the public-output allowlist boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Local session KV parser can drift from shared parser
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Local `kv_get` duplicates `read-session-env-key.sh` parsing behavior, creating drift risk for comments, duplicate keys, and malformed lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Step 18 rehydration prose is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 18a repeats `CLAUDE_PLUGIN_ROOT` rehydration prose already present in Step 18b, making future session rehydration maintenance harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Same-cause override can bypass contract-failure zero-retry handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: For `STALL_STEP` 3 or 6, a contract failure can be reclassified as `same-cause-repeat` after a matching prior signature, allowing an alternate restart despite the zero-retry contract-failure rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Symbolic ship steps can lose resume hints
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Symbolic `STALL_STEP` values such as `12d` can classify as transient infrastructure but still produce `RESUME_HINT=none`, preventing Step 18a from dispatching the expected `ship-pr` retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: First-detection issue filing may run for terminal failure classes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 18a issue filing appears to run on first detection before terminal-only handling, so unrecoverable or contract failures may still create bug issues unless explicitly guarded or documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Step 18a STALL_TRACKING truthiness is underspecified
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Step 18a gate prose does not normatively match classifier truthiness rules, so values like `STALL_TRACKING=True` could be interpreted inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: Step 18a orchestration lacks integration coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no automated harness covering Step 18a orchestration across the reference procedure, `/larch:issue`, Family B wrappers, and dry-run gating, so prose or wiring regressions may not fail existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Stall tracking clear path lacks negative durability tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests cover successful `STALL_TRACKING` clearing but not read-back or `mv` failure paths, so a failed durable clear could still leave Step 18b believing recovery completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Public-output denylist tests miss some evidence inputs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The denylist fixture does not inject sentinels into all classifier evidence paths, such as `NOTE=`, `--bail-reason-only`, or bail reason sentinels, weakening the claim that every input path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: record-attempt atomicity is not stress-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `record-attempt` is only tested with a single append, so read-modify-write corruption under rapid repeated attempts is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] chat-print allowlist lacks dedicated surface test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `chat-print` shares the bug-body composer path and has no distinct test, so future chat-print-only allowlist fields could drift if the surfaces diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: bug-comment attempts file lacks tmpdir containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `bug-comment --attempts-file` can read attempt metadata from outside the current session tmpdir, potentially merging another session's attempt data into a public terminal comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: failure-detail-log validation has TOCTOU exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `failure-detail-log` is validated before `cat`, so a symlink swap between validation and read could feed out-of-tmpdir content into classifier evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: output-file is not confined to IMPLEMENT_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--output-file` can write redacted stall reports outside the session tmpdir when an orchestrator typo provides an unintended path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Issue comment target is not helper-validated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ISSUE_NUMBER` validation is left to orchestrator prose, so drift could post a terminal-failure comment to the wrong public issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: Step 18a omits canonical BAIL_FAILURE_DETAIL_LOG handoff
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 18a classify procedure does not require reading `BAIL_FAILURE_DETAIL_LOG` from `ship-pr-state.sh` and passing it through `--failure-detail-log`, so recovery may classify from lower-quality state/session evidence instead of the canonical detail log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: Terminal-failure stall persistence is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Terminal-failure seeding into `ship-pr-state.sh` has no script or harness coverage, so early bail paths without state files can leave finalize-state non-stalled even while in-memory `STALL_TRACKING=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Retry caps are not mechanically enforced before dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `retry-policy` reports caps but does not gate dispatch, so the orchestrator can exceed documented retry limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: Anti-halt prose can trigger duplicate issue filing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 18a anti-halt wording says to continue dispatch after issue filing every iteration, which may re-invoke `/larch:issue` when `attempt_count>0` and create duplicate bug noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: FAILURE_SIGNATURE fallback diverges without SHA-256
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When SHA-256 tools are unavailable, signature generation falls back to `cksum`, making deduplication behavior environment-dependent unless the fallback is removed, documented, or tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: classify attempts-file lacks tmpdir containment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `classify --attempts-file` can read a path outside `$IMPLEMENT_TMPDIR` for signature comparison if mispointed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Manual synthetic-stall acceptance test is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criterion #10 requires a demonstrated manual synthetic-stall integration run covering Step 18a dry-run consumer behavior and dev-clone issue filing, but the branch only shows script-level and offline harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
