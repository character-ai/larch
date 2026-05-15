### FINDING_1: panel [code-review/accepted]

## **Commits** (`git merge-base HEAD main`..HEAD): `c190cbc4 fix(implement): add NEVER #13 prohibiting orchestrator from writing finalize-state.sh`, `63b53400 chore(larch-logs): flush implement run 0D35AD07-8E94-4089-AD57-E0911A2267C0`.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Hard constraint:** No file writes were performed, so no `.tsv` sidecar file was created. TSV lines for copy/paste are below.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** (`correctness`) — [`skills/implement/SKILL.md:60-60`](skills/implement/SKILL.md):60 — NEVER #13’s “Why” claims clobbering yields a cascade of `state-file missing required key` errors during teardown and ties that to “all 20 required keys” from `write_finalize_state()`. Teardown actually calls `load_and_validate_state` → `require_state_keys`, which only requires 17 keys and omits `STALL_STEP`, `RUN_ID`, `EXPECTED_SESSION_ID`, `EXPECTED_TMPDIR_BASENAME_PREFIX`, and `NO_LOGS_COMMIT` ([`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):173-181). A bad file can still miss those fields yet pass teardown’s key gate; `RUN_ID` can be empty while manifest recovery branches still run ([`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):1531-1586). **Suggested fix:** Narrow NEVER #13 to match `require_state_keys` + `require_bool_state`, or extend the shell validator to require the full 20-key ship-pr contract if that is the real invariant.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important** (`correctness`) — [`skills/implement/SKILL.md:60-60`](skills/implement/SKILL.md):60 — NEVER #13’s “Why” claims clobbering yields a cascade of `state-file missing required key` errors during teardown and ties that to “all 20 required keys” from `write_finalize_state()`. Teardown actually calls `load_and_validate_state` → `require_state_keys`, which only requires 17 keys and omits `STALL_STEP`, `RUN_ID`, `EXPECTED_SESSION_ID`, `EXPECTED_TMPDIR_BASENAME_PREFIX`, and `NO_LOGS_COMMIT` ([`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):173-181). A bad file can still miss those fields yet pass teardown’s key gate; `RUN_ID` can be empty while manifest recovery branches still run ([`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):1531-1586). **Suggested fix:** Narrow NEVER #13 to match `require_state_keys` + `require_bool_state`, or extend the shell validator to require the full 20-key ship-pr contract if that is the real invariant.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** (`risk-integration`) — [`skills/implement/SKILL.md:1900`](skills/implement/SKILL.md):1900 — The new Step 18 sentence says `finalize-state.sh` “was written by `ship-pr.sh`”. On the documented `--design-only` path, the matrix and post-/design matrix skip Steps 8+ entirely ([`skills/implement/SKILL.md:1011`](skills/implement/SKILL.md):1011, [`skills/implement/SKILL.md:1066`](skills/implement/SKILL.md):1066), so `ship-pr.sh` never runs and `write_finalize_state()` is never called ([`scripts/ship-pr.sh`](scripts/ship-pr.sh):1070–1072 is only reached from the postmerge phase). Yet Step 18 still invokes teardown with `--state-file "$IMPLEMENT_TMPDIR/finalize-state.sh"` ([`skills/implement/SKILL.md:1907-1908`](skills/implement/SKILL.md):1907-1908), and [`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):117-119 requires that path to exist and be readable before teardown proceeds. An operator trusts the new prose, assumes a ship-pr bug when the file is absent, and NEVER #13 forbids the only prompt-side repair. **Suggested fix:** Qualify the Step 18 line: state that `ship-pr.sh` writes the file only after runs that entered postmerge; for flows that never invoke Step 8+ (e.g. design-only), either document the real producer or add a mechanical writer outside the orchestrator (shell entrypoint), so NEVER #13 and teardown stay consistent.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** (`risk-integration`) — [`skills/implement/SKILL.md:1900`](skills/implement/SKILL.md):1900 — The new Step 18 sentence says `finalize-state.sh` “was written by `ship-pr.sh`”. On the documented `--design-only` path, the matrix and post-/design matrix skip Steps 8+ entirely ([`skills/implement/SKILL.md:1011`](skills/implement/SKILL.md):1011, [`skills/implement/SKILL.md:1066`](skills/implement/SKILL.md):1066), so `ship-pr.sh` never runs and `write_finalize_state()` is never called ([`scripts/ship-pr.sh`](scripts/ship-pr.sh):1070–1072 is only reached from the postmerge phase). Yet Step 18 still invokes teardown with `--state-file "$IMPLEMENT_TMPDIR/finalize-state.sh"` ([`skills/implement/SKILL.md:1907-1908`](skills/implement/SKILL.md):1907-1908), and [`scripts/implement-finalize.sh`](scripts/implement-finalize.sh):117-119 requires that path to exist and be readable before teardown proceeds. An operator trusts the new prose, assumes a ship-pr bug when the file is absent, and NEVER #13 forbids the only prompt-side repair. **Suggested fix:** Qualify the Step 18 line: state that `ship-pr.sh` writes the file only after runs that entered postmerge; for flows that never invoke Step 8+ (e.g. design-only), either document the real producer or add a mechanical writer outside the orchestrator (shell entrypoint), so NEVER #13 and teardown stay consistent.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Important** · **risk-integration** · Plan section “Files to modify” vs branch diff · The implementation plan lists only [`skills/implement/SKILL.md`](skills/implement/SKILL.md), but the branch also adds [`larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/manifest.json`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/manifest.json), [`plan-goals-test.md`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-goals-test.md), and [`plan-review-tally.json`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-review-tally.json) (`63b53400`). That breaks strict plan-to-diff traceability and ships session/run metadata alongside the skill doc change, which can confuse review (dirty-tree / unrelated churn) unless flushing those paths was an explicit, documented part of this change. **Suggested fix:** Limit the PR to `skills/implement/SKILL.md`, or record the extra paths in the plan and justify the flush commit as required deliverable.

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** · **risk-integration** · Plan section “Files to modify” vs branch diff · The implementation plan lists only [`skills/implement/SKILL.md`](skills/implement/SKILL.md), but the branch also adds [`larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/manifest.json`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/manifest.json), [`plan-goals-test.md`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-goals-test.md), and [`plan-review-tally.json`](larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-review-tally.json) (`63b53400`). That breaks strict plan-to-diff traceability and ships session/run metadata alongside the skill doc change, which can confuse review (dirty-tree / unrelated churn) unless flushing those paths was an explicit, documented part of this change. **Suggested fix:** Limit the PR to `skills/implement/SKILL.md`, or record the extra paths in the plan and justify the flush commit as required deliverable.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## **Latent** (`correctness`) — [`skills/implement/SKILL.md:60-60`](skills/implement/SKILL.md):60 — NEVER #13’s “How to apply” lists `cat`, `printf`, `echo`, and the Write tool only. Other orchestrator-driven mutations (`sed -i`, `tee`, Python one-liners, patch tools) could recreate the file while satisfying the literal list. **Suggested fix:** Forbid any orchestrator-initiated create/overwrite of that path regardless of tool.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent** (`correctness`) — [`skills/implement/SKILL.md:60-60`](skills/implement/SKILL.md):60 — NEVER #13’s “How to apply” lists `cat`, `printf`, `echo`, and the Write tool only. Other orchestrator-driven mutations (`sed -i`, `tee`, Python one-liners, patch tools) could recreate the file while satisfying the literal list. **Suggested fix:** Forbid any orchestrator-initiated create/overwrite of that path regardless of tool.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## **Plan coverage:** NEVER #13 after #12, Step 18 cross-reference before the `implement-finalize.sh teardown` bash block, and the requested substance (atomic `write_finalize_state()`, no shell/Write reconstruction, surface `state-file missing required key` and stop, no prompt-side improvisation) are all present in [`skills/implement/SKILL.md`](skills/implement/SKILL.md). The twenty names in NEVER #13 match the twenty `printf` assignments in [`scripts/ship-pr.sh`](scripts/ship-pr.sh) lines 388–407.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## **TSV (not written to disk; paste into `diff.txt.tsv` if your pipeline needs a sidecar):**

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## **TSV sidecar** (copy to `diff.txt.tsv` or equivalent; read-only session could not create the file on disk):

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## ---

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	correctness	skills/implement/SKILL.md:60	NEVER #13 ties teardown failure to all 20 keys and missing-key cascade	implement-finalize.sh require_state_keys only lists 17 keys; missing STALL_STEP RUN_ID EXPECTED_SESSION_ID EXPECTED_TMPDIR_BASENAME_PREFIX NO_LOGS_COMMIT can slip past validation; cited cascade misstates mechanics.	Align NEVER text with require_state_keys or expand the validator to the full 20-key contract.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/manifest.json larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-goals-test.md larch-logs/implement/0D35AD07-8E94-4089-AD57-E0911A2267C0/plan-review-tally.json	Committed files not listed under the implementation plan Files to modify (plan scoped skills/implement/SKILL.md only).	Plan fidelity and PR focus suffer: reviewers must separate intentional SKILL.md policy from implement run artifacts committed in the same branch.	Omit larch-logs changes from the PR or amend the plan to explicitly require the larch-logs flush and why.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: important	risk-integration	skills/implement/SKILL.md:1900	Step 18 prose claims finalize-state.sh was written by ship-pr.sh	On --design-only success ship-pr never runs (SKILL.md skips Steps 8+) but teardown still passes --state-file to that path; implement-finalize.sh requires the file to exist; NEVER #13 blocks orchestrator synthesis; misleading text hides the real failure mode and risks abandoned tmpdirs.	Qualify when ship-pr writes the file; for paths that skip Step 8+ document or implement a blessed non-orchestrator writer before teardown.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## 1

- **Reviewer**: in_scope
- **Concern**: latent	correctness	skills/implement/SKILL.md:60	NEVER #13 tool enumeration for forbidden writes	Orchestrator could use sed tee python etc. not named in NEVER #13 while still violating intent.	Forbid any orchestrator write path to that file not only named tools.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## 1

- **Reviewer**: out_of_scope
- **Concern**: nit	architecture	skills/implement/SKILL.md:1745	Step 16 gate text assumes ship-pr PHASE=done	Conflicts with design-only path that skips ship-pr entirely; pre-existing doc tension.	Reconcile Step 16 header with design-only matrix in a follow-up PR.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## Plan items checked against the diff and `scripts/ship-pr.sh` / `scripts/implement-finalize.sh` (read-only).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## Reviewed the precomputed diff and verified claims against [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (`write_finalize_state`, ~384–408) and [`scripts/implement-finalize.sh`](scripts/implement-finalize.sh) (`validate_common_state_args`, `require_state_keys`, `run_teardown`). Read-only mode prevents writing a `.tsv` file on disk; the TSV block below is the structured sidecar content to save manually if needed.

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Gathering the branch diff and commit list for a read-only edge-case review. We won't write files (HARD CONSTRAINTS conflict with the TSV sidecar); we'll include TSV records in the response.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Gathering the branch diff and commit list for a plan-fidelity review (read-only).
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## Verifying NEVER #13's claims against `ship-pr.sh` and teardown behavior for edge cases (paths without postmerge, missing state file).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## Verifying the 20 listed keys against `write_finalize_state()` in the codebase (read-only).

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## [OUT_OF_SCOPE] **Nit** (`architecture`) — [`skills/implement/SKILL.md:1745`](skills/implement/SKILL.md):1745 — “Continue to Step 16 after ship-pr reaches `PHASE=done`” sits beside flows (e.g. design-only → Step 16 → Step 18) that never invoke `ship-pr.sh`; the sentence predates this hunk but still contradicts the design-only matrix. **Why out of scope:** Not changed in the reviewed diff.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Nit** (`architecture`) — [`skills/implement/SKILL.md:1745`](skills/implement/SKILL.md):1745 — “Continue to Step 16 after ship-pr reaches `PHASE=done`” sits beside flows (e.g. design-only → Step 16 → Step 18) that never invoke `ship-pr.sh`; the sentence predates this hunk but still contradicts the design-only matrix. **Why out of scope:** Not changed in the reviewed diff.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## [OUT_OF_SCOPE] Reviewer finding

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: None.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## ```

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## ```text

- **Reviewer**: 
- **Concern**: 
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## schema_version

- **Reviewer**: scope
- **Concern**: severity	focus_area	location	what	scenario_or_breakage	suggested_fix
- **Suggested revision**: Address the concern above.

