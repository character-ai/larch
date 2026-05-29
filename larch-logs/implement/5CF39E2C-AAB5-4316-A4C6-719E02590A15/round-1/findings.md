### FINDING_1: code-quality: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] advance_step3_cursor hand-parses plan-review-round-cursor.txt instead of snapshot-plan-round.sh read-cursor If parse_cursor_file semantics change (malformed file, leading zeros, stderr warnings) the harness can still pass while Step 3 entry and assess-plan-round.sh diverge Implement advance via read-cursor + write-cursor matching skills/design/SKILL.md:1026-1039
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-design-structure.sh:843-849
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Six Step 3.6 skip breadcrumbs are not structurally pinned across SKILL.md and approval-gates.md An edit to one skip breadcrumb in SKILL.md can desync approval-gates.md:92 without failing CI until manual review Add contains pins for each ⏩ 3.6 skip literal (or pin the consolidated approval-gates sentence plus SKILL mirrors)
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two-entry case deletes case_tmp while LARCH_DISPATCH_* exports still reference it Appending tests after this block could invoke deleted mock paths Run the case in a subshell or restore $TMP mock exports after rm -rf
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/SKILL.md:1115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] plan-size-trigger|plan-validator-defects prose says before Gate B/3b while also skipping Gate B Operators may think Gate B still runs before the 2b.5 handler completes Say run Step 2b.5 then short-circuit to Step 3b; skip Gate B and Step 3.6
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-assess-plan-round.sh:31-287
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pre-existing repeated mock-dispatch heredocs across cases File was already high-churn before this branch Extract a shared write_assessor_mock helper in a separate refactor
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/design/SKILL.md:955
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Cap breadcrumb text says returning to Gate C while routing is 3b→4→Gate C Pre-existing operator confusion; not introduced by routing fixes Change breadcrumb text only with a coordinated pin update in test-design-structure.sh:86
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cursor helper reads plan-review-round-cursor.txt directly instead of read-cursor If read-cursor normalization diverges from raw file parsing, harness could pass while Step 3 entry mis-advances cursor Call snapshot-plan-round.sh read-cursor and parse ROUND_CURSOR= like SKILL.md does
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 3.5 bypass pin only checks cap-reached prefix Removing panel-failed or tally-error from SKILL.md:1134 blockquote would not fail structure test Pin the full Gate-B-bypass short-circuit list string from SKILL.md:1134
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Case-local LARCH_* mock exports left pointing at deleted case_tmp after rm -rf A test appended after the two-entry case would call missing mock scripts unset or restore LARCH_DISPATCH_PLAN_ASSESSORS_SH and LARCH_BREADCRUMB_MONITOR_SH after the case
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: skills/design/SKILL.md:955
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cap guard printf still says returning to Gate C while routing prose requires Step 3b then Step 4 then Gate C Agent following only the cap warning banner may jump to Gate C and skip diagram/rejected-findings steps Align printf with Step 3b/4/4b wording or add same-clause continuation as approval-gates.md:17
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/design/references/approval-gates.md:61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] SKILL Step 3.5 blockquote includes skipped-cap-reached; approval-gates When line does not Minor doc drift if an implementer keys only on approval-gates bypass list Add TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached to approval-gates bypass list or cross-reference SKILL matrix
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-design-structure.sh:840-849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan acceptance requires six Step 3.6 skip-breadcrumb literals byte-for-byte in SKILL.md and approval-gates.md but structure tests only pin passive-summary and partial Step 3.5 bypass text. An edit rephrases skip breadcrumbs in one file only; make lint and test-design-structure.sh pass while acceptance fails. Add paired contains pins (or a cross-file equality check) for all six ⏩ 3.6 skip breadcrumb literals in both files.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/design/SKILL.md:955,1128
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cap routing prose now goes Step 3b → Step 4 → Gate C while the pinned cap warning still says returning to Gate C. test-design-structure.sh:86 Pinned breadcrumb text can contradict normative routing without any test failure, confusing operators on cap-reached runs. Update breadcrumb and pin together for routing-consistent wording, or add an assertion linking cap prose to the warning text.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Two-entry cursor helper reads plan-review-round-cursor.txt directly instead of snapshot-plan-round.sh read-cursor/write-cursor used in SKILL.md Step 3 entry. Future read-cursor validation or format changes break production while the integration case still passes. Reimplement advance_step3_cursor using read-cursor and write-cursor like SKILL.md:1026-1038.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-design-structure.sh:846-849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 3.5 bypass pins differ between SKILL.md and approval-gates.md and omit skipped-cap-reached from the approval pin. Drift in bypass status lists between files passes CI while Step 3.5 entry exceptions diverge. Pin the identical full Gate-B-bypass status list in both files including skipped-cap-reached if normative.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/SKILL.md:1120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] main-agent-vote-required re-tally state refresh is documented only in prose with no regression harness. Stale .step3-plan-review-result.env or wrong findings-classification round could reach Gate B undetected. Add a small offline fixture asserting re-tally refresh keys and classification path when feasible.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: scripts/test-design-multi-round-integration.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Pre-existing harness does not cover Gate B passive-summary Continue or short-circuit breadcrumb printing. Not introduced by this branch; E2E gap predates/narrows relative to original OOS item 3. Consider future expansion only if full Gate B + Step 3 E2E is desired beyond current plan scope.
- **Suggested revision**: Address the concern above.

### FINDING_18: **No new executable surface in production.** `assess-plan-round.sh` / `snapshot-plan-round.sh` are unchanged. Dispatch paths from KV output remain constrained by existing `assessor_path_valid()` (basename + resolved path must live under `$DESIGN_TMPDIR`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new executable surface in production.** `assess-plan-round.sh` / `snapshot-plan-round.sh` are unchanged. Dispatch paths from KV output remain constrained by existing `assessor_path_valid()` (basename + resolved path must live under `$DESIGN_TMPDIR`).
- **Suggested revision**: Address the concern above.

### FINDING_19: **Trust-boundary prose is strengthened, not weakened.** `ballot.txt` stays explicitly untrusted; `main-agent-vote-required` now documents refreshing `.step3-plan-review-result.env` and round-scoped `--findings-classification-out` before Gate B — reducing stale-state / wrong-round classification risk (workflow integrity).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust-boundary prose is strengthened, not weakened.** `ballot.txt` stays explicitly untrusted; `main-agent-vote-required` now documents refreshing `.step3-plan-review-result.env` and round-scoped `--findings-classification-out` before Gate B — reducing stale-state / wrong-round classification risk (workflow integrity).
- **Suggested revision**: Address the concern above.

### FINDING_20: **New harness code is test-only.** Case-local `mktemp` dir, heredoc mocks, quoted `"$DIR/..."` writes, `workflow_path` fixed to `HARD` via `printf`. No secrets, injection primitives, or network/auth changes.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **New harness code is test-only.** Case-local `mktemp` dir, heredoc mocks, quoted `"$DIR/..."` writes, `workflow_path` fixed to `HARD` via `printf`. No secrets, injection primitives, or network/auth changes.
- **Suggested revision**: Address the concern above.

### FINDING_21: **`LARCH_*` overrides** (`LARCH_DISPATCH_PLAN_ASSESSORS_SH`, etc.) are pre-existing test hooks in `assess-plan-round.sh`; the new case follows the same pattern and runs last before `pass`, so it does not widen production exposure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`LARCH_*` overrides** (`LARCH_DISPATCH_PLAN_ASSESSORS_SH`, etc.) are pre-existing test hooks in `assess-plan-round.sh`; the new case follows the same pattern and runs last before `pass`, so it does not widen production exposure.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/SKILL.md:955
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Cap-hit breadcrumb still says returning to Gate C while routing is Step 3b → Step 4 → Gate C Operator or log triage assumes Gate C is immediate and may skip Step 3b/4 or mis-order recovery Clarify the live printf/normative cap sentence in the same change as routing (or update pin at scripts/test-design-structure.sh:86)
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No structural pins for the six Step 3.6 skip-breadcrumb literals across SKILL.md and approval-gates.md Future edit drops or typos a skip breadcrumb in one file while CI stays green Add paired contains pins for all six ⏩ 3.6 skip literals in test-design-structure.sh
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] advance_step3_cursor reads cursor file directly instead of read-cursor Harness passes while production mishandles malformed cursor files Use snapshot-plan-round.sh read-cursor in the helper and assert ROUND_CURSOR output
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: skills/design/SKILL.md:1120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main-agent re-tally state refresh is prose-only with no mechanical guard Stale .step3-plan-review-result.env or wrong findings-classification.tsv can still reach Gate B Add offline harness asserting --findings-classification-out and refreshed env before Gate B
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Two-entry case leaves LARCH_* exports pointing at deleted case_tmp after rm -rf Future appended harness cases could call deleted mock paths Save/restore LARCH overrides or run integration before global mock mutation
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 3.5 bypass pin only checks cap-reached prefix panel-failed or tally-error could be removed from blockquote without CI failure Pin full Gate-B-bypass list or each bypass status token
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-assess-plan-round.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Two-entry test does not exercise second Step 3 entry or Gate B settle Residual bugs in panel→Gate B→3.6 wiring stay undetected Out of plan scope; consider fuller e2e harness in a follow-up
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SKILL.md Step 3.5 Gate-B-bypass structural pin only matches a prefix, not the full short-circuit set required by the plan. An agent can remove panel-failed, tally-error, or other bypass statuses from skills/design/SKILL.md:1134 while scripts/test-design-structure.sh still passes; Step 3.5/3.6 bypass prose regresses without CI failure. Add a contains pin for the full Gate-B-bypass enumeration in SKILL.md (mirror approval-gates.md:849), including panel-failed and skipped-cap-reached if normative.
- **Suggested revision**: Address the concern above.

