Reviewing cited locations to confirm merge groupings before producing the normalized finding list.
Normalized aggregator output from 18 reviewer slots into 5 merged findings (two thematic clusters, two related but distinct harness/wiring issues, one test-contract gap).

### FINDING_1: `safe_step_value` allowlist must not shrink production stall-step tokens
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-script-contract
- **Severity**: important
- **Concern**: The proposed `safe_step_value` tightening (numeric plus `<N>a`/`<N>b` only) is narrower than live `STALL_STEP` shapes documented in `scripts/ship-pr.md` and pinned by harnesses. Production tokens such as `10-detached-head`, `12-detached-head`, `10-max-retries`, `12-max-retries`, `12d`, `9a1`, `12b`, `12c`, `10-head-changed`, `8b`, and `bump-branch-guard` would fail the closed enum and be sanitized to `unknown`, degrading issue titles and public diagnostics while classify/resume routing may still use the raw step. Regressions called out include `test-stall-recovery-report.sh` case 13g (`10-detached-head`), case 7 (`10-max-retries`), and case 20a (`12d`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Anchor full-string allowlist to ship-pr exit_stall inventory in scripts/ship-pr.sh and scripts/ship-pr.md; reject only unmatched strings (e.g. 8ainjected) not hyphenated production suffixes
  - From Codex-Arch: Use a full-string parser-safe pattern that preserves known step-family tokens, e.g. numeric 2/3/5/6/8-15 plus either one lowercase suffix letter or hyphenated lowercase/digit words; reject values containing other bytes like 8a<script>
  - From Cursor-Edge: Require anchored full-string match that rejects trailing injection (e.g. 8a<script>) but still accepts documented hyphenated/suffixed tokens from ship-pr.md; add one harness assert that 10-max-retries and 12d survive safe_step_value unchanged.
  - From Codex-Edge: Anchor the sanitizer without shrinking the existing safe token set, e.g. preserve the current numeric alnum/hyphen step family plus explicit symbolic tokens while rejecting unsafe trailing bytes like 8a<script>
  - From Codex-Innovation: Revise the plan to anchor the existing allowed token family instead of narrowing it, e.g. use a full-string regex over numeric, alnum/hyphen step-family tokens, and explicit bump-branch-guard/unknown while rejecting unsafe trailing bytes.
  - From Cursor-Pragmatic: Keep existing production suffix shapes (single-letter like `12d`, hyphenated like `10-detached-head` / `10-max-retries`) in the allowlist while rejecting unconstrained trailing injection (e.g. anchored regex); or explicitly update those harness cases in the same PR
  - From Cursor-Requirements: Production STALL_STEP tokens such as 10-detached-head 10-max-retries 12d and 12-detached-head (scripts/ship-pr.md:128-129) no longer match; classify/issue titles regress to unknown and harness case 13g (skills/implement/scripts/test-stall-recovery-report.sh:335-341) breaks Keep the existing step-family allowlist (same shapes as resume_hint_for) or enumerate all ship-pr stall tokens; do not restrict to <N>a/<N>b only; add an explicit regression row for a hyphen-suffixed token if the sanitizer changes
  - From Cursor-dyn-script-contract: Specify full-string match (reject 8a<script> trailing junk) while preserving known suffix shapes already in harnesses; add explicit regression note for 12d and hyphenated step tokens

### FINDING_2: Step 4 dedup stdout normalization must populate top-level `ISSUE_NUMBER` / `ISSUE_URL`
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Cursor-dyn-key-chain-integrity
- **Severity**: important
- **Concern**: When `/larch:issue` deduplicates the recovery issue, stdout emits `ISSUE_1_DUPLICATE=true` with `ISSUE_1_DUPLICATE_OF_NUMBER` / `ISSUE_1_DUPLICATE_OF_URL` but not `ISSUE_1_NUMBER` / `ISSUE_1_URL`. The plan’s Step 4 prose only maps indexed create keys and says to “also persist” duplicate keys; it does not clearly require writing canonical `ISSUE_NUMBER` / `ISSUE_URL` aliases. Step 8 loads `ISSUE_NUMBER` from `stall-recovery-issue.env`; an empty key forces the manual terminal-comment path instead of posting to the canonical duplicate target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify exact fallback mapping: set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_NUMBER/ISSUE_1_URL when present, else from ISSUE_1_DUPLICATE_OF_NUMBER/ISSUE_1_DUPLICATE_OF_URL; optionally also persist the raw duplicate keys
  - From Cursor-Edge: In step 4 normalization prose, when ISSUE_1_DUPLICATE=true (or ISSUE_1_NUMBER absent), set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_DUPLICATE_OF_NUMBER/URL; keep DUPLICATE keys as optional metadata.
  - From Cursor-Innovation: In step 4 prose: when ISSUE_1_DUPLICATE=true or ISSUE_1_NUMBER is absent, set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_DUPLICATE_OF_NUMBER/URL (still persist DUPLICATE keys if useful)
  - From Codex-Innovation: Make Step 4 explicit: write ISSUE_NUMBER from ISSUE_1_NUMBER else ISSUE_1_DUPLICATE_OF_NUMBER, and ISSUE_URL from ISSUE_1_URL else ISSUE_1_DUPLICATE_OF_URL. Optionally keep duplicate-specific keys too.
  - From Codex-Requirements: Revise Step 4 to explicitly set `ISSUE_NUMBER` / `ISSUE_URL` from `ISSUE_1_NUMBER` / `ISSUE_1_URL`, or from `ISSUE_1_DUPLICATE_OF_NUMBER` / `ISSUE_1_DUPLICATE_OF_URL` on dedup.
  - From Cursor-dyn-key-chain-integrity: Rewrite step 4: when ISSUE_1_DUPLICATE=true, map ISSUE_1_DUPLICATE_OF_NUMBER→ISSUE_NUMBER and ISSUE_1_DUPLICATE_OF_URL→ISSUE_URL (mirror oos-pipeline.md:48-49). Else map ISSUE_1_NUMBER/URL. Align Edge cases with Files section.

### FINDING_3: `test-implement-structure.sh` wiring grep is too broad to catch wrong `--input-file`
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: A proposed grep that only requires some `--input-file` prose line to mention `stall-recovery-issue-input.md` can pass even when the actual Step 4 `/larch:issue` call still uses `stall-recovery-bug-body.md` (e.g. via a comment on the same line), restoring the zero-item filing bug the plan targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Narrow the assertion to the actual /larch:issue --input-file line in Step 4 and also reject stall-recovery-bug-body.md on that line.
  - From Codex-Requirements: Match the actual Step 4 `/larch:issue --input-file` command and reject the raw body path, e.g. require `/larch:issue --input-file .*stall-recovery-issue-input.md` and fail on `--input-file .*stall-recovery-bug-body.md`.

### FINDING_4: Structure harness same-line `--input-file` constraint conflicts with wrapped Step 4 prose
- **Reviewer(s)**: Cursor-dyn-script-contract
- **Severity**: important
- **Concern**: A grep requiring `stall-recovery-issue-input.md` on the same line as `--input-file` conflicts with natural prose wrapping in `stall-recovery.md` Step 4. The harness may fail after a doc rewrite, or authors may contort prose onto one line to satisfy the assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-contract: Put `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` on one line in step 4, or grep the step-4 section for both tokens without same-line constraint

### FINDING_5: Unsafe-step regression may accept a truncating sanitizer (`8a` instead of `unknown`)
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The planned unsafe-step test for input like `8a<script>` may assert emitted step `8a` while the stated full-string contract requires non-matching values to become `unknown`. A truncating sanitizer would pass the test but violate the injection-rejection contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Assert the exact emitted step is `unknown` for `8a<script>` and also assert the trailing injected bytes are absent.
