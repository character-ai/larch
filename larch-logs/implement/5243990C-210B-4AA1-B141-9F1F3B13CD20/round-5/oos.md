### FINDING_16: [OUT_OF_SCOPE] Pre-existing test-stall-recovery case 19 (read default)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Pre-existing case 19 documents read default on missing file; unrelated to clear-stall KV contract unless tightening `read-session-env-key` globally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] plugin-root.env sourcing trust model (step-18b)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.sh` sources `plugin-root.env` when `CLAUDE_PLUGIN_ROOT` is unset; a same-UID writer modifying session tmpdir artifacts could redirect helper execution to attacker-controlled code during Step 18b—inherited same-user trust per `SECURITY.md`; cross-cutting hardening if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] clear-stall/seed lack absolute --implement-tmpdir containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New subcommands do not require absolute/canonical `--implement-tmpdir` containment; mis-set or relative tmpdir with unexpected cwd could write `ship-pr-state.sh` outside the intended session directory—align with repo-wide policy if adopted, else accept as pre-existing classify pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] Harness does not stub destination read exit 1
- **Reviewer(s)**: dyn-kv-emission-atomicity-output.txt
- **Severity**: latent
- **Concern**: `case22-clear-dest-assert-fail` / `case22-seed-dest-assert-fail` use no-op `mv` and value mismatch; they do not cover `read-session-env-key.sh` exiting non-zero on destination re-read, so the post-mv false-success regression would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-emission-atomicity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] case22-seed-awk-metachar does not test -v escape handling
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: Test plants semicolon inside `PHASE` value and validates allowlist override, not `\`-in-`-v` corruption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Future callers could pass unsanitized kv_get values through rewrite helper
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: Real-world keys like `BAIL_FAILURE_DETAIL_LOG` / `PR_URL` can contain `\` but are outside the `-v` rewrite set on this branch; corruption would require a future change to pass them through `rewrite_ship_pr_state_keys` without sanitization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] clear-stall leaves non-rewritten lines verbatim on disk
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` only rewrites `STALL_TRACKING` / `STALL_STEP`; other lines (e.g. malicious `PHASE=…`) remain—a state-integrity concern for downstream readers, not awk `-v` injection in the new helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] step-18b does not add awk -v rewrite surface
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: nit
- **Concern**: E2 (`step-18b-final-report.sh`) does not use the awk rewrite path; no additional `-v` value-injection surface there beyond pre-existing patterns elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] lint-bash32 / test-stall-recovery do not catch compound local -a or 3.2 runtime
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-bash32.sh` does not flag compound `local -a` init or unsafe empty `"${awk_v[@]}"` under `set -u`; `test-stall-recovery-report.sh` runs on CI bash (4.x/5.x) unless explicitly run under `/bin/bash` 3.2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Pre-existing review-and-fix compound local -a precedent
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh:812` already uses two-name `local -a round_summary_files=() round_summary_glob=()` pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] Prior round accepted two-name compound local -a as OOS
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: Round 2 noted `local -a keys=() vals=()` as acceptable OOS; this branch extends to three-name form with `awk_v`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] awk_begin+= / C-style for / vals subscript use are Bash 3.2–safe
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: nit
- **Concern**: No issue identified for those constructs in the new helper.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters):**
- **Highest-impact in-scope**: FINDING_1 (post-mv read), FINDING_19 (Step 18b duplicate emit), FINDING_20 (keyless exit-code vs `CLEARED` / plan exit 3).
- **Subsumed without separate blocks**: input FINDING_28 (`snapshot_ok` OOS duplicate of FINDING_9); input FINDING_41–45 split where distinct OOS observations remain; input FINDING_27 merged into FINDING_7 (OOS print-stdout cluster).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] Step 18 omits write-final-report --print-stdout (ops / E2E)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 18 intentionally drops `write-final-report --print-stdout`; the report body appears only via orchestrator emit. Collapsible Bash no longer shows a duplicate body; there is no E2E UI regression test if that channel returns. Product/ops may want release notes or future E2E if operators relied on collapsed stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

