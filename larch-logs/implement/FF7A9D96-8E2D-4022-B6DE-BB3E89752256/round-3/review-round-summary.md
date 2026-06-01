# Review Round 3

- Mode: `diff`
- 14 accepted, 15 rejected (10 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract doc omits ndjson discovery semantics including round-2 stale-RUN_ID no-fallback rule. A maintainer restores inline find-when-keyed-path-missing behavior believing the doc is complete; foreign ndjson could bind again or tests/harness drift from runtime. Add Ndjson discovery subsection documenting RUN_ID-keyed path find-only-when-session-id-empty ambiguity precondition and stale-RUN_ID exit 2.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Ndjson find fallback is skipped when session-id is set, unlike main inline block. Stale RUN_ID run-missing plus sole foreign-run/oos-issues.ndjson: old find binds foreign ndjson and gate may exit 0; new exits 2 via precondition. Document intentional rule or restore inline find when keyed path missing if 1:1 port is required.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract omits ndjson discovery (RUN_ID-keyed vs find-only-without-session-id). Operators/readers infer 1:1 from former inline; miss stale-RUN_ID behavior. Add Ndjson discovery subsection matching script lines 125-138.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:130-138
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Find fallback runs only when RUN_ID is empty; inline ran find whenever keyed ndjson path was missing. Stale session-id with one foreign oos-issues.ndjson: inline could pass; helper exits 2 at precondition and blocks OOS_PENDING clear. Restore inline find when keyed path missing or document intentional tightening and add explicit harness for both behaviors.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.md:16-22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract omits ndjson discovery semantics now encoded in script and tests. Operators/readers rely on code or tests for RUN_ID vs find rules. Document ndjson discovery in checkpoint.md.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Find fallback gated on empty RUN_ID diverges from removed inline block that find-fallbacks whenever keyed ndjson path is missing. Present session-id with missing keyed file plus exactly one foreign ndjson: inline would bind foreign file; checkpoint exits 2 via precondition (harness stale RUN_ID case). Document intentional tightening in checkpoint.md or restore inline-equivalent find if byte parity is required.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/implement/SKILL.md:1187,1196-1202
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SKILL promises 126/127 and other non-0/1/2 checkpoint failures are logged under step-8-oos-checkpoint-validation, but direct executable invocation can fail before the helper runs. Missing +x or unset CLAUDE_PLUGIN_ROOT yields 126/127 with no Tool Failures row; OOS_PENDING stays set and Step 8+ stops without the documented audit entry. Invoke via bash on the script path and/or add orchestrator-side append-tool-failure for 126/127 when no checkpoint log line exists; align SKILL prose.
- **Suggested revision**: Address the concern above.


### FINDING_28: code-quality: skills/implement/scripts/oos-disposition-checkpoint.md:48-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] checkpoint.md still states wiring matches the former inline block after ndjson discovery changed in round 2. Future edits may re-port inline find-when-keyed-missing behavior believing docs. Add Ndjson resolution subsection and qualify or remove the matches-inline claim.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant compound condition in find branch when RUN_ID is empty. Readability noise; future edits may misread which branch is load-bearing. Collapse to if [ -z "$_RUN_ID" ]; then before find.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/implement/scripts/oos-disposition-checkpoint.sh:130-138
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Find fallback gated on empty RUN_ID breaks 1:1 inline ndjson discovery. session-id points at missing path but one other oos-issues.ndjson exists with valid rejection data: inline could pass checkpoint; helper exits 2 and blocks OOS_PENDING clear. Restore inline find-when-keyed-path-missing logic (keep ambiguity exit 2 only for empty RUN_ID + multiple matches) or update plan/docs/tests to codify intentional stale-RUN_ID strictness.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/implement/scripts/oos-disposition-checkpoint.md:48-50
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Gate contract claims wiring still matches former inline block after ndjson behavior change. Readers assume inline-equivalent discovery; mis-triage checkpoint exit 2 vs disposition gap. Document ndjson discovery rules explicitly; qualify or remove matches-inline claim.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: skills/implement/scripts/test-oos-disposition-gate.md:20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Merge-base case doc says proceeds but harness expects exit 1. Misleading harness sibling doc during maintenance. Say range is origin/main..HEAD with disposition-gap exit 1 in harness.
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-138` — Ndjson `find` fallback is gated on `[ -z "$_RUN_ID" ]`, but the removed inline block in `skills/implement/SKILL.md` (diff hunk ~171–184) used `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` with no `RUN_ID` guard, so whenever `session-id` is non-empty and the RUN_ID-keyed file is missing, behavior diverges. **Divergent cases:** (A) `RUN_ID` set, keyed path missing, exactly one other `oos-issues.ndjson` under `larch-logs/implement/` — inline runs `find`, adopts that file, and can pass the gate (e.g. rejection markers in the foreign batch); checkpoint skips `find`, leaves a non-existent keyed path, and with `non_security_oos > 0` hits the precondition at `oos-disposition-checkpoint.sh:160-164` → exit **2** (validation) instead of **0**. (B) Same setup but zero non-security OOS — both tend to exit **0** (checkpoint omits `--oos-issues-ndjson`; inline would still attach the foreign file but the gate still passes). (C) `RUN_ID` empty — keyed path unset/missing, single or multiple `find` hits, ambiguity exit **2** — **equivalent** to inline. (D) `RUN_ID` set, keyed file present — **equivalent**. (E) `RUN_ID` set, keyed missing, multiple ndjson files — inline enters `find` but neither picks nor ambiguous-exits (ambiguity required empty `RUN_ID`); checkpoint does not `find`; both end at precondition exit **2** when non-sec OOS > 0 — **equivalent**. The new behavior is stricter (avoids cross-run ndjson binding) but is **not** the plan’s “1:1 port” / “byte-equivalently” ndjson discovery; acceptance and `oos-disposition-checkpoint.md` only document find-fallback “without `session-id`” (`test-oos-disposition-gate.md:16`), not this RUN_ID-present gap. **Suggested fix:** If parity with inline is required, restore the inline find condition (keep `elif … gt 1 && [ -z "$_RUN_ID" ]` for ambiguity). If the stale-RUN_ID hardening is intentional, document it in `oos-disposition-checkpoint.md` and the plan edge-case list, and call out the acceptance-criteria change explicitly so operators know exit **2** replaces a former silent foreign-batch pickup.
- **Reviewer**: dyn-ndjson-discovery-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/oos-disposition-checkpoint.sh:125-138` — Ndjson `find` fallback is gated on `[ -z "$_RUN_ID" ]`, but the removed inline block in `skills/implement/SKILL.md` (diff hunk ~171–184) used `if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]` with no `RUN_ID` guard, so whenever `session-id` is non-empty and the RUN_ID-keyed file is missing, behavior diverges. **Divergent cases:** (A) `RUN_ID` set, keyed path missing, exactly one other `oos-issues.ndjson` under `larch-logs/implement/` — inline runs `find`, adopts that file, and can pass the gate (e.g. rejection markers in the foreign batch); checkpoint skips `find`, leaves a non-existent keyed path, and with `non_security_oos > 0` hits the precondition at `oos-disposition-checkpoint.sh:160-164` → exit **2** (validation) instead of **0**. (B) Same setup but zero non-security OOS — both tend to exit **0** (checkpoint omits `--oos-issues-ndjson`; inline would still attach the foreign file but the gate still passes). (C) `RUN_ID` empty — keyed path unset/missing, single or multiple `find` hits, ambiguity exit **2** — **equivalent** to inline. (D) `RUN_ID` set, keyed file present — **equivalent**. (E) `RUN_ID` set, keyed missing, multiple ndjson files — inline enters `find` but neither picks nor ambiguous-exits (ambiguity required empty `RUN_ID`); checkpoint does not `find`; both end at precondition exit **2** when non-sec OOS > 0 — **equivalent**. The new behavior is stricter (avoids cross-run ndjson binding) but is **not** the plan’s “1:1 port” / “byte-equivalently” ndjson discovery; acceptance and `oos-disposition-checkpoint.md` only document find-fallback “without `session-id`” (`test-oos-disposition-gate.md:16`), not this RUN_ID-present gap. **Suggested fix:** If parity with inline is required, restore the inline find condition (keep `elif … gt 1 && [ -z "$_RUN_ID" ]` for ambiguity). If the stale-RUN_ID hardening is intentional, document it in `oos-disposition-checkpoint.md` and the plan edge-case list, and call out the acceptance-criteria change explicitly so operators know exit **2** replaces a former silent foreign-batch pickup.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/scripts/test-oos-disposition-gate.md:11-21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness md case list incomplete vs actual checkpoint tests. Contributors rely on md for coverage; missing stale RUN_ID origin/main-absent and design-export cases. Enumerate all checkpoint cases present in test-oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.


