Structured aggregator output from the supplied reviewer findings (merged by shared behavioral risk; severity = max across sources).

### FINDING_1: Post-mv destination STALL_TRACKING re-read can emit false success
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-kv-emission-atomicity-output.txt
- **Severity**: important
- **Concern**: After `mv`, `clear-stall` and `seed-terminal-state` re-read `STALL_TRACKING` on the destination `ship-pr-state.sh` using `if tracking=$(read-session-env-key.sh ...); then ...` instead of the temp-read `|| emit_cleared_false_exit` / `|| emit_seeded_false_exit` chain. On non-zero read exit, the `if` branch is skipped, value checks are skipped, and the scripts can still emit `CLEARED=true` or `SEEDED=true` without proving disk state—breaking the documented contract and risking orchestrator in-memory stall clear while disk still has `STALL_TRACKING=true` (or unverified seed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-kv-emission-atomicity-output.txt: Mirror the temp-read chain: `tracking=$(read-session-env-key.sh --file "$state" ...) || emit_cleared_false_exit 1` (and the seed analogue), then `if [ "$tracking" != false ]` / `!= true`; remove the outer `if ...; then` wrapper. Add harness cases that stub `read-session-env-key.sh` to exit 1 on the destination call only (distinct from `noop-mv`, which exercises a stale/wrong value with exit 0).

### FINDING_2: Dead `token_rc` in step-18b-final-report.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never emitted or branched on, adding dead state; readers may assume token failure affects `EMIT_BODY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: clear-stall duplicates three-tier state validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` inlines three-tier validation instead of calling `check_ship_pr_state_format`, so format rules can drift between helpers and docs when only one path is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: stall-recovery.md lacks concrete CLEARED/SEEDED parse example
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stall-recovery.md` tells the orchestrator to parse `CLEARED`/`SEEDED` without a concrete stdout capture/parse example; models may improvise parsing unlike the pinned SKILL Step 18b awk block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Duplicated Step 18 EMIT_BODY test matrix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 18 `EMIT_BODY` matrix is duplicated across `test-step-18b-final-report.sh` and `test-write-final-report.sh`; fixes to step-18b logic may require updating two stub trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: cmd_classify skips reads for keyless ship-pr-state.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `cmd_classify` now skips state-key reads when `ship-pr-state.sh` is keyless, changing classification inputs; edge runs with empty/comment-only state files classify from session-env only—a subtle behavior change that may be outside explicit plan scope unless documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Add a plan note that classify must ignore keyless on-disk state; no code change needed if asymmetry is accepted

### FINDING_7: [OUT_OF_SCOPE] Step 18 omits write-final-report --print-stdout (ops / E2E)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 18 intentionally drops `write-final-report --print-stdout`; the report body appears only via orchestrator emit. Collapsible Bash no longer shows a duplicate body; there is no E2E UI regression test if that channel returns. Product/ops may want release notes or future E2E if operators relied on collapsed stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Temp files not removed on clear/seed assert failure paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Failed clear/seed attempts can leave `ship-pr-state.sh.tmp.*` files in `IMPLEMENT_TMPDIR` when destination assert paths fail without cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Contract documents `snapshot_ok` but script does not emit it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `step-18b-final-report.md` documents `snapshot_ok` but `step-18b-final-report.sh` has no such variable or KV; maintainers/operators may expect a machine-readable snapshot status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Remove snapshot_ok from the contract or add the variable to the script

### FINDING_10: Step 18b SKILL does not document --print-stdout removal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Intentional delta: Step 18 drops `write-final-report --print-stdout`; collapsible Bash no longer shows summary body (only orchestrator verbatim emit). Worth noting in release/review notes for panel awareness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Harness gap: temp read wrong value after rewrite
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan requires temp-read assert failure to emit `CLEARED=false`; tests cover mktemp/mv/dest value but not wrong value on temp after rewrite—a bug leaving `STALL_TRACKING=true` in temp could pass temp write and only fail open at destination depending on `mv` outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Only first step-18b case asserts `.step17-emitted` never written
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Only the first harness case asserts the wrapper never writes `.step17-emitted`; a later case could regress to writing the sentinel without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: clear-stall test does not assert PR_URL preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: clear-stall append case sets `PR_URL` but does not assert preservation after rewrite; regression dropping `PR_*` keys on clear would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: No structural pin for CLEARED/SEEDED parsing on keyless exit-0 clear-stall
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No structural pin that the orchestrator must branch on `CLEARED`/`SEEDED` KVs for keyless exit-0 `clear-stall`; models may treat exit 0 alone as success and clear in-memory stall while disk is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: STEP17_EMITTED_PRESENT parsed but unused in orchestrator prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed but unused; dead parse line and possible divergence between structural pin and runtime emit logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Pre-existing test-stall-recovery case 19 (read default)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Pre-existing case 19 documents read default on missing file; unrelated to clear-stall KV contract unless tightening `read-session-env-key` globally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] plugin-root.env sourcing trust model (step-18b)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.sh` sources `plugin-root.env` when `CLAUDE_PLUGIN_ROOT` is unset; a same-UID writer modifying session tmpdir artifacts could redirect helper execution to attacker-controlled code during Step 18b—inherited same-user trust per `SECURITY.md`; cross-cutting hardening if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] clear-stall/seed lack absolute --implement-tmpdir containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New subcommands do not require absolute/canonical `--implement-tmpdir` containment; mis-set or relative tmpdir with unexpected cwd could write `ship-pr-state.sh` outside the intended session directory—align with repo-wide policy if adopted, else accept as pre-existing classify pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: step-18b snapshot cp failure can force duplicate EMIT_BODY emit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Snapshot `cp` failure removes `.step18-prebody` and can force `EMIT_BODY=true` even when `.step17-emitted` exists and `summary-final.md` is unchanged after `write-final-report`, causing a second verbatim emit (NEVER #20 duplicate). On `cp` failure with `.step17-emitted` present, require `cmp` proof of change before promoting `emit_body`; do not treat absent prebody alone as changed when the sentinel is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: clear-stall keyless present file exits 0 with CLEARED=false vs plan exit 3
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `clear-stall` treats a syntax-valid keyless present `ship-pr-state.sh` as exit 0 `CLEARED=false` while malformed paths exit 3. Orchestration that branches only on exit code (not `CLEARED`) may treat a present keyless file as benign no-op instead of format failure; diverges from plan-specified `check_ship_pr_state_format` failure (exit 3) unless formally amended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Restore exit 3 for keyless present files per the original plan, or formally amend plan/acceptance to codify the documented three-tier asymmetry

### FINDING_21: seed-terminal-state overwrites present keyless state file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SEED_MODE=seed` overwrites a present keyless state file with minimal Step-8 keys only, dropping non-key content/comments that might have carried recoverable context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: SKILL Step 18b missing explicit handling when EMIT_BODY/WFR_RC KVs absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 18b prose does not state that missing `EMIT_BODY`/`WFR_RC` KVs after awk parse mean no verbatim emit; polluted stdout yields empty `EMIT_BODY` (fail-closed in practice) but is not spelled out beside the parse block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: test-step-18b-final-report omitted from Makefile mega .PHONY line
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-step-18b-final-report` omitted from mega aggregate `.PHONY` line 4 per plan literal wording; inconsistent with `test-write-final-report` registration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add test-step-18b-final-report to line 4 mega .PHONY or amend plan to match dedicated-line convention

### FINDING_24: [OUT_OF_SCOPE] Harness does not stub destination read exit 1
- **Reviewer(s)**: dyn-kv-emission-atomicity-output.txt
- **Severity**: latent
- **Concern**: `case22-clear-dest-assert-fail` / `case22-seed-dest-assert-fail` use no-op `mv` and value mismatch; they do not cover `read-session-env-key.sh` exiting non-zero on destination re-read, so the post-mv false-success regression would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-emission-atomicity-output.txt: Address the concern above.

### FINDING_25: rewrite_ship_pr_state_keys gawk -v backslash escape footgun
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` passes replacement values through `gawk -v`, which interprets backslash escapes; unsanitized future callers could silently alter values before write. Current callers use literals or `safe_*` allowlists; pass-through keys are not fed via `-v` today—no present exploit path, but the helper is reusable risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: centralize awk-safe encoding in `rewrite_ship_pr_state_keys` (e.g. double backslashes before building `awk_v`, or pass values via `ENVIRON` / a temp file instead of `-v`), document the invariant in `stall-recovery-report.md`, and add a harness case that writes a backslash-heavy value into a rewritten key and asserts the on-disk line is byte-identical.

### FINDING_26: [OUT_OF_SCOPE] case22-seed-awk-metachar does not test -v escape handling
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: Test plants semicolon inside `PHASE` value and validates allowlist override, not `\`-in-`-v` corruption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Future callers could pass unsanitized kv_get values through rewrite helper
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: Real-world keys like `BAIL_FAILURE_DETAIL_LOG` / `PR_URL` can contain `\` but are outside the `-v` rewrite set on this branch; corruption would require a future change to pass them through `rewrite_ship_pr_state_keys` without sanitization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] clear-stall leaves non-rewritten lines verbatim on disk
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` only rewrites `STALL_TRACKING` / `STALL_STEP`; other lines (e.g. malicious `PHASE=…`) remain—a state-integrity concern for downstream readers, not awk `-v` injection in the new helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] step-18b does not add awk -v rewrite surface
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: E2 (`step-18b-final-report.sh`) does not use the awk rewrite path; no additional `-v` value-injection surface there beyond pre-existing patterns elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.

### FINDING_30: Bash 3.2 compound `local -a keys=() vals=() awk_v=()` in rewrite helper
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: latent
- **Concern**: GNU Bash 3.2 only applies array attributes to the first name in a multi-variable `local -a` declaration; `vals` and `awk_v` start as empty scalars and rely on implicit promotion on `+=`—a portability footgun on the stall-state rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Split into three declarations on separate lines (`local -a keys=()` / `local -a vals=()` / `local -a awk_v=()`), matching `BASH_AUTHORING.md` §3 style; optionally harden the final call with the repo’s Bash 3.2 empty-array idiom `"${awk_v[@]+"${awk_v[@]}"}"` (see `scripts/test-render-final-summary-bash32.sh` / issue #3039) if `n` can ever be zero.

### FINDING_31: [OUT_OF_SCOPE] lint-bash32 / test-stall-recovery do not catch compound local -a or 3.2 runtime
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-bash32.sh` does not flag compound `local -a` init or unsafe empty `"${awk_v[@]}"` under `set -u`; `test-stall-recovery-report.sh` runs on CI bash (4.x/5.x) unless explicitly run under `/bin/bash` 3.2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Pre-existing review-and-fix compound local -a precedent
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh:812` already uses two-name `local -a round_summary_files=() round_summary_glob=()` pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Prior round accepted two-name compound local -a as OOS
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: Round 2 noted `local -a keys=() vals=()` as acceptable OOS; this branch extends to three-name form with `awk_v`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] awk_begin+= / C-style for / vals subscript use are Bash 3.2–safe
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: No issue identified for those constructs in the new helper.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters):**
- **Highest-impact in-scope**: FINDING_1 (post-mv read), FINDING_19 (Step 18b duplicate emit), FINDING_20 (keyless exit-code vs `CLEARED` / plan exit 3).
- **Subsumed without separate blocks**: input FINDING_28 (`snapshot_ok` OOS duplicate of FINDING_9); input FINDING_41–45 split where distinct OOS observations remain; input FINDING_27 merged into FINDING_7 (OOS print-stdout cluster).
