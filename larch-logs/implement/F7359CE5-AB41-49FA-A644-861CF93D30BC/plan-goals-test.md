## Goal
Implement issue #4615: [IMPLEMENTING] [OOS] Test-harness, dead-code & lint-table cleanup — 8 items.

## Implementation Plan
## Plan

## Approach

- 8 OOS cleanup items. Keep each change minimal and targeted.
- Item 6 has no current Makefile violations (resolved by #4503). No code change needed.
- Item 7 is process-only: rebalance follow-ups already closed (#4600, #4503). No action.
- Item 4: consolidate voter-exclusion to a single live `parse-rate-check` call, removing the sidecar-read path. Use `--id-grammar finding-oos` and branch-specific `--voter-tool` / `--slot` wiring.
- Item 4 testing: add one targeted `python/test_review_tally.py` case that exercises narrative-only voter exclusion through the live `parse-rate-check` tally path (accepted FINDING_1). Existing `test_tally_three_voter_mixed_outcomes` only uses well-formed vote lines and does not cover this quorum branch.

## Files to modify/create

### UPDATED: scripts/test-research-structure.sh

- Add Check 14: pin NOT_SUBSTANTIVE terminal behavior in `research-phase.md`.
  - Assert `STATUS=NOT_SUBSTANTIVE` appears.
  - Assert `do not launch a Claude replacement` appears.
  - Assert `do not pass the narrative file to synthesis` appears.
  - Assert `No non-substantive retry artifacts are created` appears.
- **Drop Check 15** (original `FINDING_N` / `OOS_N` pins in `validation-phase.md`). Those literals are absent from the research tree; asserting them would fail `make lint` on every run. Item 1 scope is NOT_SUBSTANTIVE / synthesis gating, not plan-voter ballot grammar.
- Add Check 15 (renumbered from original Check 16): pin synthesis gating and STATUS-gated input exclusion in `research-phase.md`.
  - Assert `Do NOT emit a \`## Research Synthesis\` header` appears (orchestrator-owned).
  - Assert `[lane dropped: collector NOT_SUBSTANTIVE]` appears (STATUS-gated exclusion marker).
- Use existing `contains` helper.
- Keep the harness structural; do not execute `/research`.

### UPDATED: python/test_plan_review.py

- Add a test `test_embedded_plan_review_loop_not_substantive_count_emitted`.
- Use `plan_review.legacy_asset_bytes("skills/design/scripts/plan-review-loop.sh")`.
- Keep existing assertions at lines 46-47 in `test_embedded_plan_review_loop_uses_migrated_collector` unchanged (body-wide `NOT_SUBSTANTIVE and other non-OK` and `COLLECT_FAILURE_COUNT` pins).
- Strengthen count-path pinning beyond body-wide substring checks:
  1. **Initialization**: assert the exact literal `COLLECT_FAILURE_COUNT=0` appears in the embedded body (not merely `COLLECT_FAILURE_COUNT` with a nonzero suffix).
  2. **Emit region**: slice the `_write_round_summary` function body (from its opening `{` through the next top-level function or EOF) and assert that region references `round-summary.env` and contains a `COLLECT_FAILURE_COUNT` emit line (e.g. `printf` / `emit` / `COLLECT_FAILURE_COUNT=` assignment targeting the round-summary writer).
  3. **Increment path**: slice the collector-evidence counting helper (the function or loop that increments `collect_failure_count` / `COLLECT_FAILURE_COUNT` on non-OK collector rows) and assert it increments the failure count for non-OK statuses. Do **not** require a `NOT_SUBSTANTIVE` literal inside this regional block; the embedded helper counts wildcard non-OK statuses.
- If the embedded asset uses different function names, locate the round-summary writer and collector-counting blocks by searching for `round-summary.env` and `COLLECT_FAILURE_COUNT` and apply the same regional assertions to those blocks.

### UPDATED: python/collect_results.py

- In `resolve_collector_stderr_tail_file`, remove the dead `-ns-retry.txt.stderr-tail` check (lines 761-763).
- Keep the live fallback order:
  1. `-retry.txt.stderr-tail`
  2. launch-stderr rendered tail
  3. original `.stderr-tail`
- Do not remove `ns_retry_mode` / `ns_retry_reason` fields on `CollectorRecord`; those remain live diagnostics.

### UPDATED: python/test_collect_results.py

- Extend `test_stderr_tail_resolution_prefers_retry_and_dedupes` (or add a sibling test) for `resolve_collector_stderr_tail_file`.
- Create a non-empty `*-ns-retry.txt.stderr-tail` sidecar alongside a non-empty `*-retry.txt.stderr-tail` sidecar.
- Assert the ns-retry sidecar is **not** returned.
- Assert the existing `-retry.txt.stderr-tail` preference still wins.

### UPDATED: python/legacy_review_shell/tally-code-votes.sh

- Remove the `python3 "$CLI" voting parse-rate-diag-matches` call from the voter-eligibility loops (both the `THREE_SLOT_PANEL=true` and the else branch).
- Replace with a live check via `python3 "$CLI" voting parse-rate-check`, passing args available at tally time.
- **Shared args** (both branches): `--voter-file`, `--ballot-file "$BALLOT_FILE"`, `--id-grammar finding-oos`, `--review-tmpdir "$REVIEW_TMPDIR"`, `--log-mode none`.
- **Three-slot branch** (`for slot in 0 1 2`): also pass `--voter-tool "${VOTER_TOOLS[$slot]}"` and `--slot "$slot"`.
- **Legacy else branch**: do **not** pass `--slot` (unset under `set -u`). Pass `--voter-tool` with a label derived from the voter file basename (e.g. strip `-vote-output.txt` suffix) or a fixed fallback such as `claude` when no tool array exists. Read the script before editing to match existing reviewer-for-block naming.
- Parse `PARSE_RATE_STATUS=OK` from stdout. Exit code is always 0; branch on the KV line.
  - `OK` → voter is effective (add to `EFFECTIVE_VOTER_FILES`; set `EFFECTIVE_SLOT[slot]=true` in three-slot branch).
  - Non-OK → increment `VOTER_PARSE_FAILED_COUNT` and exclude.
- `BALLOT_FILE` and `REVIEW_TMPDIR` are in scope at the voter-eligibility loop (parsed at script top). Do not change `voting.py` behavior.

### UPDATED: python/test_review_tally.py

- Add `test_tally_excludes_narrative_only_voter_parse_rate_check`.
- Use the legacy (non-three-slot) `tally-code-votes` path via existing `run_review` helper and `_mk_ballot`.
- Fixture layout:
  - `cursor-vote-output.txt` and `codex-vote-output.txt`: well-formed `FINDING_N:` vote lines for every ballot item (reuse patterns from `test_tally_three_voter_mixed_outcomes`).
  - `claude-vote-output.txt`: narrative-only prose with **no** `FINDING_N:` / `OOS_N:` vote lines (e.g. `narrative only\n`). Do **not** pre-create a `-parse-rate-diag.txt` sidecar; the tally path must call live `parse-rate-check`, not infer exclusion from stale dispatch artifacts.
- Invoke `run_review("tally-code-votes", ...)` with `--ballot-file`, `--review-tmpdir`, and all three `--voter-files` in panel order.
- Assertions (quorum math on the tally hot path):
  1. `result.returncode == 0`.
  2. `ELIGIBLE_VOTER_COUNT == "3"` (three non-empty voter files seen).
  3. `VOTER_COUNT == "2"` (narrative-only voter excluded after `PARSE_RATE_STATUS=NOT_SUBSTANTIVE`).
  4. `TALLY_STATUS == "ok"` (two substantive voters remain; not the zero-judge `main-agent-vote-required` path).
  5. Optional but recommended: `voting-tally.md` (or stdout degraded warning) mentions narrative-only / parse-rate exclusion so a miswired OK/non-OK branch is visible in artifacts.
- This test fails under the pre-change sidecar path when the narrative voter lacks a matching `-parse-rate-diag.txt` (it would be counted effective). It passes only when tally excludes via live `parse-rate-check`.
- No Makefile `-k` change needed for this test: existing `test-tally-code-votes` filter `'tally_ and not emit'` already selects `test_tally_*` names.

### UPDATED: python/voting.py

- No behavioral change needed.
- Add a one-line comment near `voter_parse_rate_diag_matches_output` noting that `tally-code-votes.sh` no longer reads this sidecar; it calls `parse-rate-check` directly.

### UPDATED: Makefile

- Rename `test-dispatch-code-voters-retry-claude` to `test-dispatch-code-voters-parse-rate-claude`.
- Update:
  - The target definition (line 865).
  - The `.PHONY` entry (line 852 block).
  - The `test-harnesses-19` dependency list (line 140).
- Keep the pytest `-k voter_retry_claude` selector unless the underlying test function is also renamed.

### UPDATED: scripts/test-prompt-template-invariants.sh

- Remove the `parse-retry`-specific branch from the Codex stub (lines 59-62 in the current file).
  Specifically: `if [[ "$out" == *parse-retry* ]]; then ... fi` — remove this branch entirely.
- Keep the `else` branch that writes `Narrative output.` for all other outputs.
- Retain the assertion at line 152-153: `[[ -z "$retry_prompt" ]] || fail "plan-voter retry prompt should not be rendered"`.
- Update the sibling `.md` to reflect the removed branch.

### UPDATED: docs/linting.md

- Update the `make test-classify-bump` row (line 222).
- Remove "and release helper CLIs" from the description.
- Change the description to: "Run the pytest coverage for `python/version_bump.py`. Covers transparent bump-pipeline idempotency (`Bump version` / `chore(larch-logs)` stacks still emit `BUMP_TYPE=NONE`) and fail-closed transparent-subject spoofing. A `make lint` prerequisite via the `test-harnesses-20` shard partition."
- Leave release helper coverage documented on `test-release-prepare` and its siblings.

## Acceptance

- `bash scripts/test-research-structure.sh` passes including new Checks 14-15.
- `python3 -m pytest python/test_plan_review.py` passes including `test_embedded_plan_review_loop_not_substantive_count_emitted`.
- `python3 -m pytest python/test_collect_results.py` passes including negative ns-retry assertion.
- `python3 -m pytest python/test_review_tally.py` passes including `test_tally_excludes_narrative_only_voter_parse_rate_check`.
- `bash scripts/test-prompt-template-invariants.sh` passes with stale parse-retry stub removed.
- `bash scripts/test-harness-shards-coverage.sh` passes with renamed Makefile target.
- `make test-classify-bump` passes.
- `make py-lint` and `make py-test` pass.
- `make lint` passes.

diff_lines: 155

## Test plan
(no test plan section in plan-file)
