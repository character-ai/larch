### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair REJECT structured TSV row: expected 8 tab columns, got 7 REJECT structured TSV row: expected 8 tab columns, got 7 REJECT structured TSV row: expected 8 tab...

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt)

Reading the plan and tracing the cited code paths to validate the proposed changes.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	blocking	correctness	python/review_tally.py:105-125	Implement Step 5 uses per-round `round-N` dirs as `review_tmpdir`, so a ledger at `review_tmpdir/findings-ledger.tsv` does not persist across rounds	Round 1 tally writes `IMPLEMENT_TMPDIR/round-1/findings-ledger.tsv`; round 2 reviewers and judges read `round-2/findings-ledger.tsv` (missing or empty). Cross-round dedup never works for `/implement` Step 5 despite the `round` column. Mirror `reviewer-prune-ledger.tsv` and `_resolve_coder_timing_ledger`: when `_nested_implement_round` is true, append/read `Path(session_env_path).parent / findings-ledger.tsv` (or `IMPLEMENT_TMPDIR`); keep `review_tmpdir` only for standalone `/review`
1	in_scope	blocking	correctness	python/agents.py:3807-3840	Code-review voter prompt dispatch is pinned to `agents.py`, but voters render in `agent_voters.py::_make_voter_prompt_file`	`--findings-ledger-file` never reaches `render voter` on the `/review` and `/implement` Step 5 paths; only specialist prompts in `agents.py` get the ledger. Judges keep re-voting prior duplicates. Wire `--findings-ledger-file` in `agent_voters.py` (and drop the incorrect `agents.py` voter bullet); keep `agents.py` for specialist / Codex sentinel only
1	in_scope	important	correctness	python/agents.py:3924-3948	Codex compact prompt sentinel omits ledger path, but `render_specialist` cache keys will include ledger sha	Reconstruction via `_review_read_codex_prompt_sentinel` replays only sentinel KVs; round 2+ Codex prompts omit the ledger or fail HASH mismatch. Add `FINDINGS_LEDGER_FILE` to `_review_write_codex_prompt_sidecar` and the sentinel branch of `_review_specialist_render_args`
1	in_scope	important	correctness	python/findings_ledger.py:34-71	Plan does not define how `title`, `file_line`, and `reason` are parsed from ballot blocks	Ballots use `### FINDING_N: <title>`, `- **Concern**:`, and `- **Suggested revision**:` (`skills/shared/voting-protocol.md`), not those column names. Ad-hoc parsing will produce empty `file_line`/`reason` and weak dedup. Add a small shared extractor (heading title, first `path:line` via existing `voting` helpers or concern scan, reason from concern or judge NO tail) and unit-test it
1	in_scope	important	correctness	python/review_tally.py:693-747	Ledger `outcome` mapping for OOS items is unspecified	Classification keeps vote `result` (`accepted`/`neutral`/`rejected`) separate from `scope=oos` / `is_oos`. Mapping vote result alone makes accepted OOS rows look like in-scope `accepted`, so judge "do not down-vote accepted duplicate" can block legitimate OOS re-checks. Rule: `outcome=oos` when `scope=oos` or `is_oos`; otherwise use vote `result`
1	out_of_scope	nit	architecture	python/rendering.py:901-940	[SCOPE-REDUCTION] `render_reviewer_main` is not on the production code-review path	Only `test_rendering.py` calls `render reviewer`; Step 5 uses `render specialist` and `agent_voters` → `render voter`. Adding ledger injection there is dead surface. Limit injection to `render_specialist`, `render_plan_review`, and `render_voter` only
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 3621 bytes)
  ```
### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=8
total_findings=8
total_ballot_items=8
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=b2d368f3fa614c7537051ff41a5621ce3886dda544cccd709a25dd073d117d67
--- first 200 bytes of voter output ---
Votes cast on all 8 ballot items:

| Item | Vote | Key reason |
|------|------|------------|
| FINDING_1 | **YES** | `launch-claude-review --agent-file` (agents.py:5837-5859) builds its own render_arg
  ```
