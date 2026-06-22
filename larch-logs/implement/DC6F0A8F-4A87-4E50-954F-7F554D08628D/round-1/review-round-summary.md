# Review Round 1

- Mode: `diff`
- 8 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Dynamic specialists resolve ledger without `session_env_path`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-ledger-roundtrip-output.txt
- **Severity**: important
- **Concern**: `_synthesize_dynamic_slots` (and related dynamic reviewer dispatch) resolves the findings ledger with `findings_ledger.ledger_root(review_tmpdir)` only, without `session_env_path`, while `review_tally.py` and `agent_voters.py` pass both. For nested `/implement` layouts (`IMPLEMENT_TMPDIR/round-N`), when `IMPLEMENT_TMPDIR` is not in the process environment, `ledger_root` falls back to `round-N/` instead of the cumulative implement parent. The tally writer updates `IMPLEMENT_TMPDIR/findings-ledger.tsv`, but dynamic specialists get `--findings-ledger-file` pointing at `round-N/findings-ledger.tsv`, so round 2+ prompts see an empty ledger and duplicate suppression fails for dynamic slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass `session_env_path` from dispatch context into `_synthesize_dynamic_slots` and into `ledger_root(...)`, mirroring `agent_voters._make_voter_prompt_file`; add a nested round-2 test asserting the ledger path is the implement parent.
  - From codex-specialist-correctness-output.txt: Thread `--session-env-path` through the static and dynamic reviewer render paths, and call `findings_ledger.ledger_root(review_tmpdir, session_env_path=session_env_path)` everywhere the ledger path is derived.
  - From codex-specialist-edge-cases-output.txt: Thread session_env_path into _synthesize_dynamic_slots or pass an explicit ledger path.
  - From dyn-dyn-ledger-roundtrip-output.txt: Thread `session_env_path` into `_synthesize_dynamic_slots` and call `findings_ledger.ledger_root(review_tmpdir, session_env_path=session_env_path)`; extend `test_synthesize_dynamic_slots_passes_findings_ledger_file` with a nested `impl/round-2` layout and assert the flag resolves to `impl/findings-ledger.tsv`.


### FINDING_2: Static specialists and Codex sentinel resolve ledger without `session_env_path`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-ledger-roundtrip-output.txt
- **Severity**: important
- **Concern**: Static specialist dispatch (`_review_specialist_render_args`, Codex sentinel emission, `agent launch-review`) resolves the ledger with `ledger_root(Path(args.output).parent)` without `session_env_path`. For nested `/implement` rounds, when `IMPLEMENT_TMPDIR` is unset at render time, static Codex/Cursor specialists read `round-N/findings-ledger.tsv` while tally and voters use `IMPLEMENT_TMPDIR/findings-ledger.tsv`. Round 2+ static specialists and Codex re-renders miss the cumulative ledger that was actually written, so prior findings are invisible and duplicate suppression fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Thread `session_env_path` from launch-review into render args and sentinel KVs; use `ledger_root(..., session_env_path=...)` consistently.
  - From codex-specialist-correctness-output.txt: Thread `--session-env-path` through the static and dynamic reviewer render paths, and call `findings_ledger.ledger_root(review_tmpdir, session_env_path=session_env_path)` everywhere the ledger path is derived.
  - From cursor-specialist-edge-cases-output.txt: Pass session_env_path or explicit ledger path matching tally resolution
  - From codex-specialist-edge-cases-output.txt: Add an explicit ledger-file or session-env argument to launch-review and pass it through agent_waterfall.py.
  - From dyn-dyn-ledger-roundtrip-output.txt: Mirror `python/agent_voters.py:149-150`: pass `session_env_path` into `ledger_root(...)` (read it from launch-review args/env when available), and add a nested-implement test asserting static specialist argv uses `impl/findings-ledger.tsv`, not `impl/round-N/findings-ledger.tsv`.


### FINDING_3: Plan-review MainAgent sole-voter ledger forces `rejected` for accepted findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On the MainAgent sole-voter path (`self.main_agent_voter` set, `eligible == 1`), ledger assembly in `plan_review_tally.py` forces `outcome="rejected"` for every non-`OOS_*` item even when `_tally_votes_for_id` returns `result="accepted"`. That mirrors the pre-existing classification TSV override but violates the plan's duplicate policy ("accepted duplicates: do NOT suppress"). Round 2+ reviewers/judges would treat genuinely accepted plan findings as rejected ledger entries and skip re-raises of incomplete fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `result` (or a dedicated `accepted`/`neutral`/`rejected`/`oos` mapping aligned with artifact routing) for ledger outcomes; keep the provisional TSV override separate if still required.


### FINDING_6: Accepted latent code-review findings written to ledger as `oos`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_ledger_entry` in `review_tally.py` maps every latent-severity in-scope finding to ledger outcome `oos` even when the tally accepted it. A `FINDING_1` with latent severity and enough YES votes is written to `accepted-findings.md`, but the ledger tells later reviewers it was `oos`. Round 2+ reviewers and judges then suppress re-raise of an incomplete accepted fix instead of treating it as an accepted duplicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Do not override accepted results in `_ledger_entry`; derive `oos` only from the caller's actual OOS/scope-drift decision, or apply latent rerouting only to non-accepted outcomes if that behavior is intentional.
  - From cursor-specialist-edge-cases-output.txt: Only emit oos for latent items routed to the OOS track; pass final tally disposition into _ledger_entry
  - From codex-specialist-edge-cases-output.txt: Preserve accepted outcomes; only force oos for actual OOS/drift or non-accepted latent reroutes if intended.
  - From codex-specialist-testing-output.txt: Use the final tally outcome for accepted latent findings, only mark latent as oos on the non-accepted latent-reroute path, and add a regression test.


### FINDING_8: Missing code-review MAV re-tally ledger regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required code-review MainAgent-voter re-tally ledger test is missing. Provisional MAV tallies or stale per-round rows could regress without CI catching it; plan review has this test but code review does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test: MAV → no ledger; final tally writes; re-tally same round replaces rows without duplicates


### FINDING_11: `_sanitize_cell()` does not neutralize triple-backtick fence breakouts
- **Reviewer(s)**: dyn-dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: `_sanitize_cell()` does not neutralize triple-backtick sequences. Ledger rows are inlined inside a markdown code fence; a prior-round `reason` containing a line that is only ` ``` ` can break out of the ` ```tsv ` block and splice untrusted markdown into the trusted prompt tail ahead of the real output-format rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-safety-output.txt: Strip or replace `` ` `` runs (especially triple-backtick) in `_sanitize_cell()`, or stop using an inline markdown fence and emit the ledger through the same XML/redacted wrapper used for diff and scope anchors. Add a unit test that writes a ledger row whose `reason` is `` ``` `` and assert the rendered specialist/voter prompt still has a single intact untrusted block.


### FINDING_12: `_ledger_reason()` fallback copies full ballot bullets into ledger
- **Reviewer(s)**: dyn-dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: `_ledger_reason()` falls back to the first non-empty ballot line when no `Concern:` / `Scenario:` / `Reason:` label matches. Ballot blocks are usually full finding bullets. That entire bullet is copied into the ledger `reason` column and re-injected into later-round reviewer/judge prompts, replaying output-format-shaped text inside "evidence" rows. Round 1 reviewer prose can steer round 2+ behavior even with the short untrusted preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-safety-output.txt: Restrict fallback extraction to labeled fields only; if none exist, omit `reason` or store a capped one-line summary with markdown list markers, focus-area tokens, and `**Suggested fix:**` stripped. Add tally tests where ballot blocks use the standard bullet shape and assert the ledger `reason` column does not contain `**Suggested fix:**` or `### In-Scope Findings`.


### FINDING_14: Ledger assembly path lacks `redact.secrets` pass
- **Reviewer(s)**: dyn-dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: Ledger assembly copies ballot text into ephemeral prompts with no `redact.secrets` pass. `review_tally.py` has no redaction usage on the ledger path, while other prompt surfaces redact before external dispatch. If a prior-round finding mentions tokens, keys, or PII in `Concern`/`reason`, later-round Codex/Cursor prompts can re-broadcast them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-safety-output.txt: Pipe `title`, `file_line`, and `reason` through `redact.redact()` (or `issue_wire.redact_untrusted_stream()`) in `_row_for_entry()` or immediately before `prompt_section()` emission. Add a test with a synthetic `sk-…` substring in a ballot block and assert the injected ledger section contains `<REDACTED-TOKEN>` (or your standard redaction marker).


