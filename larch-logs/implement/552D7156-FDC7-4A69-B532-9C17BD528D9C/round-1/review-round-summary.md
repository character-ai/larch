# Review Round 1

- Mode: `diff`
- 6 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Gate B resume idempotency probe uses `-current` while settle writes numeric markers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-settle-contract-output.txt, dyn-prompt-surface-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:710` still probes `.gate-b-postapply-ready-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-current}}`, but `design-step35-settle.sh` derives a validated numeric round (`--round-num`, then `FINAL_ROUND_NUM` → `STEP3_REVIEW_ROUND_NUM` → `ROUND_NUM`) and writes `.gate-b-postapply-ready-N` only. When env round vars are unset or misaligned (including `FINAL_ROUND_NUM` set while probe vars are empty), the orchestrator may look for `.gate-b-postapply-ready-current` while the wrapper wrote `.gate-b-postapply-ready-<N>`, breaking idempotency skip and risking double application of accepted findings; legacy `-current` with unset round can also stall resume when settle exits 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace :-current probe with the same numeric derivation as the settle wrapper; fail closed when round is empty or non-numeric.
  - From cursor-specialist-edge-cases-output.txt: Remove current fallback from prose or add legacy current mapping in design_settle_resolve_gate_b_round.
  - From cursor-specialist-testing-output.txt: Align the SKILL idempotency path with the wrapper round derivation (include FINAL_ROUND_NUM drop current fail closed on non-numeric round) and add a harness case for env-only round binding.
  - From dyn-settle-contract-output.txt: Replace the `:-current` probe with the same numeric derivation the wrapper uses (including `FINAL_ROUND_NUM`), and fail closed when the round is empty or non-numeric before checking the marker.
  - From dyn-prompt-surface-output.txt: Replace the `:-current` probe with the same numeric derivation as the settle wrapper (`FINAL_ROUND_NUM` → `STEP3_REVIEW_ROUND_NUM` → `ROUND_NUM`), fail closed when the round is empty or non-numeric, and add a structure-harness pin that rejects `:-current` in Gate B marker prose.


### FINDING_10: Validator-failure retry paths in `SKILL.md` bypass settle wrapper
- **Reviewer(s)**: dyn-prompt-surface-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:926-931` still directs Gate B and discussion-round2 validator retries through raw `design-step2b-postplan.sh` or `design-postplan-emit.sh --with-plan-size`. Post-rewrite work for those sites now routes through `design-step35-settle.sh`, which owns dedup, apply-ready markers, phase writes, and `POSTPLAN_RC` parsing. Bypassing settle on retry can skip dedup, write wrong phase markers, or leave Gate B resume state inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-surface-output.txt: Update both branches so Gate B re-enters `design-step35-settle.sh --site gate-b` (with `--round-num` when bound), Gate A/discussion re-enter `--site gate-a` or `--site discussion-round2`, and only Step 2b retains direct `design-step2b-postplan.sh` / `design-postplan-emit.sh` retry paths.


### FINDING_2: Settle wrapper lacks explicit `POSTPLAN_RC=11` pause boundary handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-settle-contract-output.txt
- **Severity**: important
- **Concern**: `design-step35-settle.sh:190-238` treats pause only via `PAUSE_OK=true`, `POSTPLAN_EMIT_STATUS=paused`, or `.pause-save-complete`. When `design-step2b-postplan.sh` emits `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save` but pause-save fails or output is truncated, the wrapper falls through to unexpected-rc handling and exits 3 instead of the documented pause boundary rc 11. This regresses the prior `_postplan_rc=11` arm.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add POSTPLAN_RC=11 handling that exits 11 before the unexpected-rc path.
  - From cursor-specialist-edge-cases-output.txt: Treat whole-line POSTPLAN_RC=11 as pause before the POSTPLAN_RC switch.
  - From dyn-settle-contract-output.txt: Treat anchored `POSTPLAN_RC=11` or `POSTPLAN_STATUS=pause-save` as terminal rc `11` (still do not write `awaiting-continuation`), and add harness coverage for failed/truncated pause-save output.


### FINDING_3: Settle wrapper runs dedup and Gate B marker writes before pause check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-settle-contract-output.txt, dyn-prompt-surface-output.txt
- **Severity**: important
- **Concern**: Unlike `design-step35.sh` and `design-step2b-postplan.sh`, `design-step35-settle.sh:121-177` has no `.pause-requested` / `design-pause-save.sh` guard before `gate-b-dedup-plan.sh --dedup` and Gate B phase/apply-ready marker writes. A pause requested between LLM rewrite and settle entry can still mutate `plan.txt` and write partial Gate B state before postplan’s pause gate, breaking pause/resume and idempotency semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add design-pause-save.sh before dedup, matching design-step35.sh.
  - From cursor-specialist-edge-cases-output.txt: Add standard design-pause-save.sh exec immediately after tmpdir validation and before dedup; align with peer generated wrappers.
  - From dyn-settle-contract-output.txt: Add the same upstream `.pause-requested` → `design-pause-save.sh` guard (or an equivalent rc `11` early exit) immediately after tmpdir validation and before dedup/marker work.
  - From dyn-prompt-surface-output.txt: Add the standard wrapper pause-check immediately after tmpdir validation and before dedup, exiting `11` without writing Gate B markers when `.pause-requested` is present; extend `assert_wrapper_pause_before_work` (or equivalent) to cover `design-step35-settle.sh`.


### FINDING_4: `test-design-structure.sh` missing Gate B settle pins and anti-pattern guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-prompt-surface-output.txt
- **Severity**: important
- **Concern**: Plan-requested structure harness coverage for the new settle surface is incomplete: no pin for `SKILL.md` Step 3.5 gate-b settle launcher, no guards rejecting bare `design-step35-settle.sh` calls outside `design-run-$PPID.sh` launcher form, and no negative pins for `:-current` / `.gate-b-postapply-ready-current`. Future doc or prompt-side edits can reintroduce mismatched transport or marker probes without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add grep guard rejecting bare settle calls outside launcher-form references.
  - From codex-specialist-correctness-output.txt: Add scoped grep or awk coverage that rejects prompt-side design-step35-settle.sh --site calls unless they include the launcher, with allowlists for inventory and internal mapping prose.
  - From cursor-specialist-edge-cases-output.txt: Add grep negations for bare design-step35-settle.sh in reference files.
  - From cursor-specialist-testing-output.txt: Add contains pin for SKILL.md gate-b settle launcher and grep-fail guards for bare settle calls mirroring existing design-step2b-postplan anti-patterns.
  - From dyn-prompt-surface-output.txt: Add `contains` pins for `SKILL.md` `design-step35-settle.sh --site gate-b`, negative pins for `:-current` / `.gate-b-postapply-ready-current`, and a negative pin for bare settle invocation outside the launcher form.


### FINDING_5: Missing or invalid `POSTPLAN_RC` can relay child rc 1, colliding with dedup revise-again rc 1
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: When postplan emits no `POSTPLAN_RC` (e.g. plan missing final `diff_lines` causes `design-step2b-postplan.sh` to exit 1 without `POSTPLAN_RC`), `design-step35-settle.sh:204-209` relays raw child rc 1. Wrapper rc 1 is reserved for dedup revise-again, so callers retry duplicate/trailer cleanup instead of stopping for postplan repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Map missing or invalid POSTPLAN_RC to rc 3, or otherwise remap child rc 1 away from the dedup-only rc.
  - From codex-specialist-edge-cases-output.txt: Exit 3 for missing or malformed POSTPLAN_RC output, or remap child rc 1 so only dedup failures return wrapper rc 1.
  - From codex-specialist-testing-output.txt: Return rc 3 for missing POSTPLAN_RC contract failures, or remap child rc 1 to 3, and add a seam test.


