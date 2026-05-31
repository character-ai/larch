Aggregating reviewer findings: checking for additional reviewer output files and verifying key overlap areas in the codebase.
Normalized aggregator output from the supplied reviewer slots. Security slots 16–22 are positive attestations (no behavioral risk to fix) and are omitted from the actionable list. Merged duplicates per the merge rules below.

### FINDING_1: risk-integration — uncommitted orchestrator-fence harness breaks CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `Makefile` and `SKILL.md` wire `test-step3-orchestrator-fence.sh` into `test-harnesses-9` / `make test-step3-orchestrator-fence`, but the harness is not in the committed tree (untracked or absent at HEAD). Clean checkouts and CI shard 9 fail with “No such file.” Once the script is added, `script-md-siblings` / relevant-checks also require `test-step3-orchestrator-fence.md` alongside other harness stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: correctness — Step 3 orchestrator fence dropped LOOP_STATUS allow-list validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After allowlisted parsing of `.step3-review-result.env` and stdout merge, the orchestrator only treats **empty** `LOOP_STATUS` as `panel-failed`. Invalid or tampered values (e.g. `cap_reached`, corrupted handoff) are not re-normalized against the branch-matrix allow-list, so no matrix arm matches and Gate routing becomes undefined. The same gap applies when stdout fallback is used without a result env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Re-apply allow-list normalization in the orchestrator after merge; and/or let this invocation's stdout override file for LOOP_STATUS/TALLY when rc!=0 or values disagree.

### FINDING_3: correctness — file-first `.step3-review-result.env` can prefer stale outer state over fresh driver output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: File-first handoff can keep stale outer `LOOP_STATUS` (e.g. prior `converged`) when the current driver exits non-zero with stdout `LOOP_STATUS=panel-failed`, mis-routing Gate B instead of panel-failed short-circuit. The orchestrator no longer reads `.step3-plan-review-result.env` written at loop completion; if the loop writes inner tally-error but the driver is killed before outer write, a stale outer `complete` can win over inner/`stdout` tally-error and skip rollback and the correct Gate B path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer stdout or inner env for status keys for this invocation; or write outer result env immediately after parsing inner loop output.

### FINDING_4: code-quality — redundant double-parse of inner result env in driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` double-parses inner result env (`phase_driver_read_result_env` plus duplicate case filter and second WARN pass), increasing maintenance cost and risk of divergent WARN vs KV handling on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single-pass parse: allowlisted lines from helper, one WARN scan.

### FINDING_5: code-quality — inconsistent indentation in non-cap else branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Extra indentation in the non-cap `else` branch of `run-step3-review.sh` reduces readability of cap vs panel control flow for later #3133 drivers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Re-indent else body to match file style.

### FINDING_6: correctness — review-round-count persist order vs cursor advance changed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Driver persists `review-round-count` after HARD cursor advance; inline Step 3 persisted before cursor. On write-cursor failure before first launch, rollback avoids consuming a slot (extra review before tier cap vs legacy behavior). Behavior may be intentional but differs from prior cap accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document as intentional in run-step3-review.md/SKILL.md or restore pre-persist if strict parity with legacy cap accounting is required.

### FINDING_7: correctness — `run-step3-review.md` contract order mismatches implementation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Contract lists pending-round persist before cursor advance; implementation does the opposite, confusing operators tracing round-count vs cursor failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Swap responsibility items 3 and 4 to match run-step3-review.sh.

### FINDING_8: correctness — driver exit 2 does not force terminal orchestrator handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Driver exit 2 only prints a warning; the SKILL fence continues unless `LOOP_STATUS` is empty. Exit 2 with stray stdout KVs could leave a non-terminal `LOOP_STATUS` and skip panel-failed defaulting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On _plan_review_rc=2 force LOOP_STATUS=panel-failed or exit the fence.

### FINDING_9: risk-integration — orchestrator-fence harness omits driver exit-2 case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-step3-orchestrator-fence.sh` does not cover driver exit 2 / configuration-error handoff pinned in `SKILL.md`; a regression in SKILL handling of `run-step3-review.sh` exit 2 could ship while driver-only argv tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-step3-orchestrator-fence.sh (or test-design-structure pins) with an exit-2 handoff case matching the SKILL fence.

### FINDING_10: risk-integration — harness not listed in `run-step3-review.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.md` Harness section omits `test-step3-orchestrator-fence.sh` cited in `SKILL.md`, causing doc/harness discovery drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document test-step3-orchestrator-fence.sh in run-step3-review.md or lib-phase-driver.md once committed.

### FINDING_11: risk-integration — cap-guard prose incomplete on rollback triggers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Cap-guard prose in `SKILL.md` documents rollback only for `TALLY_PLAN_REVIEW_STATUS=tally-error`, not `LOOP_STATUS` tally-error or degraded-empty-collector handled in `run-step3-review.sh`, so operators following prose only may misdiagnose driver behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update cap-guard prose to list all rollback triggers consistent with run-step3-review.sh and the branch matrix.

### FINDING_12: [OUT_OF_SCOPE] code-quality — `session_get` duplicates phase-driver primitive in implement Step 2
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/run-step2-dispatch.sh` duplicates `lib-phase-driver.sh` KV reader; future Step 2 edits may drift from shared phase-driver reader.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib-phase-driver.sh from run-step2-dispatch when touching Step 2 stack (not required for this PR).

### FINDING_13: [OUT_OF_SCOPE] architecture — SKILL fence duplicated in orchestrator-fence harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Step 3 orchestrator handoff is mirrored in `test-step3-orchestrator-fence.sh`; skill fence and harness can drift without shared extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep harness committed; consider lib or structure-test extraction in a follow-up.

### FINDING_14: [OUT_OF_SCOPE] risk-integration — no `--help` exit-0 launcher smoke for `test-run-step3-review.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Pre-existing launcher harness pattern; not a regression on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: add --help case aligned with launcher-argv-test-coverage.md conventions.

### FINDING_15: [OUT_OF_SCOPE] security — cap env and review-round-count writes lack symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `.step3-review-cap.env` and `review-round-count.txt` are still written with plain `cat`/`printf` without symlink-target checks while `.step3-review-result.env` is hardened; matches pre-extract inline SKILL behavior and documented same-UID `/design` tmpdir trust model; defense-in-depth only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security — stdout KV merge lacks newline rejection from `phase_driver_read_result_env`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Stdout KV merge does not apply `phase_driver_read_result_env` newline rejection (file path does); trust boundary remains in-tree `plan-review-loop.sh`; unchanged from former inline fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] architecture — tier cap vs HARD cursor use different run-params keys
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier cap uses `design_classification` while HARD cursor uses `workflow_path`; inconsistent or hand-edited run-params can desync cap vs cursor (e.g. SIMPLE cap with HARD workflow_path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider single source of truth in a follow-up.

### FINDING_18: [OUT_OF_SCOPE] correctness — `read-cursor` under `set -e` aborts driver before normalized result env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-zero `read-cursor` exit aborts driver before writing `.step3-review-result.env`; orchestrator infers panel-failed only from empty `LOOP_STATUS`. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional set +e and explicit panel-failed handoff if abort is too harsh.

### FINDING_19: [OUT_OF_SCOPE] architecture — `approval-gates.md` still cites inner plan-review result env
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `approval-gates.md` still references `.step3-plan-review-result.env` as primary; operators may inspect stale file instead of `.step3-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Sync approval-gates.md to .step3-review-result.env primary (follow-up).

---

**Aggregation notes (non-voting):**
- Input items 16–22 from `cursor-specialist-security-output.txt` are security **improvement attestations**, not defects; they are not promoted to `### FINDING_N:` blocks.
- Original input 2 (missing `.md` sibling) is folded into **FINDING_1** (same integration failure surface).
- Original 3, 8, 25 (allow-list portion), and 31 → **FINDING_2**; original 26 and 25 (stale file-first portion) → **FINDING_3** (distinct fix: merge semantics vs allow-list normalization).
- Original 11 and 13 remain separate (**FINDING_8** vs **FINDING_9**): fence behavior vs harness coverage.
