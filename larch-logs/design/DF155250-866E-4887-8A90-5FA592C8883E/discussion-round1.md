## Decision 1: oos-pipeline branch body replacement
- **Question**: What replaces the `:810` oos-pipeline MANDATORY loads?
- **Resolution**: Drop `execution-issues-tracking.md` + `oos-pipeline.md` loads. Replace with slim security-sidecar disposition instruction (stall until SECURITY.md private flow clears the sidecar). Keep `ship-pr-oos-checkpoint-router.md` load — the checkpoint still runs.
- **Source**: issue body + ship.py:1841-1849 confirms only security-sidecar path reaches oos-filing on Python

## Decision 2: trimmed ship-pr-exit-matrix.md sections destination
- **Question**: Where do the 4 trimmed sections go?
- **Resolution**: OOS cap → ship-pr-oos-checkpoint-router.md (specified); steps_ran invariant → ship-pr-oos-checkpoint-router.md (logical home, already oos-branch-only); active-driver notes → trim except conflict-resolution.md MANDATORY READ which moves inline to SKILL.md stall branch; transient-retry authority → trim (logic is Python-owned, no orchestrator action required beyond the reship "Do not sleep" note already in Branch semantics).
- **Source**: issue body "or trim" language, KARPATHY §2 simplicity

## Decision 3: non-security path verification
- **Question**: Could any non-security path reach oos-pipeline on Python path?
- **Resolution**: Confirmed no. ship.py:1841-1849 shows the only condition is security_sidecar.is_file() && .st_size > 0.
- **Source**: codebase grep

## Decision 4: oos-pipeline.md cross-refs in execution-issues-tracking.md
- **Question**: Should references to oos-pipeline.md inside execution-issues-tracking.md be removed?
- **Resolution**: No — those are prose cross-references to the bash-path procedure (Step 9a.1). They remain valid because execution-issues-tracking.md is still loaded for Step 2.4, Step 3 self-review, and Step 5 code review call sites.
- **Source**: codebase analysis
