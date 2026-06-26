### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:106-107
- **Concern**: `fixture_plan` empty fallback points at committed `larch-logs/implement/<RUN_ID>/` plan artifacts, but the repo ships zero `plan.txt` under implement run logs. Scenario: An implementer leaves `fixture_plan` empty expecting run-log discovery; replay cannot load plan context, `dispatch-voters` runs without the bounded plan the historical vote used, and the acceptance before/after comparison is invalid
- **Proposed resolution**: Require every manifest row to name a committed `fixture_plan` path (under `python/test_fixtures/plan-fidelity-calibration/plans/`) or hard-fail reconstruction; drop the larch-logs empty fallback from the manifest column contract and MAY_UPDATE steps

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:103-108
- **Concern**: Acceptance replay needs committed ballot/plan/diff fixtures, but firm Files lists only `manifest.tsv` as NEW under `python/test_fixtures/plan-fidelity-calibration/`. Scenario: The zero hard-replay-failure criterion needs per-row frozen ballots (truncation/heading cases), plans, and often diffs; an implementer can merge prompt fixes plus an empty manifest without the companion-issue fixture tree and still claim calibration pass
- **Proposed resolution**: Add firm `### NEW:` entries for the manifest-bound fixture tree (`ballots/*.ballot.txt`, `plans/*.txt`, optional `diffs/*`) or state in Testing strategy that every manifest row must have those files committed before merge and list them explicitly in Files

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:157-157
- **Concern**: Calibration replay hardcodes `--round-num 1` and never seeds `findings-ledger.tsv`, so round 2+ cohort rows cannot match production voter prompts. Scenario: Production round 2+ `render voter` judge prompts include prior-round ledger rows from the session parent (`python/findings_ledger.py` via `agent_voters.py`); replay always uses a fresh tmpdir, empty ledger, and `--round-num 1`, changing plan-fidelity context for any labeled row with `round_num>1`
- **Proposed resolution**: Pass each manifest row's `round_num` into dispatch; for `round_num>1`, rebuild and inject a frozen ledger (from committed `findings-classification.tsv` / classification history for prior rounds) before `agent dispatch-voters`, or restrict the manifest cohort to round 1 only and document that restriction in the manifest header

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_fixtures/plan-fidelity-calibration/manifest.tsv:106
- **Concern**: Manifest allows empty fixture_plan to load a committed implement-run plan artifact, but none exist. Scenario: `glob **/plan.txt` under `larch-logs/implement/` returns zero files. A row with empty `fixture_plan` cannot assemble replay inputs from run dirs alone, so acceptance replay hard-fails or forces ad hoc out-of-band plan sourcing.
- **Proposed resolution**: Require non-empty `fixture_plan` for every manifest row (committed path under `python/test_fixtures/plan-fidelity-calibration/plans/`). Drop the empty fallback to `larch-logs/implement/<RUN_ID>/`; hard-fail manifest validation when `fixture_plan` is missing.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:150-157
- **Concern**: Production-parity replay treats --diff-file as optional while committed implement logs ship no diff artifacts. Scenario: `review_pipeline.py` passes `--diff-file` whenever a diff exists at Step 5 (`2349-2350`), but committed implement run dirs contain zero diff files. Plan-mandated missing-deliverable ballots need diff context to verify omission; replay without the historical diff changes voter prompts and invalidates before/after YES-rate comparison.
- **Proposed resolution**: Require non-empty `fixture_diff` per manifest row (or hard-fail the row when absent). Remove optional `--diff-file` language from the acceptance replay contract; document that every cohort row must ship a frozen diff fixture because run logs do not retain one.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_voters.py:171-172
- **Concern**: Calibration replay cannot restore findings-ledger judge context for round_num>1 cohort rows. Scenario: Production voters always receive a `findings-ledger.tsv` section when the ledger file exists (`rendering.py` `1148`, `findings_ledger.prompt_section`). Committed implement logs contain zero `findings-ledger.tsv` files, and the plan never seeds ledger fixtures. Multi-round labeled rows that were re-raised saw duplicate-suppression judge rules in production; replay with an empty ledger changes prompts and can inflate plan-fidelity YES versus the historical baseline.
- **Proposed resolution**: Add `fixture_ledger` to the manifest (or restrict the cohort to `round_num=1` only). Before `dispatch-voters`, copy the frozen ledger into the replay tmpdir ledger root when `round_num>1`; hard-fail rows that need ledger context but lack a fixture.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:106-107,150
- **Concern**: Committed implement run logs expose plan-goals-test.md, not plan.txt, but fixture assembly still names plan.txt and leaves fixture_plan empty to read a generic committed plan artifact. larch-logs/implement contains zero plan.txt files.. Scenario: An implementer following empty fixture_plan reads a non-existent plan.txt from the source run dir, or passes the wrong file shape (Goal wrapper plus Implementation Plan header) versus production plan.txt that voters actually saw. Acceptance replay hard-fails or measures prompt changes against the wrong plan context.
- **Proposed resolution**: Name the committed artifact explicitly as plan-goals-test.md (or require non-empty fixture_plan for every manifest row). Add a helper step to extract the Implementation Plan body when using plan-goals-test.md, and hard-fail when no readable plan fixture exists.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:106,157,230
- **Concern**: Production-parity replay treats fixture_diff as optional, but committed implement logs ship no diff artifact and Step 5 always passes --diff-file when a diff exists.. Scenario: Plan-mandated missing-deliverable ballots depend on diff context to verify omission. After-rate replay without the historical diff changes voter prompts versus the baseline v2_vote rows, so measured YES-rate deltas are not comparable.
- **Proposed resolution**: Require non-empty fixture_diff for every manifest row (committed under python/test_fixtures/plan-fidelity-calibration/diffs/). Hard-fail replay when a row lacks a frozen diff; do not treat --diff-file as optional for acceptance-criterion rows.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:157,224-232
- **Concern**: findings-ledger.tsv is never committed under larch-logs/implement, yet production round 2+ plan-fidelity voters receive Prior-round findings ledger judge context via dispatch-voters while replay always uses a fresh review_tmpdir with --round-num 1 and no ledger seeding.. Scenario: Round 2+ cohort rows in the labeled set voted under ledger rules (for example vote NO on rejected or neutral duplicates) that replay cannot reconstruct from committed artifacts. Before/after YES-rate comparison confounds rubric changes with missing ledger context.
- **Proposed resolution**: Constrain manifest.tsv to round_num=1 findings only, or add per-row fixture_ledger paths and copy them into review_tmpdir/findings-ledger.tsv before dispatch. Document that round 2+ rows are out of cohort unless a frozen ledger fixture exists; hard-fail otherwise.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:91-101,184-185
- **Concern**: Jsonl ballot fallback rebuilds from review-findings-full.jsonl prose_body, which compose_review.py caps at 2000 characters and stores with ## title headings and proposer attribution, not the post-prune neutralized ### FINDING_N ballot voters saw.. Scenario: The plan adds a 2000-char truncation hard-fail and heading normalization, but leaves ambiguous normalization as a silent best-effort path. Borderline plan-mandated findings can replay with shortened or differently shaped ballot text and produce YES/NO shifts unrelated to the rubric fix.
- **Proposed resolution**: Require committed fixture_ballot for every cohort row where jsonl prose_body length is >= 1900, heading normalization is non-trivial, or the source round is > 1. Treat helper jsonl reconstruction as test-only unless fixture_ballot is present; fail the acceptance criterion row instead of counting a vote.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:106-107
- **Concern**: Manifest allows empty fixture_plan and fixture_diff with fallback to committed larch-logs run artifacts, but the repo ships zero implement plan.txt or diff files under larch-logs/implement. Scenario: An implementer can leave fixture_plan and fixture_diff empty per the manifest schema, then follow steps 4 and 150 to read plan/diff from larch-logs/implement/<RUN_ID>/; those paths do not exist (verified: 0 plan.txt and 0 diff artifacts in larch-logs/implement). Required before-merge acceptance replay hard-fails or cannot assemble production-parity inputs even when ballot reconstruction succeeds
- **Proposed resolution**: Require non-empty fixture_plan for every manifest row (committed under python/test_fixtures/plan-fidelity-calibration/plans/). Require non-empty fixture_diff when the source run used diff context in production. Add NEW fixture dirs for plans/ and diffs/ in Files to modify/create. Remove empty fallback to larch-logs plan/diff artifacts or hard-fail manifest rows with empty paths

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:157-158
- **Concern**: Acceptance replay treats --diff-file as optional while implement Step 5 always passes diff to dispatch-voters when a diff exists. Scenario: Plan-mandated missing-test/deliverable findings require diff context to verify the omission. Production dispatch in python/review_pipeline.py passes --diff-file when present; replay without the historical diff changes the plan-fidelity voter prompt and invalidates before/after YES-rate comparison on the labeled cohort
- **Proposed resolution**: Require fixture_diff for cohort rows whose source implement review had diff context. Treat missing diff on those rows as a hard replay failure in Testing strategy and MAY_UPDATE guards, matching ballot reconstruction fail-closed posture

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:35-36
- **Concern**: Rubric update says to follow review-acceptance-rubric.md Update triggers that still mandate direct edits to hand-maintained agents/reviewer-testing.md and agents/reviewer-edge-cases.md, but those paths are excluded from Files and Non-goals. Scenario: Implementers following the rubric's own trigger list either expand PR scope beyond the issue's prompt-only plan-fidelity fix or ship a rubric change whose documented propagation list is knowingly unfulfilled, leaving reviewer-testing pre-rendered bodies on the old default-test-to-OOS gate
- **Proposed resolution**: Add an explicit plan-scoped carve-out in the rubric Update step: for this change, propagate only the listed generated agents and pre-rendered bodies; do not edit hand-maintained reviewer-testing.md or reviewer-edge-cases.md in this PR. Or narrow the rubric Update triggers text in the same edit so it does not contradict Files scope
