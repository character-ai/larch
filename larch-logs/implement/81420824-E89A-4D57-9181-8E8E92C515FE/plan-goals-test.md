## Goal
Implement issue #5940: [IMPLEMENTING] [BUG] /review vendor-fallback reviewer attribution not reconciled (only /design).

## Implementation Plan
## Plan

## Approach

- Keep the fix in `progress_report.py`.
- Generalize `_fallback_label_remap` instead of adding a `/review` sibling.
- Reuse `_collector_env_paths_for_round(round_dir)` to find `collector-results.env`.
  - Search order: `round_dir/collector-results.env`, then `round_dir.parent/collector-results.env`, then design root when `"plan-review"` is in `round_dir.parts`.
  - This covers code-review `/review --diff` where the collector lives at the rounds root (`review_tmpdir/collector-results.env`), parent of `round-1`.
  - It also preserves `/design` root-level `collector-results.env` and per-round collectors on implement Step 5 paths.
- Build remap entries from each round's `panel-manifest.ndjson`.
- Include `plan-review-slots.ndjson` only for `/design` plan-review rounds.
- Derive the nominal vendor from each manifest row's `tool` field.
  - Do not infer it from the slot name.
  - This handles code-review slots such as `arch` and `generalist`.
- Preserve existing label shapes:
  - `/design`: `Cursor-Arch (via Codex)`.
  - `/review` and `/implement` Step 5: `cursor/arch (via Codex)` or equivalent current Top-reviewer base label plus annotation.
- Do not touch `code-voter-slots.ndjson`.
  - It is the voter manifest.
  - This bug concerns reviewer/finder attribution in the review panel manifest.

## Files to modify/create

### UPDATED: python/larch/report/progress_report.py

- Add a small helper to resolve collector provenance for a round using `_collector_env_paths_for_round`.
  - Walk paths in the existing order; use the first present, non-symlink, non-empty collector file.
  - Return the same normalized basename to executing-tool map currently produced by `_executing_tool_by_norm_basename`.
  - Skip absent, symlinked, or empty collector files as today.
- Add a helper to produce the manifest base label for remap matching:
  - If the slot is a plan-review slot with a known plan-review prefix, use `plan_review_round._slot_human_label(slot)` to preserve `/design` output.
  - Otherwise use the same code-review label shape as `_progress_label_map_from_manifests`: `"{tool}/{slot}"`.
- Add a helper to reconcile a manifest row:
  - Inputs: `slot`, nominal `tool`, `output`, and executing tool.
  - If nominal and executing tools differ, append ` (via <TitleTool>)`.
  - If they are the same, return the base label unchanged.
  - Ignore blank or `unknown` executing tools.
- Update `_fallback_label_remap(round_dirs)` to:
  - Call the new collector path helper per round (not a hardcoded `round_dir.parent.parent` path).
  - Read `round_dir / "panel-manifest.ndjson"` for both `/design` and code review.
  - Add the design-root `plan-review-slots.ndjson` only when `"plan-review"` appears in `round_dir.parts`.
  - Read `slot`, `tool`, and `output` from each row.
  - Map the base label to the reconciled label only when the label changes.
- Keep `_apply_fallback_remap` unchanged except for any type or docstring adjustment needed by the helper changes.

### UPDATED: python/tests/report/test_progress_report.py

- Add a code-review regression beside `test_fallback_label_remap_annotates_executing_tool`.
- **Primary fixture** (exercises parent collector lookup for `/review --diff`):
  - `root = tmp_path / "review"`.
  - `round_dir = root / "round-1"`.
  - `round_dir / "panel-manifest.ndjson"` contains a slot with nominal `tool: "cursor"`, slot such as `"arch"`, and output path such as `cursor-specialist-arch-output.txt`.
  - `root / "collector-results.env"` (rounds root, parent of `round-1`) records the same output with `TOOL=codex` and `STATUS=OK`.
  - **Do not** create `round_dir / "collector-results.env"` in this case; the test must fail if remap only consults the round-local path.
  - Assert `_fallback_label_remap([round_dir])` maps the current base label, likely `cursor/arch`, to `cursor/arch (via Codex)`.
- **Secondary fixture** (optional, implement Step 5 per-round collector):
  - Same manifest shape under `round_dir`.
  - Place `collector-results.env` only under `round_dir`, not at `root`.
  - Assert the same remap when the round-local collector is the first hit in `_collector_env_paths_for_round` order.
- Add an end-to-end render assertion if cheap:
  - Use the primary fixture layout (`collector-results.env` at `root`, not under `round-1`).
  - Write minimal `round-meta.json`.
  - Write `findings-classification.tsv` with accepted `reviewer_slots` pointing at the output basename.
  - Render `render_phase_detail(rounds_root=root, skill="implement")`.
  - Assert the Top-reviewers section contains the `(via Codex)` annotation.
- Keep existing `/design` tests passing unchanged.

## Edge cases

- Missing collector file returns no remap.
- Collector `TOOL=unknown` returns no remap.
- Same nominal and executing tool returns no remap.
- Manifest rows missing `slot`, `tool`, or `output` are ignored.
- Absolute and relative output paths still match through `voting.normalize_reviewer_basename`.
- `/design` remains compatible with both per-round `panel-manifest.ndjson` and design-root `plan-review-slots.ndjson`.
- Code-review collector at rounds root (`round_dir.parent/collector-results.env`) is consulted when no round-local collector exists.

## Failure modes

- If the remap key does not match the Top-reviewer label, attribution stays unannotated.
  - The primary code-review test must catch this; it must not pass when only a round-local collector would be read.
- If multiple collector files exist, prefer the existing `_collector_env_paths_for_round` order.
  - Round-local first, then parent; matches current failed-reviewer behavior and avoids new path policy.
  - The secondary fixture verifies round-local precedence when both could exist.
- If a future manifest omits `tool`, the row cannot be reconciled.
  - Ignore it rather than guessing from file names.

## Testing strategy

- Run the focused unit test file:
  - `python3 -m pytest python/tests/report/test_progress_report.py -k 'fallback_label_remap or top_reviewers_implement_from_classification'`
- Run the full changed test file if time allows:
  - `python3 -m pytest python/tests/report/test_progress_report.py`
- Run Python lint for the changed production and test files if dependencies are present:
  - `make py-lint`
- No docs update is required because this fixes behavior to match existing documented and claimed behavior.

## Acceptance

- Run the focused unit test file:
  - `python3 -m pytest python/tests/report/test_progress_report.py -k 'fallback_label_remap or top_reviewers_implement_from_classification'`
- Run the full changed test file if time allows:
  - `python3 -m pytest python/tests/report/test_progress_report.py`
- Run Python lint for the changed production and test files if dependencies are present:
  - `make py-lint`
- No docs update is required because this fixes behavior to match existing documented and claimed behavior.

diff_added: 95
diff_deleted: 15
mechanical_churn: false
diff_lines: 110

## Test plan
(no test plan section in plan-file)
