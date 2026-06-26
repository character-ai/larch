### FINDING_1: Empty `fixture_plan` fallback targets non-existent committed plan artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The manifest and replay steps allow empty `fixture_plan` with fallback to committed `larch-logs/implement/<RUN_ID>/` plan artifacts, but the repo ships zero `plan.txt` under implement run logs (and committed logs expose `plan-goals-test.md`, not production-shaped `plan.txt`). An implementer can leave `fixture_plan` empty expecting run-log discovery; replay cannot load valid plan context, `dispatch-voters` runs without the bounded plan the historical vote used, and before/after acceptance comparison is invalid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require every manifest row to name a committed `fixture_plan` path (under `python/test_fixtures/plan-fidelity-calibration/plans/`) or hard-fail reconstruction; drop the larch-logs empty fallback from the manifest column contract and MAY_UPDATE steps
  - From Cursor-Innovation: Require non-empty `fixture_plan` for every manifest row (committed path under `python/test_fixtures/plan-fidelity-calibration/plans/`). Drop the empty fallback to `larch-logs/implement/<RUN_ID>/`; hard-fail manifest validation when `fixture_plan` is missing.
  - From Cursor-Pragmatic: Name the committed artifact explicitly as plan-goals-test.md (or require non-empty fixture_plan for every manifest row). Add a helper step to extract the Implementation Plan body when using plan-goals-test.md, and hard-fail when no readable plan fixture exists.
  - From Cursor-Requirements: Require non-empty fixture_plan for every manifest row (committed under python/test_fixtures/plan-fidelity-calibration/plans/). Require non-empty fixture_diff when the source run used diff context in production. Add NEW fixture dirs for plans/ and diffs/ in Files to modify/create. Remove empty fallback to larch-logs plan/diff artifacts or hard-fail manifest rows with empty paths

### FINDING_2: Firm Files list omits manifest-bound calibration fixture tree
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Acceptance replay needs committed ballot/plan/diff fixtures, but the firm Files list names only `manifest.tsv` as NEW under `python/test_fixtures/plan-fidelity-calibration/`. The zero hard-replay-failure criterion needs per-row frozen ballots (truncation/heading cases), plans, and often diffs; an implementer can merge prompt fixes plus an empty manifest without the companion fixture tree and still claim calibration pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add firm `### NEW:` entries for the manifest-bound fixture tree (`ballots/*.ballot.txt`, `plans/*.txt`, optional `diffs/*`) or state in Testing strategy that every manifest row must have those files committed before merge and list them explicitly in Files

### FINDING_3: Round 2+ replay omits findings-ledger judge context
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Calibration replay hardcodes `--round-num 1` and never seeds `findings-ledger.tsv`, while production round 2+ `render voter` judge prompts include prior-round ledger rows from the session parent (`python/findings_ledger.py` via `agent_voters.py`; `rendering.py` / `findings_ledger.prompt_section`). Committed implement logs contain zero `findings-ledger.tsv` files. Multi-round labeled rows that were re-raised saw duplicate-suppression judge rules in production; replay with an empty ledger changes prompts and can inflate plan-fidelity YES versus the historical baseline, confounding rubric changes with missing ledger context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass each manifest row's `round_num` into dispatch; for `round_num>1`, rebuild and inject a frozen ledger (from committed `findings-classification.tsv` / classification history for prior rounds) before `agent dispatch-voters`, or restrict the manifest cohort to round 1 only and document that restriction in the manifest header
  - From Cursor-Innovation: Add `fixture_ledger` to the manifest (or restrict the cohort to `round_num=1` only). Before `dispatch-voters`, copy the frozen ledger into the replay tmpdir ledger root when `round_num>1`; hard-fail rows that need ledger context but lack a fixture.
  - From Cursor-Pragmatic: Constrain manifest.tsv to round_num=1 findings only, or add per-row fixture_ledger paths and copy them into review_tmpdir/findings-ledger.tsv before dispatch. Document that round 2+ rows are out of cohort unless a frozen ledger fixture exists; hard-fail otherwise.

### FINDING_4: Optional or missing `fixture_diff` breaks production-parity replay
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Production-parity replay treats `--diff-file` as optional while committed implement logs ship no diff artifacts, yet implement Step 5 passes `--diff-file` whenever a diff exists (`review_pipeline.py`). Plan-mandated missing-deliverable ballots need diff context to verify omission. Replay without the historical diff changes voter prompts versus baseline v2_vote rows, so measured YES-rate deltas are not comparable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require non-empty `fixture_diff` per manifest row (or hard-fail the row when absent). Remove optional `--diff-file` language from the acceptance replay contract; document that every cohort row must ship a frozen diff fixture because run logs do not retain one.
  - From Cursor-Pragmatic: Require non-empty fixture_diff for every manifest row (committed under python/test_fixtures/plan-fidelity-calibration/diffs/). Hard-fail replay when a row lacks a frozen diff; do not treat --diff-file as optional for acceptance-criterion rows.
  - From Cursor-Requirements: Require fixture_diff for cohort rows whose source implement review had diff context. Treat missing diff on those rows as a hard replay failure in Testing strategy and MAY_UPDATE guards, matching ballot reconstruction fail-closed posture

### FINDING_5: Jsonl ballot fallback can diverge from production ballot shape
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Jsonl ballot fallback rebuilds from `review-findings-full.jsonl` `prose_body`, which `compose_review.py` caps at 2000 characters and stores with `##` title headings and proposer attribution, not the post-prune neutralized `### FINDING_N` ballot voters saw. Borderline plan-mandated findings can replay with shortened or differently shaped ballot text and produce YES/NO shifts unrelated to the rubric fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Require committed fixture_ballot for every cohort row where jsonl prose_body length is >= 1900, heading normalization is non-trivial, or the source round is > 1. Treat helper jsonl reconstruction as test-only unless fixture_ballot is present; fail the acceptance criterion row instead of counting a vote.

### FINDING_6: Rubric Update triggers contradict plan Files scope
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: The rubric update says to follow `review-acceptance-rubric.md` Update triggers that still mandate direct edits to hand-maintained `agents/reviewer-testing.md` and `agents/reviewer-edge-cases.md`, but those paths are excluded from Files and Non-goals. Implementers following the rubric's own trigger list either expand PR scope beyond the issue's prompt-only plan-fidelity fix or ship a rubric change whose documented propagation list is knowingly unfulfilled, leaving reviewer-testing pre-rendered bodies on the old default-test-to-OOS gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit plan-scoped carve-out in the rubric Update step: for this change, propagate only the listed generated agents and pre-rendered bodies; do not edit hand-maintained reviewer-testing.md or reviewer-edge-cases.md in this PR. Or narrow the rubric Update triggers text in the same edit so it does not contradict Files scope

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:15-20,49-89
- **Concern**: [SCOPE-REDUCTION] The plan widens a voter-precision fix into proposer-side rubric edits and regeneration of three unrelated code-review agent bodies.. Scenario: The feature still ships if this PR stops at `skills/shared/review-acceptance-rubric.md` and `python/rendering.py`; the extra reviewer-template churn adds generated-artifact drift and stale-surface maintenance with no effect on the plan-fidelity voter path.
- **Proposed resolution**: Remove the proposer-side carve-out and the downstream generated-reviewer updates from this change unless they are strictly required for the voter fix.
