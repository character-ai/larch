### FINDING_1: code-quality: skills/design/scripts/test-run-step3-review.sh:370-397
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Integration-seam stub duplicates plan-review-loop argv whitelist manually. plan-review-loop.sh adds a new flag and run-step3-review.sh forwards it, but the seam stub is not updated: the test still passes while production Step 3 fails with unknown option. Add a structure-test pin on the driver invocation flag set, or document/sync the stub whitelist with plan-review-loop.sh's case parser.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/cleanup/scripts/cleanup.sh:55-128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated mktemp/find/read fail-safe scaffolding across cache and /tmp passes. A fix applied to only one pass (e.g. temp-file cleanup on error) could leave asymmetric behavior between cache and /tmp. Add a brief cross-reference comment between passes, or extract a minimal shared enumerator if more edits are expected.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-design-structure.sh:156-158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Structure harness lacks absent pin for SKILL.md convergence forwarding. Someone re-adds --convergence-threshold to SKILL.md Step 3; structure tests stay green until a live /design run hits argv errors. Add absent "$SKILL_MD" '--convergence-threshold' (or the full expansion line) alongside the existing run-step3 absent pin.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/scripts/test-run-step3-review.sh:1056-1096
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Integration-seam stub checks reject-unknown only, not full forward parity A future required plan-review-loop flag omitted from run-step3-review.sh leaves this test green while real Step 3 breaks Record argv and assert expected forwards, or structure-pin required flags
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/cleanup/scripts/test-cleanup.md:7-29
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness doc omits three new enumeration/mktemp failure cases Contributors may miss regression coverage when editing cleanup fail-safes List enumeration-failure-warns, enumeration-failure-warns-tmp, and mktemp-allocation-failure-warns in Covered cases
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: skills/cleanup/scripts/cleanup.sh:137
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Symlink reaper still swallows enumeration find failure Pre-existing silent skip with SYMLINKS_REMOVED=0 and no warning Out of scope for this PR; align with cache/tmp fail-safe if desired later
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/design/scripts/test-run-step3-review.sh:362-396
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test runs run-step3-review.sh against real plan-review-loop.sh on valid argv; only invalid --round-cap 0 uses the real loop. #3274-class regression (driver forwards flag loop rejects) could return if seam stub and production loop diverge; CI stays green until a live /design Step 3 run. Add a minimal happy-path case with default RUN_STEP3_PLAN_REVIEW_LOOP_SH and stubbed panel deps; assert non-panel-failed LOOP_STATUS and no unknown option on stderr.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-design-structure.sh:156-165
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Removed SKILL.md contains pin for --convergence-threshold without an absent guard. Re-adding --convergence-threshold to SKILL Step 3 would not fail test-design-structure.sh; only run-step3-review.sh forwarding is absent-pinned. Add absent "$SKILL_MD" '--convergence-threshold' and/or absent "$SKILL_MD" 'LARCH_DESIGN_CONVERGENCE_THRESHOLD'.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/cleanup/scripts/test-cleanup.sh:233-251
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] mktemp-allocation-failure-warns asserts one generic allocation warning, not both pass-specific messages. A regression that warns/skips only the cache or only the /tmp pass could still pass if any allocation warning appears once. Assert both failed to allocate temp list for cache cleanup and for /tmp cleanup substrings when both passes run.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration: scripts/test-design-multi-round-integration.sh:113-118
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Driver integration stub still accepts any argv; would not catch convergence forward regression. Forwarding drift at driver boundary is only partially covered elsewhere; this harness predates the seam test. Pre-existing; optional follow-up to align stub with reject-unknown contract or argv capture.
- **Suggested revision**: Address the concern above.

### FINDING_11: `4e97d59cd` — Warn on cleanup enumeration failure; remove dead convergence threshold  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `4e97d59cd` — Warn on cleanup enumeration failure; remove dead convergence threshold
- **Suggested revision**: Address the concern above.

### FINDING_12: `25d20f33e` / `717fb8202` — larch-logs chores (out of scope for code review)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `25d20f33e` / `717fb8202` — larch-logs chores (out of scope for code review) **Summary:** Two workstreams — (A) `cleanup.sh` enumeration fail-safe via guarded `mktemp` + observable `find` exit, with docs/tests/`SECURITY.md` sync; (B) end-to-end removal of dead `--convergence-threshold` / `LARCH_DESIGN_CONVERGENCE_THRESHOLD` plumbing and a new driver↔loop argv integration test. From a security/trust-boundary lens, the diff is low risk and net-positive for operational security on cleanup. ---
- **Suggested revision**: Address the concern above.

### FINDING_13: **Workstream A (`cleanup.sh`)** — Changes are confined to failure paths. Top-level enumeration still uses `find` with `! -type l` (no delete-through-symlink). Deletion still goes through `should_remove_by_age` and the existing nested-scan fail-safe. On enumeration/`mktemp` failure the script warns and skips the pass (count 0) instead of silently pretending success — that improves **operator awareness** when session tmpdirs holding secrets (`.meta` `CMD_JSON`, prompts, etc., per `SECURITY.md`) were not pruned. `mktemp` uses the standard exclusive template; list files are removed on all paths. `2>/dev/null` on `find` does not hide non-zero exit status used by the `if find` branch. No new injection surfaces: `TMP_PATTERNS` and `CACHE_DIR` remain fixed/homedir-derived; `RETENTION_DAYS` is numeric-validated.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Workstream A (`cleanup.sh`)** — Changes are confined to failure paths. Top-level enumeration still uses `find` with `! -type l` (no delete-through-symlink). Deletion still goes through `should_remove_by_age` and the existing nested-scan fail-safe. On enumeration/`mktemp` failure the script warns and skips the pass (count 0) instead of silently pretending success — that improves **operator awareness** when session tmpdirs holding secrets (`.meta` `CMD_JSON`, prompts, etc., per `SECURITY.md`) were not pruned. `mktemp` uses the standard exclusive template; list files are removed on all paths. `2>/dev/null` on `find` does not hide non-zero exit status used by the `if find` branch. No new injection surfaces: `TMP_PATTERNS` and `CACHE_DIR` remain fixed/homedir-derived; `RETENTION_DAYS` is numeric-validated.
- **Suggested revision**: Address the concern above.

### FINDING_14: **Workstream B (design)** — Mechanical removal of dead argv forwarding and documentation. `run-step3-review.sh` still invokes `plan-review-loop.sh` with a fixed flag set; the new integration-seam test reduces future argv drift (including accidental forwarding of rejected flags). No authn/authz, secret handling, or deserialization changes.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Workstream B (design)** — Mechanical removal of dead argv forwarding and documentation. `run-step3-review.sh` still invokes `plan-review-loop.sh` with a fixed flag set; the new integration-seam test reduces future argv drift (including accidental forwarding of rejected flags). No authn/authz, secret handling, or deserialization changes.
- **Suggested revision**: Address the concern above.

### FINDING_15: **Tests** — `write_stub_enum_failure` and `mktemp-allocation-failure-warns` are harness-only; they do not ship on the `/cleanup` or `/design` runtime paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests** — `write_stub_enum_failure` and `mktemp-allocation-failure-warns` are harness-only; they do not ship on the `/cleanup` or `/design` runtime paths. ---
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/cleanup/scripts/cleanup.sh:137-142` — The dangling `current-design-env-*.sh` symlink reaper still uses process substitution with `|| true`, so a failed top-level `find` there remains silent (fail-open), unlike the new enumeration fail-safes. **Why OOS:** that path is unchanged by this branch; the PR only fixes enumeration on the cache and `/tmp` passes.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/cleanup/scripts/cleanup.sh:77` — `LARCH_TEST_TMP_ROOT` can redirect the scanned `/tmp` root without the `lib-design-tmpdir.sh` allowlist used elsewhere. **Why OOS:** pre-existing test hook; not introduced or amplified by the enumeration refactor (only documented in tests).
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `SECURITY.md` (general `/tmp` posture) — `/tmp` is documented as shared scratch, not a confidentiality boundary. The new enumeration lists briefly live under `${TMPDIR:-/tmp}` with `mktemp` (typically mode `0600`). On multi-user hosts, operators should not point `TMPDIR` at an untrusted, world-writable directory when running `/cleanup`. **Why OOS:** generic host hygiene; the branch does not widen deletion scope beyond existing `find` + `rm` semantics, and guarded `mktemp` is the conventional mitigation for capturing `find` exit status.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/cleanup/scripts/cleanup.sh:57-66,110-124
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-zero top-level enumeration find exit skips the entire pass even when partial results were written. On macOS/BSD, one unreadable top-level session entry can make find exit non-zero after listing others; old code could delete other stale entries silently, new code warns but skips all readable stale entries too. Document the tradeoff, or distinguish total vs partial enumeration failure if partial cleanup is desired.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/design/scripts/test-run-step3-review.sh:370-395
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Integration-seam stub only guards against unknown forwarded flags, not missing required loop flags. If plan-review-loop.sh adds a new required argv flag and run-step3-review.sh is not updated, the seam test can still pass while live Step 3 fails at the real loop boundary. Extend the seam test to compare driver argv against the real loop contract (help/argv snapshot or required-flag checklist).
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/cleanup/scripts/cleanup.sh:57,110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Enumeration find stderr is still suppressed. Operator sees failed to enumerate with no hint whether the cause is EACCES, ENOENT, or I/O error, slowing recovery on permission problems. Include a redacted find stderr line in the warning when available.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: skills/cleanup/scripts/cleanup.sh:136-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Symlink reaper enumeration remains silent fail-open. Unreadable sessions parent can make the symlink find fail with zero SYMLINKS_REMOVED and no warning, indistinguishable from no dangling links. Apply the same temp-list + warn/skip fail-safe pattern if consistency is desired (separate change).
- **Suggested revision**: Address the concern above.

### FINDING_23: `4e97d59cd` — Warn on cleanup enumeration failure; remove dead convergence threshold  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `4e97d59cd` — Warn on cleanup enumeration failure; remove dead convergence threshold
- **Suggested revision**: Address the concern above.

### FINDING_24: `25d20f33e` / `717fb8202` — `chore(larch-logs)` (out of scope per review rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `25d20f33e` / `717fb8202` — `chore(larch-logs)` (out of scope per review rules) **Scope vs plan** | Workstream | Plan requirement | Diff status | |------------|------------------|-------------| | **A** — `cleanup.sh` enumeration fail-safe | Guarded `mktemp`, observable top-level `find`, warnings, `rm -f`, `|| true` on read loops | Implemented in `cleanup.sh` (cache + `/tmp` passes) | | **A** — docs | `cleanup.md` fail-safe bullet + edit-in-sync; `SECURITY.md` | Updated | | **A** — tests | `write_stub_enum_failure`, enumeration + mktemp cases | Added in `test-cleanup.sh` | | **B** — dead `--convergence-threshold` | Remove from driver, SKILL, docs, tests; add integration seam | Done; forward line removed from `run-step3-review.sh` invocation | | **B** — structure harness | Drop convergence forwarding pins | SKILL `contains` removed; `run-step3-review.sh` already had `absent` pin (unchanged) | | **No-ops** | `approval-gates.md`, cache/tmp asymmetry docs | Correctly untouched | | **Explicit no-change** | `plan-review-loop.sh`, intentional reject test | Unchanged | Grep across `skills/`, `scripts/`, `docs/` shows no remaining `LARCH_DESIGN_CONVERGENCE_THRESHOLD` / `--convergence-threshold` except the intentional `test-plan-review-loop.sh` “removed flag rejected” case.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Workstream **A** matches the plan’s temp-file idiom: enumeration exit is owned by `if find … >"$_cache_list"`, loop-body failures stay behind `|| true`, and `mktemp` failures warn instead of tripping `set -e` before `emit_kv`.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - Workstream **A** matches the plan’s temp-file idiom: enumeration exit is owned by `if find … >"$_cache_list"`, loop-body failures stay behind `|| true`, and `mktemp` failures warn instead of tripping `set -e` before `emit_kv`.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Workstream **B** fixes the live mismatch (`run-step3-review.sh` no longer forwards `--convergence-threshold`; loop invocation is only `--design-tmpdir` … `--round-cap`).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - Workstream **B** fixes the live mismatch (`run-step3-review.sh` no longer forwards `--convergence-threshold`; loop invocation is only `--design-tmpdir` … `--round-cap`).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] The new integration-seam case (`driver argv matches plan-review-loop contract`) mirrors the real loop’s allowed flags and `unknown option` / exit `2` behavior sufficiently to catch forwarding drift.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - The new integration-seam case (`driver argv matches plan-review-loop contract`) mirrors the real loop’s allowed flags and `unknown option` / exit `2` behavior sufficiently to catch forwarding drift.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Planned no-ops are respected: `approval-gates.md` already cites hardcoded convergence; cache vs `/tmp` predicate asymmetry remains documented in `cleanup.md` without this PR re-editing it.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - Planned no-ops are respected: `approval-gates.md` already cites hardcoded convergence; cache vs `/tmp` predicate asymmetry remains documented in `cleanup.md` without this PR re-editing it.
- **Suggested revision**: Address the concern above.

### FINDING_29: **code-quality** `skills/cleanup/scripts/test-cleanup.sh:218-253` — `assert_eq`, `assert_contains`, and `kv_get` all call `fail`, which runs `exit 1` (lines 16–18, 21–28, 31–36), so a failed assertion aborts the harness before the trailing `unset PATH_PREFIX` in the two new enumeration cases. That pattern already existed for `find-failure-skips-deletion`, but placing `enumeration-failure-warns-tmp` immediately before `mktemp-allocation-failure-warns` amplifies the risk: `mktemp-allocation-failure-warns` never sets `PATH_PREFIX`, yet `run_cleanup` prefers a leaked shell `PATH_PREFIX` over per-case `$work/bin` (line 101). If `enumeration-failure-warns-tmp` fails after `PATH_PREFIX="$work/bin:"` and before line 231, the next case still runs `cleanup.sh` with the enumeration-failure stub on `PATH`, so `mktemp-allocation-failure-warns` can fail for the wrong reason (enumeration warnings instead of allocation warnings) and later cases can flake similarly. **Suggested fix:** Move `unset PATH_PREFIX` to immediately after each `run_cleanup` (before any assertion), or wrap each stubbed case in a subshell / `trap 'unset PATH_PREFIX' RETURN` so teardown runs even when `fail` exits. The `mktemp-allocation-failure-warns` block already does the right thing for `TMPDIR`/`chmod` (lines 244–245 run before assertion failures at 246+).
- **Reviewer**: dyn-test-env-isolation-output.txt
- **Concern**: - **code-quality** `skills/cleanup/scripts/test-cleanup.sh:218-253` — `assert_eq`, `assert_contains`, and `kv_get` all call `fail`, which runs `exit 1` (lines 16–18, 21–28, 31–36), so a failed assertion aborts the harness before the trailing `unset PATH_PREFIX` in the two new enumeration cases. That pattern already existed for `find-failure-skips-deletion`, but placing `enumeration-failure-warns-tmp` immediately before `mktemp-allocation-failure-warns` amplifies the risk: `mktemp-allocation-failure-warns` never sets `PATH_PREFIX`, yet `run_cleanup` prefers a leaked shell `PATH_PREFIX` over per-case `$work/bin` (line 101). If `enumeration-failure-warns-tmp` fails after `PATH_PREFIX="$work/bin:"` and before line 231, the next case still runs `cleanup.sh` with the enumeration-failure stub on `PATH`, so `mktemp-allocation-failure-warns` can fail for the wrong reason (enumeration warnings instead of allocation warnings) and later cases can flake similarly. **Suggested fix:** Move `unset PATH_PREFIX` to immediately after each `run_cleanup` (before any assertion), or wrap each stubbed case in a subshell / `trap 'unset PATH_PREFIX' RETURN` so teardown runs even when `fail` exits. The `mktemp-allocation-failure-warns` block already does the right thing for `TMPDIR`/`chmod` (lines 244–245 run before assertion failures at 246+).
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **`write_stub_enum_failure` selectivity** — Triggering on `-mindepth` matches only the cache and `/tmp` enumeration `find` invocations in `cleanup.sh` (lines 57 and 110). The nested activity scan uses `-maxdepth 5` without `-mindepth` (line 26), and the symlink reaper uses `-maxdepth 1 -name … -type l` without `-mindepth` (line 142), so the stub does not interfere with those paths; that matches the plan and existing nested-scan tests.
- **Reviewer**: dyn-test-env-isolation-output.txt
- **Concern**: - **`write_stub_enum_failure` selectivity** — Triggering on `-mindepth` matches only the cache and `/tmp` enumeration `find` invocations in `cleanup.sh` (lines 57 and 110). The nested activity scan uses `-maxdepth 5` without `-mindepth` (line 26), and the symlink reaper uses `-maxdepth 1 -name … -type l` without `-mindepth` (line 142), so the stub does not interfere with those paths; that matches the plan and existing nested-scan tests.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **`mktemp-allocation-failure-warns` teardown** — `run_cleanup` is called under `set -e`, but `run_cleanup` wraps the script invocation in `set +e` (lines 106–130), so a non-zero `cleanup.sh` exit only sets `CASE_RC` and does not trip errexit. `chmod 755` and `unset TMPDIR` run before the `[[ "$CASE_RC" -eq 0 ]]` check and before `assert_*`, so a failed assertion or non-zero RC does not leave an exported bad `TMPDIR` for later cases.
- **Reviewer**: dyn-test-env-isolation-output.txt
- **Concern**: - **`mktemp-allocation-failure-warns` teardown** — `run_cleanup` is called under `set -e`, but `run_cleanup` wraps the script invocation in `set +e` (lines 106–130), so a non-zero `cleanup.sh` exit only sets `CASE_RC` and does not trip errexit. `chmod 755` and `unset TMPDIR` run before the `[[ "$CASE_RC" -eq 0 ]]` check and before `assert_*`, so a failed assertion or non-zero RC does not leave an exported bad `TMPDIR` for later cases.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **`/usr/bin/find` in stubs** — `write_stub_enum_failure` uses `exec /usr/bin/find "$@"` (line 71), same as `write_stub_find_failure` (line 54). That predates this branch; on hosts where `find` is not `/usr/bin/find`, stub fallback paths could fail, but that is not introduced by these three cases alone.
- **Reviewer**: dyn-test-env-isolation-output.txt
- **Concern**: - **`/usr/bin/find` in stubs** — `write_stub_enum_failure` uses `exec /usr/bin/find "$@"` (line 71), same as `write_stub_find_failure` (line 54). That predates this branch; on hosts where `find` is not `/usr/bin/find`, stub fallback paths could fail, but that is not introduced by these three cases alone.
- **Suggested revision**: Address the concern above.

