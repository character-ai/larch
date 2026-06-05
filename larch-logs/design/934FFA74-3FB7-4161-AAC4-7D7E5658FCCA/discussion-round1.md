# Discussion Round 1 — Issue #3422 (Phase 7: prelude/sentinel turn audit)

## Decision 1: Fold depth for the discussion block (1c, 1d, 1d.5, 1d.7, 1e)
- **Question**: Maximal fold (delete all 5 standalone prelude fences, batch sentinels at the next driver fence) vs one merged fence per step?
- **Resolution**: Maximal fold. Delete all 5 standalone prelude fences; batch the 4 discussion sentinels (step-1c/1d/1d.5/1e) into the existing Step 2a entry fence; one combined timing mark hosted in the existing Step 0c fence. Pause is honored at the next real driver fence; this widened latency is the accepted tradeoff.
- **Source**: user

## Decision 2: Audit scope
- **Question**: Strictly the issue-named pure-LLM steps, or a full audit of all near-empty sentinel-only turns?
- **Resolution**: Full audit. Also fold the remaining prose-directed sentinel-only turns into adjacent existing fences: step-3 → Step 3.5 Gate B fence; step-3.5 → Step 3.6 fence; step-4 → Step 4b emit-preview fence (absorbing 4b's timing-only prelude); step-4b → Step 5 fence; step-5b → first Step 5c fence; step-5d → Step 6 fence; HARD-path step-2a → 2a.5 fence; step-2a.5 → 2b prelude fence.
- **Source**: user

## Decision 3: Timing-ledger granularity
- **Question**: Replacement for the 5 per-step timing marks of the folded discussion steps?
- **Resolution**: One combined block mark (e.g., `design Steps 1c–1e — discussion block`) emitted from the Step 0c fence. Per-step durations within the discussion block are no longer recorded; document this as the chosen tradeoff.
- **Source**: user

## Decision 4: Fold principle (constraint)
- **Question**: Which sentinel writes are eligible for folding?
- **Resolution**: Only turns whose ONLY payload is prelude/sentinel/timing are folded. Sentinel writes that already share a fence with real work stay put (e.g., in-fence writes for step-2b/2b.5/3.6, the Gate-B-bypass triple-sentinel branch-matrix writes, the Step 3.6 rc=10 Continue write at its decision boundary, and the `.outline-approved` write directed by design-outline.md, which is load-bearing for 1e/2a routing and written only on explicit Approve).
- **Source**: codebase

## Decision 5: Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: (a) The canonical Bash-block prelude blanket rule stays — any ad-hoc Bash during the discussion block still sources env + pause-checks; only guaranteed-near-empty standalone fences are deleted. (b) `assert_bash_fences_have_pause_check` inspects only fences that exist — fence deletion is safe; every surviving/merged fence that sources current-design-env must keep the pause-check line after the source line. (c) Check 21 `assert_step_completion_sentinels` greps each step's section for literal `.completed/step-N` — folded steps keep a section-local prose line naming the folded write site (passes the grep), with conscious harness updates only where needed. (d) `design-pause-save.sh` / `design-pause-load.sh` and `test-design-pause-resume.sh` are untouched: sentinel write SITES move, but the sentinel files, registry, and resume routing logic are unchanged. (e) Batched sentinel writes go AFTER source-env but BEFORE the pause-check in the host fence so a pause honored there resumes at the host step, not by re-running the already-completed discussion.
- **Source**: codebase

## Decision 6: Resume-granularity note
- **Question**: Does batching discussion sentinels at 2a regress pause/resume?
- **Resolution**: No regression for pause: with no Bash boundaries inside the discussion block, a pause request can only be honored at the 2a fence, by which point the discussion genuinely completed (sentinels written before the pause-check fires). 1d.7 remains sentinel-less by design (resume router via `.outline-approved` + entry guards).
- **Source**: codebase
