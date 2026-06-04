## Decision 1: Adoption scope of --with-plan-size
- **Question**: Adopt the merged --with-plan-size mode at only the initial Step 2b path, or also at Gate B and discussion-round2 re-emit sites?
- **Resolution**: All three prompt-side emit→check-plan-size sites adopt --with-plan-size (initial Step 2b, Gate B §Shared post-apply pipeline, discussion-round2). Realizes the "compounds across review rounds" benefit. Expands scope to approval-gates.md and discussion-rounds.md.
- **Source**: user

## Decision 2: Treatment of rare Step 2b.5 branches on the merged path
- **Question**: Preserve all rare branches (defects, hard-trigger, --partition, soft advisory) or drop the --partition fast-path on initial Step 2b?
- **Resolution**: Preserve all, no behavior change. The merged call surfaces the same routing so the orchestrator fires identical prompts/routes (defects→Fix/Override/Cancel; hard→Split/Cancel[/Override at Gate B]; --partition→direct Split-path; soft mechanical-churn advisory). Only the clean path gets shorter.
- **Source**: user
