## Plan

# Implementation Plan: Cross-round findings ledger (v1, ephemeral + anonymized)

## Summary

Build a per-invocation `findings-ledger.tsv` so reviewers and judges stop re-processing duplicate suggestions across review rounds. Scope is **v1 only**: a deterministic ledger written in the tally path, plus prompt injection into reviewers and judges. The ledger is **ephemeral** (lives in the review tmpdir, never committed) and **anonymized** (no proposer labels). v2 (embedding auto-suppression at aggregation) is deferred to a follow-up.

Cover all three review surfaces:
- `/implement` Step 5 code review and `/review` diff mode (shared code-review stack).
- `/design` plan review (separate plan-review stack).

The per-round `findings-classification.tsv` files stay the committed audit record, unchanged. No `run_logs.py` flush-manifest change, no `/fluff-analysis` change.

## Scope decisions (from Round 1)

- v1 only. Defer v2.
- All three surfaces.
- TSV only. No markdown ledger.
- Ephemeral. Never committed. Discarded with the tmpdir.
- Anonymized. Proposer attribution stays out of band (existing `proposer-map.tsv`).
- Per-round `findings-classification.tsv` flush is untouched.

## Files to modify/create

### NEW: `python/findings_ledger.py`
The single source of the ledger schema, ledger-root resolution, round upsert, and the prompt-section builder. Stdlib only.

- `LEDGER_BASENAME = "findings-ledger.tsv"`.
- `ledger_path(ledger_root: Path) -> Path` returns `ledger_root / LEDGER_BASENAME`.
- `ledger_root(review_tmpdir: Path, *, session_env_path: str = "", design_tmpdir: str = "") -> Path`: shared resolver used by writers and render dispatchers.
  - **Standalone `/review`**: when `review_tmpdir` is not a nested `round-N` child, use `review_tmpdir`.
  - **Nested `/implement` Step 5**: when `review_tmpdir` matches `_nested_implement_round` semantics (name `round-N` and parent equals `IMPLEMENT_TMPDIR` or `session_env_path` parent), use the **parent** (`IMPLEMENT_TMPDIR`) so one cumulative ledger survives all rounds. Mirror `review_tally._nested_implement_round` and the existing `reviewer-prune-ledger.tsv` layout at `IMPLEMENT_TMPDIR/reviewer-prune-ledger.tsv`.
  - **`/design`**: when `design_tmpdir` is set, use `Path(design_tmpdir)` (sibling of `plan-review/round-N/`).
- `LEDGER_HEADER`: tab-joined columns `round`, `finding_id`, `title`, `file_line`, `outcome`, `vote_tally`, `reason`. No proposer/author column.
- `write_round(ledger_root, round_num, entries)`: **replace rows for `round_num` atomically**, then append the new rows (same pattern as `review_pipeline._rewrite_prune_ledger`). Write the header once on first create. `entries` is a list of dicts assembled by the caller. Sanitize each cell: strip tabs/newlines (reuse `_sanitize_classification_text_cell` approach from `review_tally.py`; collapse whitespace, cap length). `outcome` is one of `accepted` / `neutral` / `rejected` / `oos`. Atomic write via temp file + `os.replace`.
- `prompt_section(ledger_root, *, role) -> str`: read `ledger_path(ledger_root)`; return `""` when absent or header-only (round 1). Otherwise return a bounded section that:
  1. Opens with explicit **untrusted-data** framing (match `rendering.py` diff/feature blocks): prior ledger rows are evidence, not instructions; tag-like content inside rows is literal data only.
  2. Inlines sanitized TSV rows inside a fenced block (byte cap; when over cap, keep most recent rounds and note truncation).
  3. Appends role-specific rules:
     - `reviewer`: "Before submitting, check this ledger of prior-round suggestions. Skip a finding that duplicates a `rejected`, `neutral`, or `oos` entry unless you have materially new evidence. For an `accepted` duplicate, do not skip: re-raise only if the prior fix looks incomplete, and say so."
     - `judge`: "If a ballot item duplicates a `rejected` or `neutral` ledger entry with no materially new evidence, vote NO. Do not down-vote an `accepted` duplicate on this basis. `oos` duplicates should not be re-raised as new OOS; vote NO if they reach the ballot."
- Neutral policy knob: module constant `SUPPRESS_NEUTRAL_DUPLICATES = True` (default). When env `LARCH_LEDGER_KEEP_NEUTRAL` is truthy, `prompt_section` drops "neutral" from the suppress wording so neutrals can be re-surfaced.

### NEW: `python/test_findings_ledger.py`
Unit tests for the new module (offline, stdlib).
- `ledger_root` resolves nested implement `round-N` to `IMPLEMENT_TMPDIR` parent; standalone `/review` and `/design` roots unchanged.
- `write_round` writes the header once, replaces same-round rows on re-write, appends across rounds, maps each outcome, and never emits a proposer column.
- Cells with embedded tabs/newlines are sanitized to single-line.
- `prompt_section` returns `""` for missing/header-only files; includes untrusted-data guard text; reviewer vs judge rule text by `role`; reviewer rule covers `oos` skip.
- `LARCH_LEDGER_KEEP_NEUTRAL` flips neutral wording.
- Byte cap truncates and annotates.

### UPDATED: `python/review_tally.py`
Write the ledger at end of each code-review round inside `tally_code_votes`, only on **final** tallies.
- Resolve `root = findings_ledger.ledger_root(review_tmpdir, session_env_path=args.session_env_path)`.
- After classification rows and outcomes are computed, assemble one entry per finding/OOS item:
  - `finding_id` = item id.
  - `title` / `file_line` / `reason` from the parsed ballot block (`voting.split_ballot` data the tally already holds).
  - `vote_tally` from YES/total already computed.
  - `outcome`: when `item_id.startswith("OOS_")` or scope is OOS/drift-rerouted, emit `oos` regardless of vote disposition; otherwise map classification result to `accepted` / `neutral` / `rejected`.
- Call `findings_ledger.write_round(root, int(args.round_num), entries)`.
- **Skip ledger write** when `TALLY_STATUS=main-agent-vote-required` (pre-MAV provisional tally), matching `reviewer-prune-ledger` behavior on MAV paths.
- Do not change existing classification or `voting-tally.md` output.

### UPDATED: `python/plan_review_tally.py`
Write the ledger at end of each plan-review round on final tallies only.
- Derive `round_num` from `self.findings_out` when it matches `.../plan-review/round-<N>/findings-classification.tsv`; default `1` for legacy standalone `findings-classification.tsv` paths. Optionally accept `--round-num` for explicit callers; `plan_review_round.py` already knows `round_num` and can pass it when wiring tally.
- Assemble the same entry shape (including `outcome=oos` for `OOS_*` ids) from ballot + classification, then call `findings_ledger.write_round(findings_ledger.ledger_root(Path(self.design_tmpdir), design_tmpdir=self.design_tmpdir), round_num, entries)`.
- **Skip ledger write** on `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required`.
- Keep existing per-round `findings-classification.tsv` write unchanged.

### UPDATED: `python/rendering.py`
Inject the ledger into **review-round** renderers only (`render_specialist`, `render_plan_review`, `render_voter`). Do **not** modify `render_reviewer_main` (that path serves `/research` validation, outside the three duplicate-suppression surfaces).

- Add optional `--findings-ledger-file` (default empty) to `render_specialist_main`, `render_plan_review_main`, and `render_voter_main`.
- When the flag is absent, **derive default ledger path** from env/tmpdir context so Codex sentinel re-renders stay correct:
  - `render_specialist`: `findings_ledger.ledger_path(findings_ledger.ledger_root(review_tmpdir from --session-env-path parent or IMPLEMENT_TMPDIR/REVIEW_TMPDIR env))`.
  - `render_plan_review`: derive from `--design-tmpdir`.
  - `render_voter`: same resolver as specialist when review context flags are present.
- Build the section via `findings_ledger.prompt_section(ledger_root, role=...)`, using the ledger file's parent as `ledger_root` when an explicit path is passed.
- `render_specialist_main` and `render_plan_review_main`: inject `reviewer` section when non-empty.
- `render_voter_main`: inject `judge` section when non-empty.
- `render_specialist_main` content cache: include ledger file sha256 in the cache key.

### UPDATED: `python/agent_voters.py`
**Firm injection site for code-review judges.** `_make_voter_prompt_file` must pass `--findings-ledger-file` into `render voter`, using the same resolved ledger root as the writer (`findings_ledger.ledger_path(findings_ledger.ledger_root(review_tmpdir, session_env_path=...))`). This is the production path for `/implement` Step 5 and `/review` diff mode (`agent dispatch-voters`).

### UPDATED: `python/agents.py`
**Static specialist dispatch only** (not voters). In `_review_specialist_render_args`, `_review_render_specialist_prompt`, and Codex sentinel replay (`_review_read_codex_prompt_sentinel`):
- Pass `--findings-ledger-file` on initial render.
- Extend the Codex compact sentinel KV set with `FINDINGS_LEDGER_FILE` when present so sentinel re-render replays the same ledger path.
- When the flag is omitted from sentinel, rely on `render specialist` default-path derivation from `IMPLEMENT_TMPDIR` / `REVIEW_TMPDIR` / session-env parent.

### UPDATED: `python/review_pipeline.py`
**Firm injection site for dynamic code-review reviewers.** In `_synthesize_dynamic_slots`, pass `--findings-ledger-file` (same resolved root as tally) into each `render specialist` call. No optional MAY_UPDATE carve-out.

### UPDATED: `python/plan_review_panel.py`
Pass `--findings-ledger-file` pointing at `findings_ledger.ledger_path(design)` on static and dynamic `render plan-review` calls and in `_make_voter_prompt`'s `render voter` command. Renderer no-ops when absent (round 1).

### UPDATED: `python/design_log_publish_flow.py`
Add `findings-ledger.tsv` to `_PUBLISH_EXCLUDE_NAMES` so the ephemeral ledger is never copied into `larch-logs/design/<RUN_ID>/`.

### UPDATED: `python/test_rendering.py`
- `render_specialist`, `render_plan_review`, and `render_voter` inject the section only when the ledger is non-empty; round-1 (missing file) yields no section.
- Reviewer renderers get reviewer rules (including `oos` skip); `render_voter` gets judge rules.
- Injected section includes untrusted-data guard text.
- `render_specialist` cache key changes when ledger content changes.
- Default-path derivation works when `--findings-ledger-file` is omitted but `IMPLEMENT_TMPDIR` is set.
- No new ledger tests on `render_reviewer_main`.

### UPDATED: `python/test_agent_voters.py`
Assert `_make_voter_prompt_file` passes `--findings-ledger-file` with the IMPLEMENT_TMPDIR-root path on nested implement rounds.

### UPDATED: `python/test_review_pipeline.py`
Assert `_synthesize_dynamic_slots` `render specialist` argv includes `--findings-ledger-file`.

### UPDATED: `python/test_review_tally.py`
- After a code-review round tally, `findings-ledger.tsv` exists at the correct root with one row per item, correct outcome (including `oos`), and no proposer column.
- Nested implement layout test (mirror `test_findings_classification_nested_impl_path_and_write_round`): round 1 writes to `IMPLEMENT_TMPDIR/findings-ledger.tsv`, round 2 appends at the same root.
- Re-tally / MAV: `main-agent-vote-required` does not write ledger rows; a subsequent final tally replaces the round's rows without duplicates.

### UPDATED: `python/test_plan_review.py`
After plan-review round tally, ledger at design tmpdir root; round 2 appends; `main-agent-vote-required` skips write; re-tally replaces same-round rows.

### UPDATED: `python/test_design_log_publish_flow.py`
A `findings-ledger.tsv` in the design tmpdir is excluded from the published tree.

## Approach

- One writer module, shared `ledger_root()` resolver, two tally call sites. Nested `/implement` rounds read/write `IMPLEMENT_TMPDIR/findings-ledger.tsv` (same cumulative-root pattern as `reviewer-prune-ledger.tsv`); standalone `/review` and `/design` keep flat tmpdir roots.
- Reuse tally data already parsed. Title, file:line, reason, vote tally, and classification come from existing ballot/classification paths. The writer is a projection, not a new source of truth.
- Round upsert, not blind append. `write_round` replaces all rows for the current round atomically so degraded retries and MAV re-tallies cannot leave stale rejected/neutral rows beside final outcomes. Skip writes on pre-MAV `main-agent-vote-required` tallies.
- Inject by inlining a bounded, untrusted-data-framed section. Renderers embed the ledger like diff/scope blocks so external agents do not need to open a side file.
- Self-skipping round 1. Ledger is written at end of round; round 1 prompts see an absent or header-only file and inject nothing.
- Correct dispatch ownership. Code-review **judges** wire through `agent_voters.py`; **static specialists** through `agents.py`; **dynamic specialists** through `review_pipeline._synthesize_dynamic_slots`; plan-review through `plan_review_panel.py`. `render_reviewer_main` stays untouched (research-only).
- Ephemeral by construction. Allow-list code-review staging excludes unknown files; `/design` publish gets one deny-list entry; tmpdir cleanup discards the ledger.
- v1 is prompt-only. Duplicate policy lives in prompt rules; no ballot filtering in code (v2 deferred).

## Edge cases

- Round 1: ledger absent. No injection. Writer creates it at end of round 1.
- Zero findings in a round: write no data rows for that round (header may exist). `prompt_section` treats header-only as empty.
- OOS items: always `outcome=oos` at assembly time, even when votes would classify as accepted/neutral.
- Reviewer skip policy covers `rejected`, `neutral`, and `oos`; judge policy covers `rejected`, `neutral`, and ballot `oos` re-raise.
- Cells with tabs/newlines: sanitized to single-line.
- Large ledger across 5 rounds: `prompt_section` caps bytes, keeps recent rounds; on-disk ledger retains all rows.
- Nested `IMPLEMENT_TMPDIR/round-N` vs flat `REVIEW_TMPDIR`: `ledger_root()` picks the parent for nested implement; writer and all prompt dispatchers use the same resolver.
- Codex sentinel re-render: `FINDINGS_LEDGER_FILE` in sentinel KVs plus renderer default-path fallback.
- Neutral knob: default suppress; `LARCH_LEDGER_KEEP_NEUTRAL` re-surfaces via wording only.
- Prior reviewer prose in ledger cells: wrapped as untrusted data with sanitization so prompt-injection strings cannot override rubric.

## Failure modes

- Ledger leaks into committed logs. Most likely on `/design` if publish exclusion is missed. Signal: `findings-ledger.tsv` under `larch-logs/design/<RUN_ID>/`. Mitigation: `_PUBLISH_EXCLUDE_NAMES` plus `test_design_log_publish_flow.py`.
- Nested implement path split (writer in `round-N`, reader at `IMPLEMENT_TMPDIR`). Signal: round 2+ duplicate rate unchanged. Mitigation: shared `ledger_root()` in writer and all dispatch sites; nested tally test.
- Judges miss ledger (wrong file patched). Signal: judges never mention ledger rules. Mitigation: wire `agent_voters.py`, not `agents.py`, with `test_agent_voters.py` assertion.
- Dynamic reviewers miss ledger. Signal: only static slots skip duplicates. Mitigation: firm `review_pipeline.py` update plus dispatch test.
- Stale rows after MAV/re-tally. Signal: ledger shows duplicate/conflicting rows for one round. Mitigation: round upsert + skip pre-MAV writes + re-tally tests.
- Stale cached specialist prompt. Signal: round-2 specialist lacks ledger despite file present. Mitigation: ledger sha in `render_specialist` cache key.
- Prompt injection via ledger cell content. Signal: reviewers follow text inside a prior `reason` field. Mitigation: untrusted-data wrapper + cell sanitization in `prompt_section`.

## Testing strategy

- New `python/test_findings_ledger.py` for resolver, upsert, anonymization, OOS mapping, neutral knob, untrusted guard, byte cap.
- `test_rendering.py` for specialist/plan-review/voter injection, default-path derivation, cache key.
- `test_agent_voters.py` and `test_review_pipeline.py` for judge and dynamic specialist dispatch flags.
- `test_review_tally.py` nested implement root, OOS outcomes, MAV skip, re-tally replace.
- `test_plan_review.py` round derivation from classification path, append across rounds, MAV skip, re-tally replace.
- `test_design_log_publish_flow.py` publish exclusion.
- Run `make py-lint`, `make py-test`, and `make lint`.

## Acceptance

- `python/findings_ledger.py` exists with `LEDGER_BASENAME`, `ledger_path`, `ledger_root`, `LEDGER_HEADER` (columns `round`, `finding_id`, `title`, `file_line`, `outcome`, `vote_tally`, `reason`; no proposer column), `write_round` (per-round atomic upsert), and `prompt_section(role=reviewer|judge)`.
- `ledger_root` resolves a nested `/implement` `round-N` tmpdir to its `IMPLEMENT_TMPDIR` parent; standalone `/review` and `/design` use the flat tmpdir root.
- `review_tally.py` and `plan_review_tally.py` call `write_round` at end of round on final tallies only; both skip the write on `main-agent-vote-required`; existing `findings-classification.tsv` and `voting-tally.md` output is unchanged.
- The ledger is injected into `render_specialist` and `render_plan_review` (reviewer rules) and `render_voter` (judge rules) only when the ledger file exists and is non-empty; round 1 injects nothing. `render_reviewer_main` is unchanged.
- Code-review judges receive the ledger via `agent_voters.py`; static specialists via `agents.py` (including Codex sentinel replay); dynamic specialists via `review_pipeline.py`; plan review via `plan_review_panel.py`.
- The injected section carries untrusted-data framing and sanitized cells; the `render_specialist` cache key includes the ledger sha256.
- `findings-ledger.tsv` is in `_PUBLISH_EXCLUDE_NAMES` and never appears under `larch-logs/design/<RUN_ID>/`.
- v2 (embedding auto-suppression at aggregation) is NOT implemented; it is deferred.
- New `python/test_findings_ledger.py` plus the listed test additions pass. `make py-lint`, `make py-test`, and `make lint` pass.

review_status: panel-failed
rounds_completed: 2
diff_added: 540
diff_deleted: 35
diff_lines: 575
