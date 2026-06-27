# Review Round 1

- Mode: `diff`
- 3 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 1b empty `FAILED_RUN_ID` is not terminal (steps 2–12 gap)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/implement/references/ship-pr-ci-fix.md:12` routes on empty `FAILED_RUN_ID` but only skips steps 3–12, not step 2. When `NEXT_ACTION=ci-fix` with empty `FAILED_RUN_ID`, `FORKED_TARGET=false`, and `REPO_UNAVAILABLE=false`, an orchestrator that treats 1b as non-terminal can still run step 3 (`main-agent-ci-fix-.attempted`) and step 5 (`gh run-logs --run-id ""`), defeating the intended early exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Make 1b terminal: say “end this procedure” or “skip steps 2–12” after routing to `operator-bail` or post-driver `stall`.


### FINDING_3: NEVER #14 bookkeeping ownership conflicts with pre-driver `oos file` runtime
- **Reviewer(s)**: dyn-dyn-oos-routing-output.txt
- **Severity**: important
- **Concern**: NEVER #14 documents pre-driver `python/cli.py oos file` as the normal-path OOS authority but still says only checkpoint `NEXT_ACTION=reship` may write `run-statistics.md`, stamp the manifest, and clear `OOS_PENDING=false`. That conflicts with NEVER #5 and with `python/oos_filer.py:_after_checkpoint`, which already runs disposition-checkpoint and writes stats/stamps `steps_ran.step9a1` inside pre-driver before any `oos-pipeline` branch. An orchestrator following NEVER #14 literally may treat lawful pre-driver bookkeeping as a violation or attempt to redo it at the checkpoint fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-routing-output.txt: Split bookkeeping ownership explicitly: pre-driver `oos file` owns disposition-checkpoint + stats + manifest stamp for non-security OOS on the normal path; `step-8-oos-checkpoint.sh` owns the same tail only on the `oos-pipeline` security-sidecar path (including `OOS_PENDING=false`). Drop the blanket "Only checkpoint … may write run statistics" wording or scope it to the security branch only.


### FINDING_4: Pre-driver security sidecar can route to `halt-oos` without private-disposition guidance
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: The new security-sidecar procedure is documented only under post-driver `NEXT_ACTION=oos-pipeline` (`skills/implement/SKILL.md:785-810`), but pre-driver can stop earlier with `NEXT_ACTION=halt-oos`: `python/implement_dispatch.py:1629-1633` maps any non-zero `python/cli.py oos file` result to `halt-oos`, and `python/oos_filer.py:811-815` fails when `security-oos-observations.md` is already non-empty. A run with a pre-existing or newly materialized security sidecar can follow the line 787 Tool Failures / Step 18 path and never reach the line 810 private-disposition instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Route the pre-driver security-sidecar case to the same private-disposition flow, either by emitting `NEXT_ACTION=oos-pipeline` for the known security-sidecar status or by adding explicit security-sidecar handling under `halt-oos` before generic Tool Failures routing.


