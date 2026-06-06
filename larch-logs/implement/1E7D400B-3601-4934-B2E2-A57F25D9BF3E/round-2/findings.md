Omitted affirmative validation notes that did not state a behavioral risk.

### FINDING_1: [OUT_OF_SCOPE] normalize-issue-env path-containment harness gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Case 21 path-containment tests cover other stall-recovery outputs but not `normalize-issue-env --issue-stdout-file` / `--output-file`; runtime guards exist, so this is a harness-only gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] ISSUE_URL origin is not pinned to GitHub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `issue_value_is_url` accepts any `http(s)://` origin. Current consumers rely on numeric `ISSUE_NUMBER`, but surfacing `ISSUE_URL` later could make this a trust-boundary issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Predictable filtered stdout temp path can be symlinked
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `normalize-issue-env` writes filtered `/larch:issue` stdout to a predictable `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout.filtered.$$` path using shell redirection, allowing a same-UID symlink precreation attack to truncate or overwrite an arbitrary target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Use mktemp inside the validated tmpdir for the filtered file and clean it up with a trap/local cleanup instead of writing to a predictable $$ path.
  - From codex-specialist-edge-cases-output.txt: Use mktemp inside the tmpdir plus trap cleanup, or parse without a predictable temporary filename.

### FINDING_4: write-failed normalization path can hard-fail and leave stale env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-kv-output.txt
- **Severity**: important
- **Concern**: On `atomic_write_text` failure, `normalize-issue-env` exits `1` instead of behaving like other soft filing failures, and it may leave a pre-existing `stall-recovery-issue.env` that Step 8 later consumes, risking skipped fallback handling or comments posted to the wrong issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return exit 0 on write-failed or document stdout-first handling in stall-recovery.md step 4
  - From dyn-bash-kv-output.txt: On `write-failed`, `rm -f "$out_file"` before exiting (mirror `emit_issue_env_false`), and add a harness case that seeds a stale env file then forces `atomic_write_text` failure.

### FINDING_5: Production-token sanitizer harness omits common ship-pr tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The production-token preservation loop omits `10-head-changed`, `12-head-changed`, and `12-max-retries`, so a future regex regression could map common stall steps to `unknown` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add missing ship-pr tokens to the case-20 preservation loop

### FINDING_6: Step 4 structure tests do not pin normalize-issue-env wiring
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash-kv-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: important
- **Concern**: `test-implement-structure.sh` pins headed issue filing but not the required `normalize-issue-env`, stdout capture, or `ISSUE_ENV_WRITTEN` wiring, so future prose could drop canonical env normalization while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Grep step-4 window for normalize-issue-env and stdout capture wiring
  - From cursor-specialist-testing-output.txt: Add grep -Fq 'normalize-issue-env' (and optionally ISSUE_ENV_WRITTEN / stall-recovery-issue.stdout) inside the stall_step4_window assertions.
  - From dyn-bash-kv-output.txt: Extend the Step 4 awk window with greps for `normalize-issue-env`, `stall-recovery-issue.stdout`, and `ISSUE_ENV_WRITTEN`.
  - From dyn-issue-batch-output.txt: Extend the step-4 `awk` window grep pins (or the dry-run integration block) to require `normalize-issue-env`, `stall-recovery-issue.stdout`, and parsing `ISSUE_ENV_WRITTEN`, mirroring the existing `stall-recovery-issue-input.md` wiring pin.
  - From dyn-prompt-protocol-output.txt: Extend the `stall_step4_window` assertions with greps for `normalize-issue-env`, `stall-recovery-issue.stdout`, and `ISSUE_ENV_WRITTEN` (or `stall-recovery-issue.env`), and note the new pins in `scripts/test-implement-structure.md`.

### FINDING_7: [OUT_OF_SCOPE] resume_hint_for still uses raw permissive step patterns
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: latent
- **Concern**: `safe_step_value` now rejects non-canonical public title tokens, but `resume_hint_for` and related signature logic still consume raw `STALL_STEP` with prefix globs, so internal recovery routing can diverge from sanitized public issue metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align resume_hint_for with safe_step_value if internal/public parity is desired (separate change)
  - From dyn-issue-batch-output.txt: Route `resume_hint_for` (and signature hashing if step is meant to be canonical) through `safe_step_value` output, or share one allowlist function used by both resume routing and `issue-input-file` title synthesis.
  - From dyn-prompt-protocol-output.txt: worth tracking separately if internal dispatch ever needs the same grammar as public titles.

### FINDING_8: Step 4 does not define ISSUE_RC/stdout capture protocol
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-kv-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: important
- **Concern**: Step 4 calls `normalize-issue-env --issue-exit-code "$ISSUE_RC"` and expects `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout`, but it does not define how `/larch:issue` stdout is captured or how `ISSUE_RC` is bound. Empty or guessed exit codes can hard-fail normalization or bypass intended failure handling, leaving Step 8 without canonical issue targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document mandatory ISSUE_RC capture from /larch:issue exit status; handle normalize exit 1 like ISSUE_ENV_WRITTEN=false; optionally treat empty --issue-exit-code as invalid input with soft-fail KV emission.
  - From dyn-bash-kv-output.txt: Pin in step 4 that `ISSUE_RC` must be the foreground `/larch:issue` invocation’s process exit code captured in the same Bash block that writes `stall-recovery-issue.stdout`, and add a `test-implement-structure.sh` grep for `normalize-issue-env` plus `--issue-exit-code` alongside the existing `issue-input-file` pins.
  - From dyn-issue-batch-output.txt: In step 4, explicitly require capturing the `/larch:issue` process exit code into `ISSUE_RC` immediately after filing (before `normalize-issue-env`), and make `normalize-issue-env` treat an empty/missing `--issue-exit-code` like a failed filing (`emit_issue_env_false "issue-exit-code-missing"`) with exit **0** so the prose fallback always applies.
  - From dyn-prompt-protocol-output.txt: Add an executable sub-bullet in step 4 mirroring design 5b: invoke `/larch:issue` via Skill, write stdout-only to `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout`, bind `ISSUE_RC` from the Skill tool exit (with `set +e`/`set -e` if shown as Bash), then call `normalize-issue-env`; or drop the separate exit-code requirement and have `normalize-issue-env` infer failure solely from filtered stdout like `file-design-oos.sh annotate`.

### FINDING_9: Step 4 structure test does not enforce dev-clone gate ordering
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structure pin checks token presence but not that `is-larch-dev-clone` precedes report composition and `/larch:issue` filing, so a future edit could auto-file from consumer or forked runs while the test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Compare token positions within stall_step4_window and require is-larch-dev-clone before bug-body/issue-input-file and before the /larch:issue --input-file command.

### FINDING_10: ISSUE_NUMBER accepts zero
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: Canonical issue number validation accepts `0`, which could be written to `stall-recovery-issue.env` and later used by `gh issue comment`, even though real `/larch:issue` output should never emit zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: Reject `issue_number` unless it matches `^[1-9][0-9]*$` (and the same for `duplicate_number` before fallback).

### FINDING_11: issue stdout normalization has no size bound
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: `--issue-stdout-file` is path-contained but not size-capped before `awk`/`kv_get`, so corrupted or verbose stdout can be loaded into memory during normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: Apply the same 64 KiB cap used for failure-detail logs (reject with `issues-stdout-oversize` and stale-env removal) before filtering.

### FINDING_12: [OUT_OF_SCOPE] unrelated run-log commit present
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: nit
- **Concern**: The branch includes a `larch-logs/implement/…` run-log commit unrelated to the stall-recovery fix surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: worth confirming it is intentional before merge.

### FINDING_13: [OUT_OF_SCOPE] dry-run stdout is not explicitly rejected
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: `normalize-issue-env` does not explicitly reject filtered `ISSUE_1_DRY_RUN=true`; current grammar fails closed, but future stdout drift could make this unsafe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: an explicit `ISSUE_1_DRY_RUN` guard would harden the protocol against future stdout drift.

### FINDING_14: [OUT_OF_SCOPE] sanitizer fixture does not isolate old prefix-glob behavior
- **Reviewer(s)**: dyn-issue-batch-output.txt
- **Severity**: nit
- **Concern**: The `8a<script>` unsafe-step fixture and added exact-only loop do not distinguish the new sanitizer regex from the old prefix `case` glob; production-token preservation remains the meaningful regression pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] pre-existing Step 18a classification gaps remain
- **Reviewer(s)**: dyn-issue-batch-output.txt
- **Severity**: latent
- **Concern**: Pre-existing Step 18a gaps around seeding in-memory `STALL_STEP`/`PHASE` before classification remain outside this diff and can affect classification/resume independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Address the concern above.

### FINDING_16: Step-reference ambiguity can misroute fallback handling
- **Reviewer(s)**: dyn-prompt-protocol-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery.md` refers to “Step 8” for fallback/comment behavior while `/implement` also has a prominent Step 8, so an orchestrator may confuse the stall-recovery procedure step with the ship phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-protocol-output.txt: Qualify every in-document step reference as “procedure step 8 (terminal-failure path)” or “step 8 below,” matching the disambiguation style used elsewhere in larch skills.

### FINDING_17: [OUT_OF_SCOPE] test-stall-recovery-report.md omits normalize-issue-env case docs
- **Reviewer(s)**: dyn-prompt-protocol-output.txt
- **Severity**: nit
- **Concern**: The sibling `.md` contract text does not enumerate the `normalize-issue-env` harness cases, a doc-sync gap rather than a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-protocol-output.txt: Address the concern above.
