### FINDING_1: code-quality: skills/design/SKILL.md:1080-1122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The twelve-key KV allowlist is copy-pasted across SKILL display/parse loops and test-step3-orchestrator-fence.sh without a shared definition or parity test. Adding a new emit_kv field in run-step3-review.sh can leave one parse arm unaware so display suppresses or drops state keys inconsistently. Introduce a shared key-list helper or a structure-test that diffs allowlist tokens between SKILL.md and the harness.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/run-step3-review.sh:69-129
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plugin-root resolution is duplicated on preview-only and no-preview entry paths. Future plugin-root bugfixes may be applied to only one branch leaving preview or review mis-resolving CLAUDE_PLUGIN_ROOT. Extract _step3_resolve_plugin_root and call it from both branches.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/run-step3-review.sh:107-111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Variable _has_header also covers the exact missing-plan warning path. Maintainers may add header-only checks under a misleading name and break sentinel touch rules. Rename to _touch_sentinel or use two explicit boolean flags.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/SKILL.md:1038-1078
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate rc=2 configuration-error banner in two Step 3 bash fences. Message wording can diverge between preview and review fences on a future edit. Document byte-identical requirement or centralize the banner prose once in Step 3.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-design-multi-round-integration.sh:498-500
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Integration test relies on implicit --no-preview default instead of explicit flag. A future default change could alter integration coverage without a compile-time signal. Pass --no-preview explicitly on the run-step3-review.sh invocation.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/design/SKILL.md:1089-1122
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Thin-fence file-first precedence treats any existing safe .step3-review-result.env as authoritative even when the current --no-preview run exits non-zero without updating that file (write failure after review completes). Fresh LOOP_STATUS/TALLY on captured stdout are not applied for keys already in the stale file. Intentional per plan but correctness regression vs old rc!=0 stdout override: Gate C re-run after converged env; new review fails with driver rc=1 and stdout LOOP_STATUS=panel-failed but env write fails; orchestrator loads stale converged and routes to passive-summary Gate B instead of panel-failed short-circuit. Scope safe-env authority to the current driver invocation: honor file only on driver exit 0, or stamp/clear result env before capture and require a same-run write, or fall back to stdout override on rc!=0 when write refused/failed.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: docs/linting.md:224
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No dedicated make test-run-step3-review linting row documents new preview/sentinel/argv coverage despite plan acceptance calling for harness prose updates. Maintainers may miss driver-owned sentinel and mutual-exclusion tests when reading docs only; CI still runs the target via Makefile. Add a make test-run-step3-review table row beside test-step3-review-cap describing preview mode sentinel argv mutual exclusion and default no-preview behavior.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-design-multi-round-integration.sh:498-500
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan optional --no-preview on direct driver integration call not applied; test relies on implicit default. A future change to default mode parsing could alter integration behavior without a failing test diff. Pass --no-preview explicitly on the run-step3-review.sh integration invocation.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/design/scripts/test-run-step3-review.sh:875-988
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Preview tests use RUN_STEP3_EMIT_PREVIEW_SH stubs only; no --preview-only case with real emit-design-plan-preview.sh. Renderer output string drift vs driver case patterns could break sentinel touch in production while stub tests pass. Add one integration case with real emit-design-plan-preview.sh under --preview-only for allowlisted tmpdir and missing plan.txt.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/SKILL.md:1032-1041
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Preview-only fence rc=2 abort path not covered by harnesses. Regression removing preview rc=2 handling might ship with green test-run-step3-review and orchestrator-fence suites. Add preview-only argv failure test and/or structure pin for preview fence configuration banner before exit 1.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Sentinel writes are allowlist-gated** — `.step3-entry-plan-printed` is no longer touched from `emit-design-plan-preview.sh` on missing/empty `plan.txt`. The driver only touches it after `larch_design_tmpdir_validate` and only when renderer output matches the header or the exact missing-plan warning (`run-step3-review.sh` ~86–114). That closes the prior path where a warning-only exit could still create a sentinel outside the intended contract.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Sentinel writes are allowlist-gated** — `.step3-entry-plan-printed` is no longer touched from `emit-design-plan-preview.sh` on missing/empty `plan.txt`. The driver only touches it after `larch_design_tmpdir_validate` and only when renderer output matches the header or the exact missing-plan warning (`run-step3-review.sh` ~86–114). That closes the prior path where a warning-only exit could still create a sentinel outside the intended contract.
- **Suggested revision**: Address the concern above.

### FINDING_12: **Symlink-safe result env** — Step 3 loads `.step3-review-result.env` only with `[[ -f … && ! -L … ]]`, and on `rc=2` the fence **`exit 1` before** any env load, display pass, or `LOOP_STATUS` normalization. That reduces symlink / stale-env routing bugs that could skip gates.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Symlink-safe result env** — Step 3 loads `.step3-review-result.env` only with `[[ -f … && ! -L … ]]`, and on `rc=2` the fence **`exit 1` before** any env load, display pass, or `LOOP_STATUS` normalization. That reduces symlink / stale-env routing bugs that could skip gates.
- **Suggested revision**: Address the concern above.

### FINDING_13: **KV state hardening** — Twelve-key allowlist plus file-first precedence when a safe env exists (stdout cannot override file `LOOP_STATUS`/`TALLY` on `rc!=0`). That limits **state confusion** from spoofed stdout, which is adjacent to security when branch matrix skips Gate B / assessor paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **KV state hardening** — Twelve-key allowlist plus file-first precedence when a safe env exists (stdout cannot override file `LOOP_STATUS`/`TALLY` on `rc!=0`). That limits **state confusion** from spoofed stdout, which is adjacent to security when branch matrix skips Gate B / assessor paths.
- **Suggested revision**: Address the concern above.

### FINDING_14: **Docs aligned with behavior** — `SECURITY.md` now records that `step3` preview is a pure renderer and the driver owns the sentinel under allowlist rules.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Docs aligned with behavior** — `SECURITY.md` now records that `step3` preview is a pure renderer and the driver owns the sentinel under allowlist rules.
- **Suggested revision**: Address the concern above.

### FINDING_15: **REPO on all Step 3 pause-save guards** — Consistent `${REPO:+--repo "$REPO"}` threading reduces cross-repo pause/resume mistakes (integrity/consistency, not a new attack surface).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **REPO on all Step 3 pause-save guards** — Consistent `${REPO:+--repo "$REPO"}` threading reduces cross-repo pause/resume mistakes (integrity/consistency, not a new attack surface). ### Surfaces reviewed (no new exploitable paths found) | Area | Verdict | |------|--------| | **Command injection** | `_preview_sh` and renderer invoked quoted; argv parsed with `case`. No new metacharacter interpolation. | | **`RUN_STEP3_EMIT_PREVIEW_SH`** | Test seam (same family as `RUN_STEP3_PLAN_REVIEW_LOOP_SH`). Arbitrary script only if caller exports env — trusted operator/harness model; not set by `SKILL.md` fences. | | **`--design-tmpdir` allowlist** | Preview still runs renderer on raw path for warnings; **sentinel read/write/touch** requires `larch_design_tmpdir_validate` + canonical `pwd -P`. Disallowed tmpdir + stale sentinel still re-renders warnings (harnessed). | | **Path traversal** | No change to allowlist rules in `lib-design-tmpdir.sh`. `plan.txt` read remains under validated tmpdir (pre-existing symlink-follow behavior unchanged). | | **Prompt injection** | `plan.txt` / issue-body content shown in preview is still **untrusted data** (issue-anchored trust boundary). Not introduced by this refactor; preview path is equivalent to the removed direct `emit-design-plan-preview.sh` fence. | | **Display pass (verbatim non-KV stdout)** | Increases chat-visible driver breadcrumbs; content is **trusted plugin/driver output**, not parsed into state unless allowlisted. No path found where reviewer/plan prose is newly echoed through this channel. | | **Secrets** | No new logging, env dumps, or credential handling. | ### Out of scope (unchanged, not introduced here)
- **Suggested revision**: Address the concern above.

### FINDING_16: Untrusted `larch:plan` / `plan.txt` reaching the operator and external reviewers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Untrusted `larch:plan` / `plan.txt` reaching the operator and external reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_17: External reviewer read-only vs implementer write delegation (`SECURITY.md` § External tool delegation).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - External reviewer read-only vs implementer write delegation (`SECURITY.md` § External tool delegation).
- **Suggested revision**: Address the concern above.

### FINDING_18: `gatec` preview variant (explicitly untouched).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `gatec` preview variant (explicitly untouched).
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] architecture: skills/design/SKILL.md:1027-1041
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel suppresses preview on every Step 3 re-entry without checking whether plan.txt was repaired after an earlier missing-plan warning. Operator fixes plan.txt then triggers Gate C re-run; preview fence exits quietly; review runs with no refreshed ## Plan Candidate for Review and no repeated warning. Consider future enhancement: tie re-entry suppression to plan.txt presence/mtime, or clear sentinel when plan.txt becomes non-empty.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:1029-1074
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Uncaptured preview and captured review read plan.txt at different times if the tree mutates between fences. Operator sees preview from revision N while plan-review-loop reviews revision N+1; confusing triage of review findings vs chat preview. Document for operators; optional follow-up to invalidate sentinel or re-preview on plan.txt change.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] correctness: skills/design/scripts/run-step3-review.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preview-mode canonicalization uses bare cd under set -e. Rare cd failure after validate passes aborts the whole Step 3 preview Bash block instead of degrading with a warning. Wrap cd in set +e; on failure skip sentinel touch and still run renderer on raw --design-tmpdir.
- **Suggested revision**: Address the concern above.

### FINDING_22: `e9a468593` — Move Step 3 preview ownership into `run-step3-review.sh --preview-only`
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `e9a468593` — Move Step 3 preview ownership into `run-step3-review.sh --preview-only`
- **Suggested revision**: Address the concern above.

### FINDING_23: `591715344` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `591715344` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_24: `a3f9ae3f7` — Apply relevant-checks fixes (Step 5)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `a3f9ae3f7` — Apply relevant-checks fixes (Step 5) **Scope:** 12 files in the precomputed diff (drivers, `SKILL.md`, harnesses, docs, `SECURITY.md`). Matches the plan’s file list except `scripts/test-design-multi-round-integration.sh`, which the plan marked **optional**. ---
- **Suggested revision**: Address the concern above.

### FINDING_25: **architecture** `docs/topology.md:24` and `skills/shared/topology.tsv:14` — Topology still lists `emit-design-plan-preview.sh` as the sole runtime authority for Step 3 plan-candidate preview, while the plan’s operator contract is `run-step3-review.sh --preview-only` (renderer remains `emit-design-plan-preview.sh` under the driver). **Suggested fix:** If step 6’s drift sweep is meant to include generated topology, extend the row (or add a companion row) so projection matches the new entrypoint; otherwise document in the issue/PR that topology update is intentionally deferred.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **architecture** `docs/topology.md:24` and `skills/shared/topology.tsv:14` — Topology still lists `emit-design-plan-preview.sh` as the sole runtime authority for Step 3 plan-candidate preview, while the plan’s operator contract is `run-step3-review.sh --preview-only` (renderer remains `emit-design-plan-preview.sh` under the driver). **Suggested fix:** If step 6’s drift sweep is meant to include generated topology, extend the row (or add a companion row) so projection matches the new entrypoint; otherwise document in the issue/PR that topology update is intentionally deferred. --- ### Traceability summary (plan → diff) | Plan requirement | Status | |------------------|--------| | `--preview-only` / `--no-preview`, mutual exclusion (exit 2), default `--no-preview` | Done in `run-step3-review.sh` + tests | | Preview before `--round-cap` / `cd` | Preview branch returns before review validation | | Sentinel owned by driver; allowlist-gated touch; exact header or exact missing-plan warning | Done; broad harness coverage in `test-run-step3-review.sh` | | `step3` pure renderer; `gatec` unchanged | Done in `emit-design-plan-preview.sh` | | `SKILL.md`: live preview fence, captured `--no-preview`, REPO on all pause-save lines | Done | | Thin fence: rc=2 → banner + `exit 1` before load/parse; display pass; `-f && ! -L`; file-first precedence; qualified rc≠0 override | Done; mirrored in `test-step3-orchestrator-fence.sh` | | `assert_thin_fence` on Step 3; obsolete fat pins removed | Done in `test-design-structure.sh` | | Docs: `configuration-and-permissions.md`, `issue-anchored-plan.md`, `linting.md`, `SECURITY.md` | Done | | `test-emit-design-plan-preview.sh`, `test-run-step3-review.sh`, `test-step3-orchestrator-fence.sh` | Done | | Optional `test-design-multi-round-integration.sh --no-preview` | Not added; **OK** — omitted flags default to `--no-preview` (`scripts/test-design-multi-round-integration.sh:498-500`) | | Original “remove one preview turn per Step 3 entry” | **Explicitly deferred** in plan; implementation matches deferred acceptance | ---
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **Pre-existing quiet/capture contract** — The display pass replays non-KV lines from `_plan_review_out` only. Cap-reached prose must still land in the captured stream (FD 3 / quiet dup behavior). That predates this phase; not introduced by this diff.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Pre-existing quiet/capture contract** — The display pass replays non-KV lines from `_plan_review_out` only. Cap-reached prose must still land in the captured stream (FD 3 / quiet dup behavior). That predates this phase; not introduced by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **`make test-run-step3-review` linting row** — Plan asked for harness prose updates; `docs/linting.md` folds new coverage into the `test-emit-design-plan-preview` row rather than expanding a dedicated `test-run-step3-review` table entry. Makefile already registers `test-run-step3-review` in `test-harnesses-8`; behavior is documented, just not in a separate linting table row.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **`make test-run-step3-review` linting row** — Plan asked for harness prose updates; `docs/linting.md` folds new coverage into the `test-emit-design-plan-preview` row rather than expanding a dedicated `test-run-step3-review` table entry. Makefile already registers `test-run-step3-review` in `test-harnesses-8`; behavior is documented, just not in a separate linting table row. --- **Verdict:** Implementation is **complete and correct against the supplied implementation plan**. The only material follow-up is optional topology/doc projection alignment if you want consumer docs to name the driver entrypoint, not only the renderer script.
- **Suggested revision**: Address the concern above.

