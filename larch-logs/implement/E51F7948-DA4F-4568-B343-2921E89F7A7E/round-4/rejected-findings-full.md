### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/dispatch-plan-review-panel.sh:89-145 and skills/design/scripts/decompose-panel-dispatch.sh:136-204
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Parallel both-absent generic-Claude launch blocks with divergent prompt assembly and validation. Fixing TSV/sentinel handling on one path (e.g. plan-review validate-research-output) without updating the other leaves inconsistent degraded floors and panel contracts. Extract a shared helper or enforce one canonical pattern both scripts call.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: skills/design/scripts/test-dispatch-plan-review-panel.sh:43-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stubs still emit removed PHASE2_RELAUNCH_COUNT KV. Downstream code that still requires PHASE2_RELAUNCH_COUNT will not fail harnesses that mimic production stdout shape. Align stubs with production KVs or add assertion that dispatcher omits PHASE2_RELAUNCH_COUNT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Removed `reuse_slot_result` / `cp` impersonation** — eliminates copies without `.done` sentinels (prior ~31 min `SENTINEL_TIMEOUT` stalls) and stops treating one external opinion as two independent reviewers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Removed `reuse_slot_result` / `cp` impersonation** — eliminates copies without `.done` sentinels (prior ~31 min `SENTINEL_TIMEOUT` stalls) and stops treating one external opinion as two independent reviewers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **`--no-fallback` paths-file contract** — only successful slot outputs are listed; collectors no longer wait on ghost paths. Newline checks on manifest `output` paths remain (`dispatch-with-waterfall.sh` ~117–120, 451–458).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--no-fallback` paths-file contract** — only successful slot outputs are listed; collectors no longer wait on ghost paths. Newline checks on manifest `output` paths remain (`dispatch-with-waterfall.sh` ~117–120, 451–458).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Manifest construction** — plan-review/decompose use `jq -nc --arg` for NDJSON rows (safe escaping). Slot validation still restricts `tool` to `codex|cursor` and requires string-typed paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Manifest construction** — plan-review/decompose use `jq -nc --arg` for NDJSON rows (safe escaping). Slot validation still restricts `tool` to `codex|cursor` and requires string-typed paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **`degraded-tools-gate.sh` env fallback** — values pass through `norm_bool` / `norm_tristate`; flags override env; gate is a **detector only** (does not choose which tools launch). Aligns warnings with `session-setup` exports; not a bypass of `--codex-present` / `--cursor-present` on dispatchers.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`degraded-tools-gate.sh` env fallback** — values pass through `norm_bool` / `norm_tristate`; flags override env; gate is a **detector only** (does not choose which tools launch). Aligns warnings with `session-setup` exports; not a bypass of `--codex-present` / `--cursor-present` on dispatchers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **`write-design-current-env.sh`** — still uses `printf '%q'` for sourced env; session-id/repo/pid validation unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`write-design-current-env.sh`** — still uses `printf '%q'` for sourced env; session-id/repo/pid validation unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **No new secrets, `eval` on untrusted input, or shell-outs with unquoted external data** in the changed dispatch paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new secrets, `eval` on untrusted input, or shell-outs with unquoted external data** in the changed dispatch paths. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/decompose-panel-dispatch.sh:144-148
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Generic decompose prompt uses sed anchored on "Your focus:" plus head -n 8. Template edits that move or rename that section break the combined prompt without test failure until runtime. Build generic prompt from render_prompt per archetype or add template-structure harness assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: architecture: scripts/dispatch-with-waterfall.sh:411-427
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] dispatch_ok not cleared when only dynamic slots exist and all fail under --no-fallback. Hypothetical dynamic-only manifest: ALL_SLOTS_DROPPED with DISPATCH_OK=true yields inconsistent soft vs hard failure vs static-only total drop. Set dispatch_ok=false whenever all_output_files is empty and slot_count > 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:104,226
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Generic and waterfall first-line ERE patterns differ. Output accepted on both-absent floor could be dropped on single-vendor waterfall for the same bytes. Unify first-line pattern constant across both paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/plan-review-loop.sh:813-821 and skills/design/scripts/dispatch-plan-review-panel.sh:262-268
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] COMBINED_FALLBACK_COUNT > floor_half degradation heuristic is inert for --no-fallback design panels. Operators or maintainers may believe Claude/cross-tool padding fired when only slot drops occurred. Remove or scope fallback-count degradation to legacy multi-phase callers only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_4: code-quality: scripts/dispatch-with-waterfall.sh:463-471
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate if/else branches when assembling ALL_OUTPUT_FILES. Minor maintenance noise; no functional regression identified. Unify loops with a single empty-path skip.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: correctness: skills/design/scripts/dispatch-plan-review-panel.sh:96-102
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Both-absent generic prompt uses only head -n 1 per archetype plus one shared tail, not full per-lens render bodies. Externals both down on HARD plan: single Claude reviewer gets thinner lens guidance than five separate reviewers; may under-report findings but does not stall. Expand generic prompt to full per-archetype bodies or document compressed floor as intentional.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: scripts/test-dispatch-with-waterfall.sh:76-96
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead cp stub remains after grouped-reuse tests removed. Maintainers may reintroduce or debug cp-fail reuse paths that no longer exist in production; stub adds noise with zero assertions. Remove unused cp stub and related env knobs unless a new ungrouped phase-2 test needs them.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

