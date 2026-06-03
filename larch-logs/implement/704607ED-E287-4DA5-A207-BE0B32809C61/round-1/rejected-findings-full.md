### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/test-lib-external-launcher-common.sh:458-499
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] assert_resolver_timeout only tests env-based resolution not SESSION_ENV_PATH or IMPLEMENT_TMPDIR session-env.sh A regression in the session-file loop could ship while env-only unit tests still pass Add session-file cases for default 30 positive override and explicit 0 opt-out
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-collect-agent-retry.sh:18
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-listed harness opt-out is not in commit b2a221942; it lives in an earlier branch commit. Cherry-pick of only the feature commit leaves test-collect-agent-retry.sh without TIMEOUT=0 and can break make test-harnesses-16. Squash or document dependency; include retry harness in the same logical change set as the resolver default.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/research/references/
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No E2E/offline test proves /research or standalone /review inherit default-on gate without session-env. Intended product behavior (extra probe latency or fast-fail when tools unhealthy) is unverified beyond resolver unit tests and docs. Optional harness: run-external-agent with stub check-reviewers, no session-env, no TIMEOUT=0, assert probe invoked.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: Resolved values are constrained by digit-only `case` arms before use; explicit `0` still clears the out-var and skips the gate.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Resolved values are constrained by digit-only `case` arms before use; explicit `0` still clears the out-var and skips the gate.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: The fallback literal is fixed `'30'`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - The fallback literal is fixed `'30'`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: `external_launch_health_gate()` passes `timeout_seconds` as a quoted argument to `timeout`/`gtimeout` and invokes `check-reviewers.sh` with fixed `--skip-*` flags only—no user-controlled command words.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `external_launch_health_gate()` passes `timeout_seconds` as a quoted argument to `timeout`/`gtimeout` and invokes `check-reviewers.sh` with fixed `--skip-*` flags only—no user-controlled command words. Session values continue to be read via `read-session-env-key.sh` (parse-only, not `source`), which was already the trust boundary for `SESSION_ENV_PATH` / `IMPLEMENT_TMPDIR/session-env.sh`. Default-on increases how often Codex/Cursor launches run the pre-launch health probe (including auth-related probe code inside `check-reviewers.sh`). That is a **reliability/availability** product change, not a new injection, deserialization, or secret-handling path. Opt-out remains `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` (documented). Harnesses that must avoid real probes export `0` at the top level—test-only, not production weakening. No hard-coded secrets, new network fetch surfaces, or auth-bypass logic were introduced in the diff. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: scripts/lib-external-launcher-common.sh:44-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Zero-padded numeric env (e.g. 000) opts out via early return and skips session files. Env 000 disables the gate while session-env writers would persist 30 for empty/non-digit only; mixed config confuses operators. Align zero detection with writers or document that only bare 0 opts out.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: scripts/lib-external-launcher-common.sh:100-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] /research and standalone /review inherit default-on without session-env writers. Parallel research/validation lanes each run check-reviewers before launch; auth stamps or rate limits can spike vs pre-change gate-off behavior. Document opt-out; monitor execution-issues; consider serializing probes if incidents appear.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: architecture: scripts/lib-external-launcher-common.sh:56-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] read-session-env-key failure is treated as empty candidate, then 30 fallback. Unreadable SESSION_ENV_PATH with intended opt-out in file never applied; gate turns on unexpectedly. Document fail-open; optionally warn or fail closed on read errors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: risk-integration: scripts/test-run-external-agent.sh:12
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness opt-out of health gate is conventional, not mechanically enforced. New test invokes run-external-agent with codex/cursor stub but no export=0; fails at health probe under default-on. Add lint/grep guard or require test-harnesses-* sweep in CI for resolver-only changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: correctness: scripts/lint-fix-loop.sh:138-220
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] affected_files_from_log keeps only existing repo files. Checks log reports failure in a file not yet on disk; empty In-scope list; external coder gets vague fix-only-log guidance. Extend path extraction or document limitation for create/delete failures.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: `b2a221942` — Make external-launch health gate default ON via resolver fallback
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `b2a221942` — Make external-launch health gate default ON via resolver fallback The precomputed diff vs `main` is much larger (release skill, bump/ship changes, run logs, etc.). Correctness review below targets **`b2a221942` and the OOS #3369 plan**, not the unrelated branch history. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

