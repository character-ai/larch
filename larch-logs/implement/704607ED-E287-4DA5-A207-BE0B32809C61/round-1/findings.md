### FINDING_1: code-quality: scripts/test-lib-external-launcher-common.sh:458-499
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] assert_resolver_timeout only tests env-based resolution not SESSION_ENV_PATH or IMPLEMENT_TMPDIR session-env.sh A regression in the session-file loop could ship while env-only unit tests still pass Add session-file cases for default 30 positive override and explicit 0 opt-out
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/lib-external-launcher-common.md:7
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] "optional" contradicts default-on gate wording Readers infer gate is off unless configured Rename to "pre-launch health gate" or "enabled by default; opt out with 0"
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/run-external-agent.md:120-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test harness section omits LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 guidance for offline stubs New harnesses may hit real check-reviewers.sh and flake under default-on Document export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 unless testing the gate
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/lib-external-launcher-common.sh:76-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Three copies of literal 30 across resolver and writers Drift if one site changes without the others Plan-accepted; comment + resolver test mitigate
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/test-collect-agent-retry.sh:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Opt-out export landed in a87f4c059 not b2a221942 Cherry-pick of feature commit alone may miss harness-16 isolation Ensure retry harness export rides with resolver PR
- **Suggested revision**: Address the concern above.

### FINDING_6: `b2a221942` — Make external-launch health gate default ON via resolver fallback
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `b2a221942` — Make external-launch health gate default ON via resolver fallback The precomputed diff vs `main` is much larger (release skill, bump/ship changes, run logs, etc.). Correctness review below targets **`b2a221942` and the OOS #3369 plan**, not the unrelated branch history. ---
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/lib-external-launcher-common.sh:53-74` — If `SESSION_ENV_PATH` resolves to `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0`, the session loop returns immediately and never reads `$IMPLEMENT_TMPDIR/session-env.sh`, even if the latter has a positive value. That matches documented “explicit `0` opts out” semantics but can surprise operators who set `0` in a design env file and `30` in implement session-env. **Suggested fix:** No code change required; optional doc note that the first readable session file in order wins for opt-out, not “most specific” implement env.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **risk-integration** (branch scope) — Merging `HEAD` vs `main` carries substantial non–#3369 changes (release skill, ship/finalize, Cursor retry, lint-fix-loop, version bumps, run logs). If the PR is meant to be only the health-gate fix, reviewers should target **`b2a221942`** (16 files) rather than the full branch diff.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** (operational, intentional) — Standalone `/research` and `/review` will run up to one `check-reviewers.sh` probe per Codex/Cursor `run-external-agent.sh` launch (≤30s each, fail-open on unparseable output). That closes #3369 but adds latency and can fast-fail unhealthy tools before stubs run in production (not in harnesses that export `0`). **Suggested fix:** Documented in `docs/configuration-and-permissions.md`; operators can set `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` to opt out. --- **Summary:** The behavioral change is small, internally consistent, and well covered by unit/harness updates. I did not run the test matrix in Ask mode; the plan’s harness list is the right pre-merge checklist, especially `make test-harnesses-1` (not always pulled in by `relevant-checks.sh` on lib-only edits).
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/relevant-checks.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] relevant-checks does not map lib-external-launcher-common.sh or run-external-agent.sh changes to their harness targets. After a resolver-only edit, running only relevant-checks can pass while test-lib-external-launcher-common.sh and test-run-external-agent.sh fail on make test-harnesses-8/6. Add relevant-checks cases for lib-external-launcher-common.sh, run-external-agent.sh, and paired test-* harnesses, or require full make lint in PR checklist for this surface.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-lib-external-launcher-common.sh:497-499
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test pins non-numeric/empty env coercing to resolver default 30. Documented edge case (garbage env) can regress without failing harnesses that only test unset env, explicit 0, and positive override. Add assert_resolver_timeout cases for env abc and/or empty string expecting 30.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-collect-agent-retry.sh:18
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-listed harness opt-out is not in commit b2a221942; it lives in an earlier branch commit. Cherry-pick of only the feature commit leaves test-collect-agent-retry.sh without TIMEOUT=0 and can break make test-harnesses-16. Squash or document dependency; include retry harness in the same logical change set as the resolver default.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/research/references/
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No E2E/offline test proves /research or standalone /review inherit default-on gate without session-env. Intended product behavior (extra probe latency or fast-fail when tools unhealthy) is unverified beyond resolver unit tests and docs. Optional harness: run-external-agent with stub check-reviewers, no session-env, no TIMEOUT=0, assert probe invoked.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Full branch diff mixes unrelated commits with the health-gate fix. CI or reviewers may attribute failures to the wrong change set. Scope review and bisect to b2a221942 for #3369.
- **Suggested revision**: Address the concern above.

### FINDING_15: Resolved values are constrained by digit-only `case` arms before use; explicit `0` still clears the out-var and skips the gate.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Resolved values are constrained by digit-only `case` arms before use; explicit `0` still clears the out-var and skips the gate.
- **Suggested revision**: Address the concern above.

### FINDING_16: The fallback literal is fixed `'30'`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - The fallback literal is fixed `'30'`.
- **Suggested revision**: Address the concern above.

### FINDING_17: `external_launch_health_gate()` passes `timeout_seconds` as a quoted argument to `timeout`/`gtimeout` and invokes `check-reviewers.sh` with fixed `--skip-*` flags only—no user-controlled command words.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `external_launch_health_gate()` passes `timeout_seconds` as a quoted argument to `timeout`/`gtimeout` and invokes `check-reviewers.sh` with fixed `--skip-*` flags only—no user-controlled command words. Session values continue to be read via `read-session-env-key.sh` (parse-only, not `source`), which was already the trust boundary for `SESSION_ENV_PATH` / `IMPLEMENT_TMPDIR/session-env.sh`. Default-on increases how often Codex/Cursor launches run the pre-launch health probe (including auth-related probe code inside `check-reviewers.sh`). That is a **reliability/availability** product change, not a new injection, deserialization, or secret-handling path. Opt-out remains `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` (documented). Harnesses that must avoid real probes export `0` at the top level—test-only, not production weakening. No hard-coded secrets, new network fetch surfaces, or auth-bypass logic were introduced in the diff. ---
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] **`.gitleaks.toml` (branch, not in `b2a221942`)** — Adds `scripts/test-launch-review.sh` to the gitleaks allowlist. That narrows secret scanning for that file; acceptable if the harness contains intentional token-shaped fixtures, but worth confirming the allowlist matches actual fixture content and not live credentials.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **`.gitleaks.toml` (branch, not in `b2a221942`)** — Adds `scripts/test-launch-review.sh` to the gitleaks allowlist. That narrows secret scanning for that file; acceptable if the harness contains intentional token-shaped fixtures, but worth confirming the allowlist matches actual fixture content and not live credentials.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] **`SECURITY.md` design-log-publish paragraph (branch, not in `b2a221942`)** — Documents CI-gated admin merge behavior; documentation-only relative to this feature.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`SECURITY.md` design-log-publish paragraph (branch, not in `b2a221942`)** — Documents CI-gated admin merge behavior; documentation-only relative to this feature.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] **Pre-existing fail-open in `external_launch_health_gate()`** — Unparseable probe output still returns success and allows launch (`lib-external-launcher-common.sh` ~130–133). Not introduced or amplified by the resolver fallback beyond running the same probe more often by default.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Pre-existing fail-open in `external_launch_health_gate()`** — Unparseable probe output still returns success and allows launch (`lib-external-launcher-common.sh` ~130–133). Not introduced or amplified by the resolver fallback beyond running the same probe more often by default. --- **Verdict:** The #3369 change set does not introduce security vulnerabilities under the injection / secrets / auth / trust-boundary lens. Operators in air-gapped or no-external-CLI environments should set `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` if they need to avoid auth probes—that is operational configuration, not a defect in this diff.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: scripts/lib-external-launcher-common.sh:40-78
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-numeric env values now fall through to the 30s default instead of disabling the gate. Operator sets LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=30s or leaves a typo; gate runs and may fast-fail launches that previously skipped the probe. Document typo→on behavior; add resolver test pinning garbage env → 30.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/lib-external-launcher-common.sh:44-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Zero-padded numeric env (e.g. 000) opts out via early return and skips session files. Env 000 disables the gate while session-env writers would persist 30 for empty/non-digit only; mixed config confuses operators. Align zero detection with writers or document that only bare 0 opts out.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/lib-external-launcher-common.sh:100-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] /research and standalone /review inherit default-on without session-env writers. Parallel research/validation lanes each run check-reviewers before launch; auth stamps or rate limits can spike vs pre-change gate-off behavior. Document opt-out; monitor execution-issues; consider serializing probes if incidents appear.
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/lib-external-launcher-common.sh:56-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] read-session-env-key failure is treated as empty candidate, then 30 fallback. Unreadable SESSION_ENV_PATH with intended opt-out in file never applied; gate turns on unexpectedly. Document fail-open; optionally warn or fail closed on read errors.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-run-external-agent.sh:12
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness opt-out of health gate is conventional, not mechanically enforced. New test invokes run-external-agent with codex/cursor stub but no export=0; fails at health probe under default-on. Add lint/grep guard or require test-harnesses-* sweep in CI for resolver-only changes.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/lint-fix-loop.sh:138-220
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] affected_files_from_log keeps only existing repo files. Checks log reports failure in a file not yet on disk; empty In-scope list; external coder gets vague fix-only-log guidance. Extend path extraction or document limitation for create/delete failures.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture: scripts/lib-external-launcher-common.sh:110-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No outer timeout binary leaves probe duration to check-reviewers internal timeout. Hung probe on machine without timeout/gtimeout blocks launch longer than 30s intent. Pre-existing; optional follow-up to bound unwrapped probe.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/lib-external-launcher-common.sh:130-133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unparseable probe output fail-opens to launch. Probe stderr noise or partial KV → child still runs despite unhealthy tool. Pre-existing; default-on increases exposure frequency only.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **Branch breadth** — Full `HEAD` vs `main` includes large unrelated changes (release skill, version bumps, run logs, etc.). Plan fidelity for #3369 should be judged on `b2a221942` (and harness prep already on the branch), not the entire megadiff.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Branch breadth** — Full `HEAD` vs `main` includes large unrelated changes (release skill, version bumps, run logs, etc.). Plan fidelity for #3369 should be judged on `b2a221942` (and harness prep already on the branch), not the entire megadiff.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **Test execution** — Plan calls for many `make test-harnesses-*` targets; this review did not run them (read-only / ask mode). Implementation matches the plan’s harness edits; pass/fail is not verified here.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Test execution** — Plan calls for many `make test-harnesses-*` targets; this review did not run them (read-only / ask mode). Implementation matches the plan’s harness edits; pass/fail is not verified here.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Resolver unit tests** — `assert_resolver_timeout` covers env-only default/`0`/positive paths. Session-file `0` opt-out is already covered by `health gate zero opt-out beats session fallback` in the same harness; not a plan gap, only slightly narrower than the plan’s “any source” wording in the new helper alone.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Resolver unit tests** — `assert_resolver_timeout` covers env-only default/`0`/positive paths. Session-file `0` opt-out is already covered by `health gate zero opt-out beats session fallback` in the same harness; not a plan gap, only slightly narrower than the plan’s “any source” wording in the new helper alone.
- **Suggested revision**: Address the concern above.

