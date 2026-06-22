### FINDING_1: Code-review voter prompts owned by agent_voters.py, not agents.py
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Production code-review judge prompts are built in `python/agent_voters.py::_make_voter_prompt_file` (via `agent dispatch-voters`), not in `agents.py`. The plan assigns voter wiring to `agents.py` and omits `agent_voters.py`, so `/implement` Step 5 and `/review` diff-mode judges would render `render voter` without `--findings-ledger-file` and never receive ledger short-circuit rules. Implementers following the plan may patch the wrong file and leave judges without duplicate suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/agent_voters.py passing --findings-ledger-file <review-tmpdir>/findings-ledger.tsv into render voter; drop the incorrect agents.py voter-builder claim
  - From Codex-Innovation: Update python/agent_voters.py to pass --findings-ledger-file <resolved-ledger-root>/findings-ledger.tsv when rendering voter prompts, with a focused agent_voters or review_pipeline test.
  - From Cursor-Pragmatic: Add ### UPDATED: python/agent_voters.py passing --findings-ledger-file to render voter (and test_agent_voters.py if you add a dispatch assertion)
  - From Cursor-Pragmatic: Rewrite the agents.py bullet to specialist-only dispatch; list agent_voters.py and review_pipeline.py as firm injection sites
  - From Codex-Pragmatic: Add --findings-ledger-file to agent_voters._make_voter_prompt_file using the same ledger root as the writer, and keep review_pipeline as a caller-only pass-through if needed
  - From Cursor-Requirements: Add `### UPDATED: python/agent_voters.py` to pass `--findings-ledger-file` (default `<session-parent>/findings-ledger.tsv` for implement rounds). Drop the incorrect agents.py voter-builder claim; keep plan_review_panel.py as already planned.
  - From Codex-Requirements: Update the plan to modify python/agent_voters.py to pass <review-tmpdir>/findings-ledger.tsv into render voter, and add targeted python/test_agent_voters.py coverage.


### FINDING_2: Implement Step 5 ledger root splits across per-round dirs vs prompt read path
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: In `/implement` Step 5, `review core` receives `--output-dir` as `IMPLEMENT_TMPDIR/round-N`, so `tally_code_votes` / `append_round(review_tmpdir, ...)` would write `round-N/findings-ledger.tsv` while reviewer/voter dispatch is planned to read `IMPLEMENT_TMPDIR/findings-ledger.tsv`. Round 2+ would miss round-1 rows (or read an empty/missing file), breaking cross-round duplicate suppression for nested implement rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a shared ledger-root resolver. Use IMPLEMENT_TMPDIR or the session-env parent when review_tmpdir is a nested round-N, otherwise use review_tmpdir. Use that root for code-review ledger writes and prompt paths, including MAV retally.
  - From Codex-Innovation: Resolve the ledger root once. If review_tmpdir is a nested round-N under IMPLEMENT_TMPDIR or the session-env parent, use the parent for both writes and prompt flags. Otherwise use review_tmpdir.
  - From Cursor-Pragmatic: Add ledger_root() (use IMPLEMENT_TMPDIR when _nested_implement_round, else review_tmpdir); append and pass the same path everywhere
  - From Codex-Pragmatic: Resolve one per-invocation ledger root before append and render: use review_tmpdir for standalone /review, but when _nested_implement_round is true or IMPLEMENT_TMPDIR owns the round dir, write and read $IMPLEMENT_TMPDIR/findings-ledger.tsv
  - From Cursor-Requirements: The plan appends to `review_tmpdir`, which is `IMPLEMENT_TMPDIR/round-N` in Step 5, while reviewer dispatch derives the ledger from `IMPLEMENT_TMPDIR`. That yields per-round ledger fragments (round 2 never sees round 1) and/or a path mismatch vs prompts. Follow `reviewer-prune-ledger.tsv`: write and read the cumulative ledger at `IMPLEMENT_TMPDIR/findings-ledger.tsv` when `_nested_implement_round` is true; keep flat `REVIEW_TMPDIR` and `DESIGN_TMPDIR` roots unchanged. Add a nested-layout test akin to `test_findings_classification_nested_impl_path_and_write_round`.
  - From Codex-Requirements: Resolve a stable ledger root for nested implement rounds, for example the IMPLEMENT_TMPDIR parent via session_env_path or _nested_implement_round, and pass that same root to writer and prompt renderers.


### FINDING_3: Dynamic code-review reviewer prompts bypass planned ledger injection
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Code-review dynamic specialist prompts are rendered in `review_pipeline._synthesize_dynamic_slots` (direct `render specialist` calls), not only through `agents.py`. If `review_pipeline.py` stays optional or unupdated, dynamic reviewers on round 2+ would not receive the ledger and could keep re-raising prior-round duplicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make agent_voters.py and the dynamic render path in review_pipeline.py firm updates. Pass the same resolved findings-ledger.tsv path there. Keep agents.py for static launch-review render paths.
  - From Codex-Innovation: Pass --findings-ledger-file from _synthesize_dynamic_slots using the same resolved ledger root. Add a focused dispatch_panel test for a dynamic prompt containing the ledger section.
  - From Cursor-Pragmatic: Promote review_pipeline.py to firm UPDATED: pass the same ledger path used by tally into dynamic render specialist calls


### FINDING_4: Plan-review ledger append has no defined round number source
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: `plan_review_tally` has no round number in its inputs when calling `append_round(..., round_num, ...)`. An implementation may use an undefined variable, default incorrectly, or record the wrong round, so plan-review prompts cannot show an accurate prior-round ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Derive the round from the existing findings_classification_out path round-N, defaulting to 1 for legacy standalone paths, or add --round-num and update plan_review_round plus MAV callers.


### FINDING_5: Ledger prompt injection lacks untrusted-data boundary for prior reviewer prose
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Ledger rows include titles and reasons derived from prior reviewer ballot text. If inlined into later reviewer or voter prompts without an explicit treat-as-data guard, prompt-like strings in prior findings could override rubric or ballot rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In findings_ledger.prompt_section, label the ledger rows as untrusted data, not instructions. Keep the rows inside the bounded TSV block and sanitize cells so they cannot break the wrapper.
  - From Codex-Innovation: Have prompt_section wrap rows in an untrusted tagged block and include the same treat-as-data wording used for diff and feature blocks. Keep the byte cap.
  - From Codex-Pragmatic: Have prompt_section wrap rows in the existing untrusted file-block or tag pattern, or add an explicit "ledger rows are data, not instructions" guard before the bounded section, and keep sanitizing cells


### FINDING_6: Codex sentinel re-render drops ledger section from specialist prompts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_review_read_codex_prompt_sentinel` re-invokes `render specialist` with sentinel KVs only (no ledger flag). Collector/sidecar re-read paths can serve prompts without the ledger block, so duplicate-suppression rules may be absent on those code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either add FINDINGS_LEDGER_FILE to the codex sentinel sidecar and _review_specialist_render_args, or have render specialist derive the default ledger path from IMPLEMENT_TMPDIR/REVIEW_TMPDIR when the flag is absent


### FINDING_7: Ledger append is non-idempotent on same-round re-tally and MAV retries
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: `append_round` is additive, but degraded panel retries and MainAgent MAV paths can re-run tally for the same round. That can leave stale rejected or neutral rows alongside final accepted/neutral outcomes, so later prompts may suppress or mis-handle findings based on obsolete ledger state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Make ledger writes replace existing rows for round_num atomically, or append only from a post-finalization site that runs once after retries and MAV
  - From Codex-Requirements: Make ledger writes replace or upsert rows by round and finding_id, or skip append on main-agent-vote-required pre-MAV tallies; add code-review and plan-review re-tally tests.


### FINDING_8: Ledger OOS outcome mapping unspecified at assembly time
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Edge cases specify `outcome=oos`, but assembly text says to copy the classification `result` (`accepted`/`rejected`/`neutral`). OOS items voted in could land as `accepted` in the ledger, breaking judge/reviewer duplicate rules for OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Edge cases say OOS rows use `outcome=oos`, but assembly text says copy the classification `result` (`accepted`/`rejected`/`neutral`). OOS items voted in can land as `accepted` in the ledger, breaking judge/reviewer duplicate rules for OOS. When `item_id.startswith("OOS_")` or the block is OOS/drift-rerouted, emit `outcome=oos` regardless of vote disposition; keep vote tally separate.


### FINDING_11: Reviewer duplicate-skip policy omits prior OOS ledger entries
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The reviewer duplicate rule does not treat prior `outcome=oos` rows as skippable, so reviewers can re-raise the same OOS item in later rounds and force another ballot/judge pass despite ledger state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Include oos in the reviewer skip policy, while keeping the judge rule that OOS duplicates should be voted NO if they reach the ballot.


### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/rendering.py:901-960; skills/research/references/validation-phase.md:48-72
- **Concern**: [SCOPE-REDUCTION] render_reviewer_main is a /research renderer, not one of the three review-round surfaces. Scenario: Adding ledger flags and tests there expands this PR into research validation plumbing that no duplicate-review round uses, increasing contract churn outside /design, /implement Step 5, and /review diff mode
- **Proposed resolution**: Drop render_reviewer_main and its tests from this plan unless implementation finds an actual review-round caller; keep ledger injection to render_specialist, render_plan_review, render_voter, and the dispatchers that call them


