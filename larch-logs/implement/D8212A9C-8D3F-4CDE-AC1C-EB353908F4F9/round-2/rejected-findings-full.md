### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/SKILL.md:1080-1122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The twelve-key KV allowlist is copy-pasted across SKILL display/parse loops and test-step3-orchestrator-fence.sh without a shared definition or parity test. Adding a new emit_kv field in run-step3-review.sh can leave one parse arm unaware so display suppresses or drops state keys inconsistently. Introduce a shared key-list helper or a structure-test that diffs allowlist tokens between SKILL.md and the harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: skills/design/SKILL.md:1032-1041
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Preview-only fence rc=2 abort path not covered by harnesses. Regression removing preview rc=2 handling might ship with green test-run-step3-review and orchestrator-fence suites. Add preview-only argv failure test and/or structure pin for preview fence configuration banner before exit 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Sentinel writes are allowlist-gated** — `.step3-entry-plan-printed` is no longer touched from `emit-design-plan-preview.sh` on missing/empty `plan.txt`. The driver only touches it after `larch_design_tmpdir_validate` and only when renderer output matches the header or the exact missing-plan warning (`run-step3-review.sh` ~86–114). That closes the prior path where a warning-only exit could still create a sentinel outside the intended contract.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Sentinel writes are allowlist-gated** — `.step3-entry-plan-printed` is no longer touched from `emit-design-plan-preview.sh` on missing/empty `plan.txt`. The driver only touches it after `larch_design_tmpdir_validate` and only when renderer output matches the header or the exact missing-plan warning (`run-step3-review.sh` ~86–114). That closes the prior path where a warning-only exit could still create a sentinel outside the intended contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **Symlink-safe result env** — Step 3 loads `.step3-review-result.env` only with `[[ -f … && ! -L … ]]`, and on `rc=2` the fence **`exit 1` before** any env load, display pass, or `LOOP_STATUS` normalization. That reduces symlink / stale-env routing bugs that could skip gates.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Symlink-safe result env** — Step 3 loads `.step3-review-result.env` only with `[[ -f … && ! -L … ]]`, and on `rc=2` the fence **`exit 1` before** any env load, display pass, or `LOOP_STATUS` normalization. That reduces symlink / stale-env routing bugs that could skip gates.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **KV state hardening** — Twelve-key allowlist plus file-first precedence when a safe env exists (stdout cannot override file `LOOP_STATUS`/`TALLY` on `rc!=0`). That limits **state confusion** from spoofed stdout, which is adjacent to security when branch matrix skips Gate B / assessor paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **KV state hardening** — Twelve-key allowlist plus file-first precedence when a safe env exists (stdout cannot override file `LOOP_STATUS`/`TALLY` on `rc!=0`). That limits **state confusion** from spoofed stdout, which is adjacent to security when branch matrix skips Gate B / assessor paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **Docs aligned with behavior** — `SECURITY.md` now records that `step3` preview is a pure renderer and the driver owns the sentinel under allowlist rules.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Docs aligned with behavior** — `SECURITY.md` now records that `step3` preview is a pure renderer and the driver owns the sentinel under allowlist rules.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **REPO on all Step 3 pause-save guards** — Consistent `${REPO:+--repo "$REPO"}` threading reduces cross-repo pause/resume mistakes (integrity/consistency, not a new attack surface).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **REPO on all Step 3 pause-save guards** — Consistent `${REPO:+--repo "$REPO"}` threading reduces cross-repo pause/resume mistakes (integrity/consistency, not a new attack surface). ### Surfaces reviewed (no new exploitable paths found) | Area | Verdict | |------|--------| | **Command injection** | `_preview_sh` and renderer invoked quoted; argv parsed with `case`. No new metacharacter interpolation. | | **`RUN_STEP3_EMIT_PREVIEW_SH`** | Test seam (same family as `RUN_STEP3_PLAN_REVIEW_LOOP_SH`). Arbitrary script only if caller exports env — trusted operator/harness model; not set by `SKILL.md` fences. | | **`--design-tmpdir` allowlist** | Preview still runs renderer on raw path for warnings; **sentinel read/write/touch** requires `larch_design_tmpdir_validate` + canonical `pwd -P`. Disallowed tmpdir + stale sentinel still re-renders warnings (harnessed). | | **Path traversal** | No change to allowlist rules in `lib-design-tmpdir.sh`. `plan.txt` read remains under validated tmpdir (pre-existing symlink-follow behavior unchanged). | | **Prompt injection** | `plan.txt` / issue-body content shown in preview is still **untrusted data** (issue-anchored trust boundary). Not introduced by this refactor; preview path is equivalent to the removed direct `emit-design-plan-preview.sh` fence. | | **Display pass (verbatim non-KV stdout)** | Increases chat-visible driver breadcrumbs; content is **trusted plugin/driver output**, not parsed into state unless allowlisted. No path found where reviewer/plan prose is newly echoed through this channel. | | **Secrets** | No new logging, env dumps, or credential handling. | ### Out of scope (unchanged, not introduced here)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Untrusted `larch:plan` / `plan.txt` reaching the operator and external reviewers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Untrusted `larch:plan` / `plan.txt` reaching the operator and external reviewers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: External reviewer read-only vs implementer write delegation (`SECURITY.md` § External tool delegation).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - External reviewer read-only vs implementer write delegation (`SECURITY.md` § External tool delegation).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: `gatec` preview variant (explicitly untouched).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `gatec` preview variant (explicitly untouched).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/run-step3-review.sh:69-129
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plugin-root resolution is duplicated on preview-only and no-preview entry paths. Future plugin-root bugfixes may be applied to only one branch leaving preview or review mis-resolving CLAUDE_PLUGIN_ROOT. Extract _step3_resolve_plugin_root and call it from both branches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `e9a468593` — Move Step 3 preview ownership into `run-step3-review.sh --preview-only`
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `e9a468593` — Move Step 3 preview ownership into `run-step3-review.sh --preview-only`
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `591715344` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `591715344` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: `a3f9ae3f7` — Apply relevant-checks fixes (Step 5)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `a3f9ae3f7` — Apply relevant-checks fixes (Step 5) **Scope:** 12 files in the precomputed diff (drivers, `SKILL.md`, harnesses, docs, `SECURITY.md`). Matches the plan’s file list except `scripts/test-design-multi-round-integration.sh`, which the plan marked **optional**. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/run-step3-review.sh:107-111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Variable _has_header also covers the exact missing-plan warning path. Maintainers may add header-only checks under a misleading name and break sentinel touch rules. Rename to _touch_sentinel or use two explicit boolean flags.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/SKILL.md:1038-1078
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate rc=2 configuration-error banner in two Step 3 bash fences. Message wording can diverge between preview and review fences on a future edit. Document byte-identical requirement or centralize the banner prose once in Step 3.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/test-design-multi-round-integration.sh:498-500
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Integration test relies on implicit --no-preview default instead of explicit flag. A future default change could alter integration coverage without a compile-time signal. Pass --no-preview explicitly on the run-step3-review.sh invocation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: correctness: skills/design/SKILL.md:1089-1122
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Thin-fence file-first precedence treats any existing safe .step3-review-result.env as authoritative even when the current --no-preview run exits non-zero without updating that file (write failure after review completes). Fresh LOOP_STATUS/TALLY on captured stdout are not applied for keys already in the stale file. Intentional per plan but correctness regression vs old rc!=0 stdout override: Gate C re-run after converged env; new review fails with driver rc=1 and stdout LOOP_STATUS=panel-failed but env write fails; orchestrator loads stale converged and routes to passive-summary Gate B instead of panel-failed short-circuit. Scope safe-env authority to the current driver invocation: honor file only on driver exit 0, or stamp/clear result env before capture and require a same-run write, or fall back to stdout override on rc!=0 when write refused/failed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: risk-integration: docs/linting.md:224
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No dedicated make test-run-step3-review linting row documents new preview/sentinel/argv coverage despite plan acceptance calling for harness prose updates. Maintainers may miss driver-owned sentinel and mutual-exclusion tests when reading docs only; CI still runs the target via Makefile. Add a make test-run-step3-review table row beside test-step3-review-cap describing preview mode sentinel argv mutual exclusion and default no-preview behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: risk-integration: scripts/test-design-multi-round-integration.sh:498-500
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan optional --no-preview on direct driver integration call not applied; test relies on implicit default. A future change to default mode parsing could alter integration behavior without a failing test diff. Pass --no-preview explicitly on the run-step3-review.sh integration invocation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: skills/design/scripts/test-run-step3-review.sh:875-988
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Preview tests use RUN_STEP3_EMIT_PREVIEW_SH stubs only; no --preview-only case with real emit-design-plan-preview.sh. Renderer output string drift vs driver case patterns could break sentinel touch in production while stub tests pass. Add one integration case with real emit-design-plan-preview.sh under --preview-only for allowlisted tmpdir and missing plan.txt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

