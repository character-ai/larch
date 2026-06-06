### FINDING_1: Raw ISSUE_1 metadata is persisted into env output
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `normalize-issue-env` preserves raw `ISSUE_1_*` stdout metadata in `stall-recovery-issue.env`, creating risks of secret leakage and shell metacharacter execution if the file is logged or sourced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Strip non-essential ISSUE_1_* metadata from the env file or pipe preserved values through redact-secrets.sh before atomic_write_text; keep digit-only validation on canonical ISSUE_NUMBER.
  - From codex-specialist-security-output.txt: Persist only canonical validated keys, or shell-quote persisted metadata and require read-session-env-key.sh consumers.

### FINDING_2: safe_step_value still accepts non-inventory tokens
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `safe_step_value` still permits arbitrary hyphenated tokens that are not valid production stall steps, allowing poisoned values such as `10-evil-token` into public issue titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Replace the regex with an explicit allowlist aligned to scripts/ship-pr.md stall tokens (harness already pins several).

### FINDING_3: [OUT_OF_SCOPE] resume_hint_for classifies raw unsafe stall steps
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-kv-output.txt
- **Severity**: latent
- **Concern**: `resume_hint_for` uses raw `stall_step` prefix globs while public output uses sanitized step values, so corrupted values can produce mismatched public titles and recovery dispatch hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply safe_step_value (or the same allowlist) inside resume_hint_for before branch matching.
  - From cursor-specialist-correctness-output.txt: Align resume_hint_for with safe_step_value or sanitize stall_step before resume-hint selection (follow-up).
  - From cursor-specialist-edge-cases-output.txt: Route resume_hint_for through safe_step_value or classify using the sanitized step token
  - From dyn-shell-kv-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] ISSUE_URL accepts arbitrary http(s) hosts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `issue_value_is_url` accepts any `http(s)` URL without validating the host or repository, so adversarial stdout could persist misleading issue metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optionally require ISSUE_URL host to match gh repo view slug or drop URL from env when host mismatches.

### FINDING_5: unsafe-step harness fixture does not catch prefix-glob regressions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-kv-output.txt
- **Severity**: latent
- **Concern**: The unsafe step-value test uses `8a<script>`, which both old and new sanitizers reject, so it would not detect a regression to the old prefix-style matcher that allowed alnum-only suffixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add 8aevil (or similar alnum-only junk suffix) to the invalid-token loop; assert heading is at unknown and suffix is absent.
  - From dyn-shell-kv-output.txt: Add a harness case with `STALL_STEP=8aevil` (or similar) asserting the `issue-input-file` title is `… at unknown` and that `8aevil` is absent from the heading line, alongside the existing `8a<script>` case.

### FINDING_6: Step 4 structure tests under-pin filing and normalization order
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-issue-interop-output.txt
- **Severity**: latent
- **Concern**: Step 4 ordering tests only partially constrain the prose sequence and could pass even if `bug-body`, `issue-input-file`, `/larch:issue`, stdout capture, or `normalize-issue-env` are reordered incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add position checks that bug-body precedes issue-input-file and issue-input-file precedes /larch:issue --input-file.
  - From cursor-specialist-testing-output.txt: Extend index assertions for the full Step 4 call sequence.
  - From dyn-issue-interop-output.txt: Extend the Step 4 `stall_step4_order_line` index checks so `/larch:issue --input-file` precedes `normalize-issue-env`, and optionally that `stall-recovery-issue.stdout` appears in the capture sentence before `normalize-issue-env`.

### FINDING_7: Step 4 documents /larch:issue as a Bash subprocess instead of a Skill invocation
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-issue-interop-output.txt
- **Severity**: important
- **Concern**: `skills/implement/references/stall-recovery.md` describes `/larch:issue` as running inside a foreground Bash block with shell stdout and exit-code capture, but `/issue` is a prompt-side Skill invocation. Following the prose literally can fail to file the recovery issue and leave `normalize-issue-env` without valid stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Reword Step 4 to invoke /larch:issue via the Skill tool, capture returned stdout to the file, and pass a success code only when the Skill call succeeds or relax normalize-issue-env to trust successful counters.
  - From codex-specialist-edge-cases-output.txt: Rewrite Step 4 to invoke /larch:issue via the Skill tool and capture Skill stdout to stall-recovery-issue.stdout before running normalize-issue-env, or add a real scriptable wrapper if process exit capture is required.
  - From codex-specialist-testing-output.txt: Rewrite the branch to invoke /larch:issue via the Skill tool, define a feasible stdout-to-file or sidecar contract for normalize-issue-env, and add a structure assertion for the canonical Skill invocation wording.
  - From dyn-issue-interop-output.txt: Rewrite Step 4 to match OOS filing: invoke `issue` via the Skill tool (`--input-file "$IMPLEMENT_TMPDIR/stall-recovery-issue-input.md"`), persist only machine lines matching `^(ISSUES?_[A-Z0-9_]+)=` from the Skill return into `stall-recovery-issue.stdout`, set `ISSUE_RC` from parsed `ISSUES_FAILED` (0 vs non-zero) rather than a shell exit code, then run `normalize-issue-env` in a separate Bash call; add a `test-implement-structure.sh` grep for “Skill tool” (or “Invoke … issue”) in the Step 4 window.

### FINDING_8: normalize-issue-env harness contract docs omit new Case 20 coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-stall-recovery-report.md` does not document the newly added normalize fixtures, making their expected `REASON` tokens and KV outputs hard to trace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Case 20 subsection documenting each normalize fixture and expected KV outputs.

### FINDING_9: dedup normalize path lacks missing-URL negative coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The dedup normalize path lacks a fixture for missing or invalid URLs, so stale env removal and comment-target failure behavior could regress without test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add case asserting issue-url-missing and stale-env removal on dedup without valid URL.

### FINDING_10: [OUT_OF_SCOPE] normalize-issue-env coverage appears sound
- **Reviewer(s)**: dyn-issue-interop-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that `normalize-issue-env` and its harness cases cover create, dedup, failed-item, non-zero exit, missing exit code, stale-env removal, and write-failure paths, closing the original silent no-op when wired correctly.

### FINDING_11: [OUT_OF_SCOPE] consumer and forked routing remain gated
- **Reviewer(s)**: dyn-issue-interop-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that consumer/`--forked` routing remains gated through `is-larch-dev-clone` and dry-run still skips filing via `DRY_RUN_DECISION`.

### FINDING_12: [OUT_OF_SCOPE] consumer manual filing output is unchanged
- **Reviewer(s)**: dyn-issue-interop-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that printing heading-less `bug-body` content for consumer manual filing is unchanged pre-existing behavior.

### FINDING_13: dedup URL fallback can discard a valid create URL
- **Reviewer(s)**: dyn-shell-kv-output.txt
- **Severity**: latent
- **Concern**: On the dedup fallback path, `normalize-issue-env` can overwrite a valid `ISSUE_1_URL` with an empty or invalid duplicate-of URL, producing `issue-url-missing` despite usable stdout metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-kv-output.txt: Only override `issue_url` when `issue_value_is_url "$duplicate_url"` succeeds; otherwise keep a valid `ISSUE_1_URL` if present, or fail closed if neither URL is valid.

### FINDING_14: [OUT_OF_SCOPE] env body composition strips trailing newline
- **Reviewer(s)**: dyn-shell-kv-output.txt
- **Severity**: nit
- **Concern**: `content=$(…)` strips trailing newlines from the composed env body, which is harmless for current readers but inconsistent with other env writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-kv-output.txt: Address the concern above.
