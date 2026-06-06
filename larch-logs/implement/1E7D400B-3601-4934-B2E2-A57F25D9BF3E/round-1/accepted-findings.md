### FINDING_10: `safe_step_value` allows invalid suffixes on exact-only bare steps
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The optional suffix branch appears to apply to bare steps `2`, `3`, `5`, and `6`, allowing malformed tokens like `3a` or `5-max-retries` into public titles instead of mapping them to `unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Split the regex so 2/3/5/6 are exact-only and only 8-15 accept suffix or hyphen forms; add negative tests for 2a, 3a, 5-max-retries, and 6a.


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


