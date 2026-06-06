### FINDING_1: [OUT_OF_SCOPE] `issue-input-file` trusts upstream body redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `cmd_issue_input_file` composes the issue input from a caller-provided body file without a second redaction pass, so secrecy depends on callers always passing the `bug-body` output. This was described as pre-existing/out of scope but also raised as a residual security concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional defense-in-depth: run the composed file through `redact-secrets.sh` before write, or fail closed if `body-file` is not under the expected `stall-recovery-bug-body.md` path.

### FINDING_2: Step 4 issue-env normalization is prompt-only and under-tested
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-issue-flow-output.txt, dyn-orchestrator-docs-output.txt
- **Severity**: important
- **Concern**: Step 4 depends on parsing `/larch:issue --input-file` batch stdout into canonical `ISSUE_NUMBER`/`ISSUE_URL` keys in `stall-recovery-issue.env`, including create and dedup paths, but the mapping is prose-owned and not pinned by a helper, fixture, structure test, or helper-contract doc. A mis-parse can leave Step 8 unable to comment on the intended recovery issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a script normalizer or integration test pinning create and dedup stdout mapping to canonical ISSUE_NUMBER/ISSUE_URL
  - From cursor-specialist-edge-cases-output.txt: Grep-pin ISSUE_1_DUPLICATE_OF_NUMBER and canonical ISSUE_NUMBER in Step 4 window
  - From cursor-specialist-testing-output.txt: Add Step 4 structure greps for normalization keywords plus a fixture test that maps sample ISSUE_1_* stdout to canonical ISSUE_NUMBER/ISSUE_URL including the dedup-only path.
  - From codex-specialist-testing-output.txt: Add structure greps for the env file and indexed/canonical keys, or an executable normalization harness covering create and duplicate stdout.
  - From dyn-issue-flow-output.txt: Add a small `stall-recovery-report.sh` subcommand (or shared normalizer) that consumes `/issue` stdout and emits `stall-recovery-issue.env`, and pin create + dedup fixtures in `test-stall-recovery-report.sh`.
  - From dyn-orchestrator-docs-output.txt: Add a small helper (e.g. `normalize-issue-env` or extend `issue-input-file` post-`/issue`) that reads batch stdout and writes `stall-recovery-issue.env` with the documented create/dedup fallback, and point step 4 at that helper instead of inline parsing rules.
  - From dyn-orchestrator-docs-output.txt: Extend `test-implement-structure.sh` with greps on the Step 4 window for `stall-recovery-issue.env` plus indexed-key normalization (or an integration fixture that feeds representative `/issue` stdout through the helper and asserts the env file contents).
  - From dyn-orchestrator-docs-output.txt: Add a contract subsection (or subcommand entry) describing `stall-recovery-issue.env` keys, write timing (after non-dry-run dev-clone `/issue`), and the canonical `ISSUE_NUMBER`/`ISSUE_URL` mapping so `stall-recovery.md` and `stall-recovery-report.md` stay aligned.

### FINDING_3: [OUT_OF_SCOPE] Generic `/issue --input-file` body splitting footgun
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Generic batch parsing treats in-body `### <title>` lines as new item boundaries. Stall-recovery first-detection bodies avoid that shape today, but untrusted body content remains a general `/issue --input-file` risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for #3568; tracked separately (#3550 / #3547 family).

### FINDING_4: Step 4 can persist issue env after failed `/issue`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-flow-output.txt
- **Severity**: important
- **Concern**: Step 4 does not clearly fail closed before writing `stall-recovery-issue.env` when `/larch:issue` exits non-zero, reports `ISSUES_FAILED>0`, or sets `ISSUE_1_FAILED=true`. An empty or stale env file can make Step 8 skip the intended comment path or target the wrong issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only normalize when /issue exits 0 with ISSUES_FAILED=0 and a resolvable ISSUE_1_NUMBER or dedup ISSUE_1_DUPLICATE_OF_* pair; otherwise omit stall-recovery-issue.env.
  - From cursor-specialist-edge-cases-output.txt: Skip or conditionalize stall-recovery-issue.env on ISSUES_FAILED>0 or ISSUE_1_FAILED; log failure explicitly
  - From dyn-issue-flow-output.txt: Extend Step 4 with the same failure contract as OOS filing: only write `stall-recovery-issue.env` when `/issue` succeeds with no failed items; on failure, skip env normalization, log under `Tool Failures` in `$IMPLEMENT_TMPDIR/execution-issues.md`, and rely on Step 8’s manual-filing fallback.

### FINDING_5: Production stall-token preservation tests miss key ship-pr tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-shell-regex-output.txt
- **Severity**: latent
- **Concern**: The preservation tests for public issue-title step tokens omit documented production tokens, especially `9a1` and other suffixed ship-pr tokens. A regex regression could break real stall titles while current tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add 9a1 9b and 12c to the case20-token loop or pin the full ship-pr stall inventory in a dedicated safe_step_value assert.
  - From cursor-specialist-edge-cases-output.txt: Add 9a1 to production-token preservation cases
  - From cursor-specialist-testing-output.txt: Extend the token loop to the full stall inventory from scripts/ship-pr.md or add a table-driven parameterized case.
  - From dyn-shell-regex-output.txt: Extend the heredoc-fed token list to include at least `9a1`, and ideally the other single-letter suffixed ship tokens (`8b`, `9b`, `12b`, `12c`) so the `[[:lower:]][[:digit:]]?` arm is regression-pinned alongside the hyphen and symbolic arms.

### FINDING_6: [OUT_OF_SCOPE] `resume_hint_for` still prefix-matches raw stall steps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-shell-regex-output.txt, dyn-orchestrator-docs-output.txt
- **Severity**: latent
- **Concern**: `resume_hint_for` still dispatches on prefix-style raw `STALL_STEP` matching while `safe_step_value` uses stricter full-string sanitization for public output. Exotic invalid tokens can therefore route internally as a step-specific recovery while filing publicly as `unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: align resume_hint_for with safe_step_value or document intentional split.
  - From cursor-specialist-edge-cases-output.txt: Route resume_hint_for through safe_step_value or shared allowlist
  - From cursor-specialist-testing-output.txt: consider aligning resume_hint_for with safe_step_value in a follow-up.

### FINDING_7: [OUT_OF_SCOPE] Unsafe-step regression test does not catch alnum-only prefix acceptance
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-flow-output.txt
- **Severity**: important
- **Concern**: The `STALL_STEP=8a<script>` fixture would not catch a regression back to the old loose prefix glob, because the old and new logic both reject that non-alnum suffix. An alnum-only invalid suffix such as `8aevil` is needed to prove suffix rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add an 8aevil assert expecting unknown in the issue title line.
  - From cursor-specialist-edge-cases-output.txt: Add an alnum-only fixture such as STALL_STEP=8aevil that old glob accepts and new regex rejects; assert title uses unknown and excludes the suffix
  - From dyn-issue-flow-output.txt: an alnum-only invalid suffix such as `8aevil` would be a stronger regression pin.

### FINDING_8: [OUT_OF_SCOPE] Consumer/fork manual filing body lacks an explicit title heading
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The consumer/forked path still prints heading-less bug-body content for manual filing, requiring operators to add a `###` title manually outside the dev-clone auto-file path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Out of scope; consider single-mode /issue with explicit title for consumer path in a follow-up

### FINDING_9: [OUT_OF_SCOPE] Consumer path composes unused issue-input file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `issue-input-file` is still composed when `LARCH_DEV_CLONE=false`, producing an unused `stall-recovery-issue-input.md` on the consumer path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Harmless; optionally gate composition on LARCH_DEV_CLONE=true

### FINDING_10: `safe_step_value` allows invalid suffixes on exact-only bare steps
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The optional suffix branch appears to apply to bare steps `2`, `3`, `5`, and `6`, allowing malformed tokens like `3a` or `5-max-retries` into public titles instead of mapping them to `unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Split the regex so 2/3/5/6 are exact-only and only 8-15 accept suffix or hyphen forms; add negative tests for 2a, 3a, 5-max-retries, and 6a.

### FINDING_11: Dry-run skip for issue env normalization is not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 4 structure tests pin filing wiring but not the `DRY_RUN_DECISION` short-circuit that should prevent issue filing and `stall-recovery-issue.env` persistence in dry-run mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Step 4 window greps for DRY_RUN_DECISION and prose that forbids stall-recovery-issue.env writes under dry-run.

### FINDING_12: [OUT_OF_SCOPE] Branch contains unrelated larch-log commit
- **Reviewer(s)**: dyn-issue-flow-output.txt, dyn-shell-regex-output.txt
- **Severity**: nit
- **Concern**: The branch includes an unrelated `chore(larch-logs)` commit alongside the functional stall-recovery fix, though reviewers noted it does not affect the reviewed integration surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-flow-output.txt, dyn-shell-regex-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Step 4 attempt-count source is ambiguous
- **Reviewer(s)**: dyn-orchestrator-docs-output.txt
- **Severity**: nit
- **Concern**: Step 4 gates on `attempt_count==0` but does not name the authoritative source for that value, unlike nearby attempt-tracking prose. This ambiguity predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-docs-output.txt: Address the concern above.
