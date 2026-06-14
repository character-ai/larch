## Goal
Implement issue #4331: [IMPLEMENTING] [OOS] Test coverage, blocking severity, and orchestrator-never contract gaps — 4 items.

## Implementation Plan
## Plan

## Approach

Use the approved outline as binding scope. `approach-synthesis.txt` is `NO_SKETCHES`, so base the plan on direct inspection only.

Keep changes small:
- Add targeted tests for launcher terminal ordering.
- Add targeted tests for `kill_session_background_processes` edge cases.
- Pin the missing orchestrator-never carve-out literal.
- Add `blocking` to severity surfaces and the high-severity matcher.

Edit generator **sources** only for reviewer prompt text. Regenerate committed artifacts instead of hand-editing generated files:
- `agents/reviewer-correctness.md` → `python3 python/cli.py generate pre-rendered-reviewer-prompts`
- `skills/shared/reviewer-templates.md` → run every `generate *-agent` row in `scripts/generators.tsv` that reads `reviewer-templates.md`:
  - `python3 python/cli.py generate code-reviewer-agent`
  - `python3 python/cli.py generate reviewer-plan-fidelity-agent`
  - `python3 python/cli.py generate reviewer-code-robustness-agent`
  - `python3 python/cli.py generate reviewer-security-structure-tests-agent`

## Files to modify/create

### UPDATED: python/test_launch_review.py

Add two focused ordering tests near the existing launcher tests.

- Add `test_codex_terminal_artifacts_order_metadata_usage_dirty_tree_done`.
  - Stub `_prepare_codex_home` to succeed.
  - Stub `resolve_model_args` to return empty args.
  - Stub `_review_run_with_retries` to return `(RunExternalAgentResult(0, out), 1, 1)` — a 3-tuple matching `_review_launch_codex` unpack at `agents.py:3563` and the existing pattern in `test_codex_review_ingests_token_record_sidecar` (`test_launch_review.py:455-456`). Do not return a bare `RunExternalAgentResult`.
  - Track calls from:
    - `_review_append_outer_meta` as `metadata`
    - `_record_usage_from_events` as `usage`
    - `_review_write_clean_readonly_dirty_tree` as `dirty-tree`
    - `_promote_inner_done` as `done`
  - Assert the tracked terminal sequence is exactly:
    - `metadata`
    - `usage`
    - `dirty-tree`
    - `done`

- Add `test_cursor_terminal_artifacts_order_metadata_trap_postprocess_dirty_tree_done`.
  - Reuse the existing cursor stubbing pattern from `test_cursor_done_promoted_after_timing_record`.
  - Track calls from:
    - `_review_append_outer_meta` as `metadata`
    - `_review_run_test_trap_after_inner_done_if_enabled` as `trap`
    - `_review_cursor_postprocess` as `postprocess`
    - `_review_write_cursor_dirty_tree_from_baseline` as `dirty-tree`
    - `_promote_inner_done` as `done`
  - Assert the tracked terminal sequence is exactly:
    - `metadata`
    - `trap`
    - `postprocess`
    - `dirty-tree`
    - `done`

Keep the existing `test_cursor_done_promoted_after_timing_record` unless it becomes redundant or conflicts. Do not add broad integration coverage beyond these terminal-order assertions.

### UPDATED: python/test_finalize.py

Add three edge-case tests near `test_kill_session_background_processes_skips_live_python_ancestors`.

- Add `test_kill_session_background_processes_returns_false_without_tmpdir`.
  - Build a context with `tmpdir=""`.
  - Use `RecordingRunner(strict=True)`.
  - Assert the function returns `False`.
  - Assert no runner calls occurred.

- Add `test_kill_session_background_processes_returns_false_when_no_processes_match`.
  - Monkeypatch `os.getpid` and `os.getppid`.
  - Use strict runner responses for ancestor lookup, shell probe, and an empty process-list result.
  - Assert the function returns `False`.
  - Assert no `kill -TERM` call occurred.

- Add `test_kill_session_background_processes_tolerates_tmpdir_resolve_oserror`.
  - Monkeypatch `finalize.Path` only for the resolve call path, or use a small fake path class if needed.
  - Make `resolve(strict=False)` raise `OSError`.
  - Return one matching PID from the process-list command.
  - Assert the function still attempts `kill -TERM` for that PID.
  - Assert the function returns `True`.

Keep these as unit tests. Do not add or extend the shell `dispatch-with-waterfall` harness because the approved non-goal says TERM behavioral coverage already exists.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

Add one `check "$ORCH_NEVER_MD"` assertion near the existing shared orchestrator assertion.

- Pin this literal:
  - `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter`

Use a label that names `skills/shared/orchestrator-never.md`, for example:
- `shared orchestrator NEVER pins premature-notification recovery as narrow single-waiter guidance`

Do not change the rule text itself unless the assertion shows it is already absent.

### UPDATED: agents/reviewer-correctness.md

Update the prose severity list at the numbered-list instruction (~line 60).

- Change the list from:
  - `**Important**` / `**Nit**` / `**Latent**`
- To include:
  - `**Blocking**` / `**Important**` / `**Nit**` / `**Latent**`

The TSV instruction already includes `blocking`; leave it unchanged unless formatting requires consistency.

Do not hand-edit `agents/pre-rendered/reviewer-correctness-body.txt`. Regenerate it after this source edit (see Regeneration below).

### UPDATED: python/review_and_fix.py

Extend `_HIGH_RE` to treat `**Blocking**` as high severity across **all three branches** that already handle Important — not only the FINDING-title alternation.

Current structure (`review_and_fix.py:34-38`):
1. FINDING-title alternation: `^### FINDING_[0-9]+:...` with embedded `**Important**` / `**Critical**` / `**High**`
2. Standalone body-line branch: `\*\*[Ii]mportant\*\*`
3. Concern bracket branch: `^- \*\*Concern\*\*:\s*\[[Ii]mportant\](?:[\s,:;.\)]|$)`

Apply Blocking in each branch, mirroring Important casing and placement:

- **Branch 1 (FINDING-title alternation):** add `\*\*Blocking\*\*` to the grouped alternation alongside `\*\*Important\*\*`, `\*\*Critical\*\*`, and `\*\*High**`.
- **Branch 2 (standalone body-line):** add `\*\*[Bb]locking\*\*` as a separate alternation arm alongside the existing `\*\*[Ii]mportant\*\*` arm so body lines such as `- **Blocking**` or `- **blocking**` match without a FINDING-title severity tag.
- **Branch 3 (Concern bracket):** add `^- \*\*Concern\*\*:\s*\[[Bb]locking\](?:[\s,:;.\)]|$)` alongside the existing `[Ii]mportant` Concern pattern so `Concern [Blocking]` / `Concern [blocking]` formats match.

Do not change downstream counting logic (`_high_severity_count`, `_important_present`).

### UPDATED: skills/shared/reviewer-templates.md

Add `blocking` to canonical severity enumerations across all in-scope canonical prompt text that enumerates severities.

**Main code reviewer template (JSONL path):**

- JSONL field description near the main code reviewer template (~line 204): add `"blocking"` to the `severity` enum.
- `### Severity` prefix bullets (~lines 212-215): add a `**Blocking**` bullet before `**Important**` with minimal semantics, for example: must be fixed before merge; correctness, security, or contract breakage that blocks the change.
- Severity-tags prose (~line 219): include `**Blocking**` in the backtick list so it reads `**Blocking**`, `**Important**`, `**Nit**`, `**Latent**`.
- In-Scope numbered-list severity instruction (~line 239): add `**Blocking**` to the required-prefix enumeration.
- Out-of-Scope "same three-option tag" prose (~line 245): update to four-option wording consistent with the In-Scope line.

**Matching generated-body sections** (TSV-based reviewer variants):

- JSONL/TSV usage prose (~lines 357, 472, 583): add `blocking` to the `severity` value list (`blocking`, `important`, `nit`, or `latent`).
- Numbered-list severity instructions in matching canonical sections (~lines 338, 453, 564): add `**Blocking**` to each `**Important**` / `**Nit**` / `**Latent**` enumeration.

Use the same casing pattern already used at each site:
- JSONL/TSV values: `"blocking"`, `"important"`, `"nit"`, `"latent"`
- Markdown severity tags: `**Blocking**`, `**Important**`, `**Nit**`, `**Latent**`

Do not hand-edit `agents/code-reviewer.md`, `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, or `agents/reviewer-security-structure-tests.md`. Regenerate all four after this template edit (see Regeneration below).

### UPDATED: python/rendering.py

Update the rendered prompt text near the JSONL schema instructions (~line 1136).

- Change:
  - `severity important, nit, or latent`
- To:
  - `severity blocking, important, nit, or latent`

Do not alter unrelated ballot severity axes such as `blocker|major|minor|nit|uncertain`.

### Regeneration (generator-owned artifacts)

After the source edits above, regenerate committed artifacts. Run every `generate *-agent` verb in `scripts/generators.tsv` whose output derives from `skills/shared/reviewer-templates.md`, plus pre-rendered bodies:

```bash
python3 python/cli.py generate code-reviewer-agent
python3 python/cli.py generate reviewer-plan-fidelity-agent
python3 python/cli.py generate reviewer-code-robustness-agent
python3 python/cli.py generate reviewer-security-structure-tests-agent
python3 python/cli.py generate pre-rendered-reviewer-prompts
```

Expected generated updates (do not hand-edit):
- `agents/code-reviewer.md`
- `agents/reviewer-plan-fidelity.md`
- `agents/reviewer-code-robustness.md`
- `agents/reviewer-security-structure-tests.md`
- `agents/pre-rendered/reviewer-correctness-body.txt`
- `agents/pre-rendered/.manifest` (if the generator updates manifest hashes)

## Edge cases

- The launcher ordering tests should track function calls, not filesystem mtimes.
- The ordering tests should avoid real vendor calls.
- The Codex ordering test must stub `_review_run_with_retries` as a 3-tuple; a bare `RunExternalAgentResult` will fail at unpack in `_review_launch_codex`.
- The finalize OSError test should avoid changing global `pathlib.Path` behavior outside the smallest needed scope.
- `blocking` must be added to reviewer severity enums without changing ballot-voting severity values.
- `_HIGH_RE` must match Blocking in all three Important-parity shapes: FINDING-title tag, standalone body-line `**Blocking**` / `**blocking**`, and `Concern [Blocking]` / `Concern [blocking]` — title-only extension is insufficient for substantiality/convergence logic.
- The primary `### Severity` prefix bullets and the later JSONL/markdown severity lists must stay consistent after regeneration; do not update downstream lists without the ~212-215 prefix bullets.
- Template edits to Plan Fidelity, Code Robustness, and Security+Structure+Tests GENERATED_BODY blocks require all four reviewer-template generators; running only `code-reviewer-agent` leaves the other three agent files stale and fails `generate check`.
- Generator-owned files must stay in sync with their sources; CI `agent-sync` runs `python3 python/cli.py generate check`.

## Failure modes

- A broad monkeypatch in `test_finalize.py` can break unrelated `Path` use. Keep it local and restore through `monkeypatch`.
- If a launcher test stubs too much, it may stop exercising the terminal sequence. Stub external boundaries only.
- A Codex ordering-test stub returning a bare result object instead of `(result, auth_attempt, transient_attempt)` causes an immediate unpack `TypeError` before terminal-order assertions run.
- Hand-editing `agents/code-reviewer.md`, `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, `agents/reviewer-security-structure-tests.md`, or `agents/pre-rendered/reviewer-correctness-body.txt` causes CI drift or overwrites on regeneration. Edit sources and run the generate commands.
- Extending `_HIGH_RE` only in the FINDING-title alternation leaves body-line `**Blocking**` and `Concern [Blocking]` findings invisible to `_high_severity_count` / `_important_present`, so blocking-only rounds may be misclassified as non-substantial.
- Updating JSONL severity enums and In-Scope lists without the primary `### Severity` prefix bullets (~212-215) leaves contradictory reviewer instructions in regenerated agent files.
- Regenerating only `code-reviewer-agent` after `reviewer-templates.md` edits leaves Plan Fidelity, Code Robustness, and Security+Structure+Tests agent files out of sync; `python3 python/cli.py generate check` fails on those three outputs.
- Skipping `generate check` after template/agent source edits can leave local pytest green while CI `agent-sync` fails on stale generated output.

## Testing strategy

Run targeted checks first:
- `python3 -m pytest python/test_launch_review.py python/test_finalize.py`
- `bash scripts/test-implement-anti-polling-rule.sh`

After reviewer source/template edits, regenerate and verify generator sync:
- `python3 python/cli.py generate code-reviewer-agent`
- `python3 python/cli.py generate reviewer-plan-fidelity-agent`
- `python3 python/cli.py generate reviewer-code-robustness-agent`
- `python3 python/cli.py generate reviewer-security-structure-tests-agent`
- `python3 python/cli.py generate pre-rendered-reviewer-prompts`
- `python3 python/cli.py generate check`

Then run repository-relevant checks:
- `bash scripts/relevant-checks.sh`

If time allows, run:
- `make py-test`

## Acceptance

All four items implemented, tests pass, and generator sync is verified:

- `python3 -m pytest python/test_launch_review.py` passes with two new ordering tests.
- `python3 -m pytest python/test_finalize.py` passes with three new edge-case tests.
- `bash scripts/test-implement-anti-polling-rule.sh` passes with the new carve-out pin.
- `python3 python/cli.py generate check` exits 0 (no stale generated artifacts).
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 270

## Test plan
(no test plan section in plan-file)
