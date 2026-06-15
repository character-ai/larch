### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: code-quality: skills/implement/scripts/step-5-review.sh:24-32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] read_session_key is defined but never called after rehydrate_larch_triplet removal; cap still uses awk. Dead code adds maintenance noise; diverges from the documented session read-key pattern used elsewhere. Remove read_session_key, or use it for LARCH_DYNAMIC_ARCHETYPES_MAX resolution.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: **correctness** `skills/implement/SKILL.md:588-594` — The scripted-loop Step 5 start breadcrumb is deferred until `<task-notification>`, which breaks the step-entry contract. The banner now prints only inside `step-5-review.sh` stdout on an immediate-background fence (`skills/implement/scripts/step-5-review.sh:47`), while anti-halt rules forbid reading child output before notification. Previously, foreground `step-5-entry.sh` returned caps and the orchestrator printed the `🔶` banner before launching the long-running review loop. Operators get no Step 5 start line for the full review duration, and `skills/shared/progress-reporting.md:59` timer semantics (elapsed time from the `🔶` start line) no longer anchor at Step 5 entry. **Suggested fix:** Restore operator-visible timing by having the orchestrator print the same byte-stable banner immediately before the background `step-5-review.sh` call (with shared cap resolution), or document and implement an explicit carve-out for emitting the wrapper’s leading banner before yield; optionally suppress duplicate banner output from the wrapper.
- **Reviewer**: dyn-step5-launcher-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:588-594` — The scripted-loop Step 5 start breadcrumb is deferred until `<task-notification>`, which breaks the step-entry contract. The banner now prints only inside `step-5-review.sh` stdout on an immediate-background fence (`skills/implement/scripts/step-5-review.sh:47`), while anti-halt rules forbid reading child output before notification. Previously, foreground `step-5-entry.sh` returned caps and the orchestrator printed the `🔶` banner before launching the long-running review loop. Operators get no Step 5 start line for the full review duration, and `skills/shared/progress-reporting.md:59` timer semantics (elapsed time from the `🔶` start line) no longer anchor at Step 5 entry. **Suggested fix:** Restore operator-visible timing by having the orchestrator print the same byte-stable banner immediately before the background `step-5-review.sh` call (with shared cap resolution), or document and implement an explicit carve-out for emitting the wrapper’s leading banner before yield; optionally suppress duplicate banner output from the wrapper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: **architecture** `skills/implement/SKILL.md:584-594` — The scripted Step 5 path now emits the only `🔶` start breadcrumb from inside `step-5-review.sh` stdout, but the fence is immediate-background and SKILL.md explicitly waits for `<task-notification>` before parsing child stdout. That removes the prior foreground entry contract (old flow: foreground `step-5-entry.sh` → orchestrator printed banner → background review loop), so operators get no Step 5 start line for the entire review duration even though `skills/shared/progress-reporting.md` requires step-start visibility on entry. **Suggested fix:** Keep the single launcher call, but restore prompt-side step-start timing: either have the orchestrator print the same byte-stable banner immediately before launching `step-5-review.sh`, or split the wrapper into a foreground telemetry/banner fence plus one background review fence, and pin the timing in `scripts/test-implement-structure.sh`.
- **Reviewer**: dyn-prompt-fences-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:584-594` — The scripted Step 5 path now emits the only `🔶` start breadcrumb from inside `step-5-review.sh` stdout, but the fence is immediate-background and SKILL.md explicitly waits for `<task-notification>` before parsing child stdout. That removes the prior foreground entry contract (old flow: foreground `step-5-entry.sh` → orchestrator printed banner → background review loop), so operators get no Step 5 start line for the entire review duration even though `skills/shared/progress-reporting.md` requires step-start visibility on entry. **Suggested fix:** Keep the single launcher call, but restore prompt-side step-start timing: either have the orchestrator print the same byte-stable banner immediately before launching `step-5-review.sh`, or split the wrapper into a foreground telemetry/banner fence plus one background review fence, and pin the timing in `scripts/test-implement-structure.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: **architecture** `scripts/test-implement-fence-shape.sh:54-55` — The fence-shape harness now whitelists one exact self-review command containing `|| true`, which is the first permitted inline shell control operator in new-shape SKILL.md fences. That erodes the “one repo-relative script target, no inline control logic” boundary the harness exists to enforce, and future edits to the telemetry label or argv will silently re-break lint unless the byte-exact exception string is updated in lockstep. **Suggested fix:** Move self-review telemetry into a tiny wrapper such as `skills/implement/scripts/step-5-self-review-entry.sh` (mirroring the scripted launcher pattern) so both Step 5 paths stay one-line fences without a harness carve-out for `|| true`.
- **Reviewer**: dyn-prompt-fences-output.txt
- **Concern**: - **architecture** `scripts/test-implement-fence-shape.sh:54-55` — The fence-shape harness now whitelists one exact self-review command containing `|| true`, which is the first permitted inline shell control operator in new-shape SKILL.md fences. That erodes the “one repo-relative script target, no inline control logic” boundary the harness exists to enforce, and future edits to the telemetry label or argv will silently re-break lint unless the byte-exact exception string is updated in lockstep. **Suggested fix:** Move self-review telemetry into a tiny wrapper such as `skills/implement/scripts/step-5-self-review-entry.sh` (mirroring the scripted launcher pattern) so both Step 5 paths stay one-line fences without a harness carve-out for `|| true`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: correctness: skills/implement/scripts/step-5-review.sh:38-49
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Wrapper resolves session-env-first dynamic archetypes cap but does not forward it to review-and-fix step5 session-env has LARCH_DYNAMIC_ARCHETYPES_MAX=2 and process env has LARCH_DYNAMIC_ARCHETYPES_MAX=9; banner prints cap=2, then python/review_and_fix.py uses env 9 first and stalls preflight Pass --dynamic-archetypes "$dynamic_archetypes_cap" to review-and-fix step5 or export the resolved value before exec
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

