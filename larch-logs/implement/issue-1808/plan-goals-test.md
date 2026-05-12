## Goal

Implement a run-depth router that pre-computes run parameters (`sketch_budget`, `review_budget`, `workflow_path`) once into `run-params.json` at orchestrator entry, and adaptive `/design` sketch fan-out (0/2/4 sketches) gated on the SIMPLE classifier. Downstream steps read pre-computed budget values rather than re-reasoning through policy paragraphs each step.
## Implementation Plan: Run-Depth Router + Adaptive Sketch Fan-Out (Revised)

### Objective
Add a run-depth router that pre-computes run parameters to `run-params.json` once at orchestrator entry, and implement adaptive /design sketch fan-out (0/2/4 sketches) based on SIMPLE classifier output. Downstream steps read the pre-computed parameters instead of re-reasoning through policy paragraphs.

### Scope clarification (FINDING_1)
Adaptive sketch fan-out applies to **standalone /design** and to **/implement HARD path** (where /implement invokes /design). The existing /implement SIMPLE auto-switch to inline-plan (skipping /design entirely) is **unchanged**. SIMPLE fan-out (sketch_budget=2) is reachable only from: (a) standalone `design --quick`, (b) `/implement` when `quick_mode=true` is set by `--quick` flag explicitly and the user also invokes `/design` standalone. The plan does NOT change /implement's SIMPLE auto-switch. The feature description's "SIMPLE=2 sketches" refers to `/design --quick` mode alignment.

### Decisions incorporated
- **Discussion-round1 Decision 1 (Router timing)**: The `/implement` router fires after Step 1 plan synthesis (post-/design) reading `plan.txt` for post-plan classification. The `/design` router fires at Step 0 tail after session-setup.sh sets DESIGN_TMPDIR (not before).
- **Discussion-round1 Decision 2 (0-sketch NEVER rule)**: Revise NEVER rule #1 with explicit trivial-task carve-out, requiring codebase scan.
- **Dialectic Decision 2 (Single-source classification)**: `/implement` passes its classification to `/design` via a new `--design-classification` flag (not session-env). Standalone `/design` runs its own router when `--design-classification` is absent.

### `run-params.json` schema — capability budget style (Discussion Round 2 + FINDING_2 + FINDING_8)
```json
{
  "schema_version": 1,
  "design_classification": "TRIVIAL_DOC_ONLY|SIMPLE|HARD",
  "design_classification_reason": "<brief prose>",
  "design_classification_source": "router-pre-design|caller-forwarded",
  "sketch_budget": 0,
  "review_budget": "quick|full",
  "workflow_path": "SIMPLE|HARD"
}
```

Capability budget schema (Discussion Round 2): `sketch_budget` replaces `sketch_count`; `review_budget` replaces `plan_review_mode`. Derived fields (`run_dialectic`, `max_review_rounds`) are NOT stored in the JSON — consumers compute them from budgets:
- `sketch_budget=0` → `run_dialectic=false` (no sketches, no dialectic possible)
- `sketch_budget=2|4` → `run_dialectic=(sketch_budget==4 && no quick_mode)` (derived by consumer)
- `review_budget=quick` → `max_review_rounds=7` quick-mode loop; `review_budget=full` → 4-reviewer panel

Post-plan fields stored separately as `post_plan_workflow_path` in session-env.sh (FINDING_3). No `reviewer_count` field (always derived from `review_budget`).

The file is written exclusively via a new `scripts/write-run-params.sh` helper using `jq -n --arg ...` to safely handle prose content (FINDING_8).

Missing or schema-invalid `run-params.json`: all consumers fall back to HARD defaults.

### `sketch_budget` logic (authoritative, capability budget style)
```
if full_mode=true:
    sketch_budget = 4
elif quick_mode=true:
    sketch_budget = min(classified_budget, 2)  # quick caps at 2
else:
    classification → sketch_budget:
        TRIVIAL_DOC_ONLY → 0 (requires codebase scan to confirm)
        SIMPLE → 2
        HARD → 4
    sketch_budget = classification_budget
```

0-sketch classification (TRIVIAL_DOC_ONLY) requires codebase scan (same ~30 LOC scan as SIMPLE classifier), not text-only classification (FINDING_13). Absent scan capability, default to SIMPLE (sketch_budget=2).

`review_budget` derivation:
- `quick_mode=true` → `review_budget=quick`
- `quick_mode=false` → `review_budget=full`

### Files to modify

**Implementation order respects dependencies:**

**1. `scripts/write-run-params.sh` + `scripts/write-run-params.md` (new, FINDING_8)**
- jq-based writer; accepts `--classification`, `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`, `--output`
- Validates enum values (classification: TRIVIAL_DOC_ONLY|SIMPLE|HARD; review-budget: quick|full; sketch-budget: 0|2|4)
- Returns non-zero on invalid enum; callers fall back to HARD defaults

**2. `skills/design/references/flags.md`**
- Add `--full` flag: "Set `full_mode=true`. Default: `full_mode=false`. Forces `sketch_budget=4` regardless of classification. When `--full` and `--quick` are both set, sketch fan-out uses 4 agents but plan review still uses `plan-review-quick.md` (`quick_mode` governs plan review, not sketch count)."
- Add `--design-classification <value>`: "Caller-forwarded TRIVIAL_DOC_ONLY|SIMPLE|HARD classification from `/implement`. When present, the /design router accepts it without re-classifying. Ignored when supplied via standalone invocation without `--branch-info` (defensive: only trusted when `branch_info_supplied=true`, ensuring a nested /implement context). Default: empty (standalone /design runs its own classification)."

**3. `skills/design/references/sketch-launch.md`**
- Replace binary `quick_mode` dispatch with `sketch_budget` lookup
- Add `sketch_budget=0` block: "Codebase scan confirms TRIVIAL_DOC_ONLY. No external agents launched. Write sentinel artifacts: `approach-synthesis.txt` = `NO_SKETCHES_CLASSIFIED_TRIVIAL`; `contested-decisions.md` = `NO_CONTESTED_DECISIONS`. Skip Step 2a.5. Proceed directly to Step 2b plan synthesis."
- `sketch_budget=2`: existing quick-mode blocks (1 Cursor-Generic + 1 Codex-Generic)
- `sketch_budget=4`: existing regular-mode blocks (2 Cursor + 2 Codex by personality)

**4. `skills/design/references/heavy-worker.md`**
- Required Reads: add reading `$DESIGN_TMPDIR/run-params.json` as step 0 (before sketch launch)
- 0-sketch path: when `sketch_budget=0`, write sentinel artifacts and skip Step 2a.5
- Artifact Contract: add `run-params.json` as internal-only required artifact (NOT exported in manifest, per FINDING_16 resolution — see item 11 below)
- Fallback on absent/invalid run-params.json: default to sketch_budget=4

**5. `skills/design/SKILL.md`**
- Add Step 0 router block: fires after session-setup.sh (after DESIGN_TMPDIR is available, FINDING_6), before Step 1c/1d discussion. Location: "Step 0 tail — after session-setup.sh returns and DESIGN_TMPDIR is confirmed."
  - When `--design-classification <value>` was passed AND `branch_info_supplied=true`: accept forwarded classification, set `design_classification_source=caller-forwarded`
  - Otherwise: classify from FEATURE_DESCRIPTION + codebase scan (LOC estimate)
  - Write `$DESIGN_TMPDIR/run-params.json` via `scripts/write-run-params.sh`
- NEVER rule #1 carve-out: "Exception: when the router classifies TRIVIAL_DOC_ONLY (confirmed by codebase scan), `sketch_budget=0` is permitted. The router must write sentinel stubs (`approach-synthesis.txt` = `NO_SKETCHES_CLASSIFIED_TRIVIAL`, `contested-decisions.md` = `NO_CONTESTED_DECISIONS`) so downstream steps have stable inputs."
- Step 2a dispatch: branch on `sketch_budget` from `run-params.json` (0/2/4)
- Flag table: add `--full` and `--design-classification`

**6. `skills/implement/SKILL.md`**
- **Post-plan router** (at Step 1 tail, after `post-design-boundary.sh` + manifest binding): read `plan.txt` size and file count to derive `post_plan_workflow_path` (SIMPLE or HARD). Write this to session-env.sh as a new key `POST_PLAN_WORKFLOW_PATH`. Do NOT overwrite `design_classification` or `sketch_count` from `run-params.json` (FINDING_3). The post-plan field is separate and consumed only by downstream review/round logic.
- Add `--design-classification <value>` forwarding when invoking /design: pass `--design-classification "$ROUTER_CLASSIFICATION"` in the canonical /design invocation order when classification was pre-computed. Note: current SIMPLE auto-switch to inline plan is unchanged (FINDING_1).
- **Manifest-reuse path** (FINDING_15): when the manifest-reuse fast path fires (reusing prior design manifest), skip router pre-classification and instead read `design_classification` from the reused manifest (or from a co-located `run-params.json` export if present). Do not overwrite a reused classification. Router fires only for new (non-reused) design runs.

**7. `scripts/test-design-structure.sh` + `scripts/test-design-structure.md` (FINDING_7, FINDING_10)**
- Update structural assertions to accept `sketch_budget=0|2|4` section headers
- Add "sketch_budget=0 path: collect-agent-results.sh not called" assertion
- Update output-path sync checks for 2 and 4 paths
- Update sibling .md with behavior changes

**8. `scripts/test-implement-structure.sh` + `scripts/test-implement-structure.md` (FINDING_7, FINDING_10)**
- Accept `run-params.json` as allowed in implement tmpdir
- Update sibling .md

**9. `scripts/write-run-params.sh` tests (part of item 1's sibling .md)**
- Valid enum values, invalid JSON fallback, `--quick/--full` precedence; budget vs direct field name changes

**10. User-facing docs (FINDING_9)**
- `README.md` (flags table for /design): add `--full` flag description
- `docs/workflow-lifecycle.md`: update quick/subagent/full interaction prose
- `skills/shared/subskill-invocation.md`: update /design argument list per its explicit update trigger

**11. `skills/design/scripts/write-design-manifest.sh` (FINDING_16)**
- `run-params.json` is internal-only: it is written by the router and consumed by the same run. It is NOT exported in the manifest. The heavy-worker gate checks it exists (via `-f` check) but does not include it in `copy_required_may_be_empty`.
- Document in `heavy-worker.md` Artifact Contract that `run-params.json` is internal-only.

**12. `skills/shared/topology.tsv` + regenerate `docs/topology.md` (FINDING_11)**
- Update sketch count topology rows to reflect 3-tier (0/2/4)
- Run `bash scripts/generate-topology-docs.sh` after editing the TSV
- Verify `docs/topology.md` changed only from generation (no manual edits)

**13. `docs/collaborative-sketches.md`**
- Update hardcoded 4/2 sketch count references to 3-tier model

### Edge cases and failure modes
- **sketch_budget=0 path artifact stubs**: `approach-synthesis.txt` = `NO_SKETCHES_CLASSIFIED_TRIVIAL`, `contested-decisions.md` = `NO_CONTESTED_DECISIONS`, `dialectic-resolutions.md` = empty file.
- **Absent/invalid `run-params.json`**: all consumers default to HARD (`sketch_budget=4`). No hard gate dependency.
- **`--full` + `--quick`**: `--full` wins for sketch count; `quick_mode=true` still governs plan review.
- **Caller classification trust**: Only trusted when `branch_info_supplied=true` (meaning /design was invoked by /implement with explicit --branch-info). Standalone /design ignores forwarded classification.
- **Manifest-reuse**: router does not pre-classify on the manifest-reuse path; classification is read from the reused context.
- **Post-plan classification**: stored as `POST_PLAN_WORKFLOW_PATH` in session-env, separate from `design_classification`. Does not affect artifacts already written by /design.
- **`collect-agent-results.sh` zero-args guard**: `sketch_budget=0` path does NOT call `collect-agent-results.sh`. NEVER rule #5 preserved.

### Testing strategy
1. Run `make test-design-structure` — verify 0/2/4 sketch path structural assertions pass; verify collector-not-called for 0-sketch.
2. Run `make test-implement-structure` — verify run-params.json allowed in tmpdir.
3. Run `scripts/write-run-params.sh` unit tests (enum validation, jq safety, fallback).
4. Run `bash scripts/generate-topology-docs.sh` and verify docs/topology.md reflects 3-tier.
5. Run `/relevant-checks` (pre-commit + agent-lint) after each file edited.
6. Manual spot checks: `--full` produces `sketch_budget=4`; `--quick` caps at 2; trivial doc task with codebase scan produces `sketch_budget=0`.

### Implementation order
1. `scripts/write-run-params.sh` + `.md` (new shared helper — no deps)
2. `skills/design/references/flags.md` (new flags — no deps)
3. `skills/design/references/sketch-launch.md` (0/2/4 dispatch)
4. `skills/design/references/heavy-worker.md` (consume run-params.json, 0-sketch stubs, internal-only contract)
5. `skills/design/SKILL.md` (router block + NEVER rule carve-out + Step 2a branch + flag table)
6. `skills/implement/SKILL.md` (post-plan router + --design-classification forwarding + manifest-reuse fix)
7. `scripts/test-design-structure.sh` + `.md`
8. `scripts/test-implement-structure.sh` + `.md`
9. `README.md` + `docs/workflow-lifecycle.md` + `skills/shared/subskill-invocation.md`
10. `skills/shared/topology.tsv` → run generator → `docs/topology.md` + `docs/collaborative-sketches.md`

## Test plan

1. `make test-design-structure` — verify `sketch_budget=0/2/4` structural assertions pass; verify collector-not-called for 0-sketch.
2. `make test-implement-structure` — verify `run-params.json` allowed in implement tmpdir.
3. `scripts/write-run-params.sh` unit tests (enum validation, jq safety, fallback).
4. `bash scripts/generate-topology-docs.sh` and verify `docs/topology.md` reflects 3-tier.
5. `/relevant-checks` (pre-commit + agent-lint) after each file edited.
6. Manual spot checks: `--full` produces `sketch_budget=4`; `--quick` caps at 2; trivial doc task with codebase scan produces `sketch_budget=0`.
