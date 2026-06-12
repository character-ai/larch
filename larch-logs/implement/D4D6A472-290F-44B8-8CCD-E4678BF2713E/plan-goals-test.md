## Goal
Implement issue #4101: [IMPLEMENTING] [OOS] Render phase detail & mermaid test coverage — 5 items.

## Implementation Plan
## Plan

## Plan

### Approach

- Treat the accepted reviewer finding as a required revision to Item 1.
- Keep the local developer path no-auto-install.
- Make generated Mermaid validation mandatory in GitHub Actions CI.
- Respect the #4062 prerequisite:
  - Items 1, 2, and 4 assume #4062 has merged first.
  - Do not implement Gantt harness, Mermaid lint, or final-summary/final-report Gantt doc-sync changes against pre-#4062 call sites.
  - Items 3 and 5 are independent and can be implemented before #4062 if needed.
- Preserve existing Gantt overlap behavior.
- Preserve token-ledger vendor cost behavior.
- Split round timing windows:
  - Use a skill-filtered window for table Time and Cost.
  - Use the existing unfiltered window for Gantt round overlap.
- Make live progress skip the shared renderer only when every discovered round dir lacks `round-meta.json`.
- Keep final reports and final summaries rendering `No review rounds completed.` for valid roots with zero completed rounds.
- Make Mermaid parse lint optional only outside required validation mode:
  - Local harness runs precheck for an existing `mmdc`.
  - Local harness prints one visible `SKIP:` breadcrumb when no existing CLI is available.
  - GitHub Actions CI installs the Mermaid toolchain before the renderer harness shard runs.
  - GitHub Actions CI fails if the helper cannot find the Mermaid CLI.
  - GitHub Actions CI fails if `python3 python/cli.py lint mermaid-fences` exits `2`.
  - The harness itself must not trigger `npm ci`, Mermaid package installation, or Chromium setup.

## Files to modify/create

### UPDATED: scripts/render-review-phase-detail.sh

- Replace the shared `rrange` use with two windows per completed round:
  - `table_rrange`, filtered by skill:
    - Pass `SKILL` into awk with `-v SKILL="$SKILL"`.
    - Match round rows with `$2=="round" && $4==SKILL && $6==r`.
    - Use this window for:
      - the table Time column.
      - total time accumulation.
      - `round_vendor_cost`.
  - `gantt_rrange`, unfiltered by skill:
    - Keep the existing predicate `$2=="round" && $6==r`.
    - Use this window only for `round_windows_file`.
- Keep writing `round_windows_file` from the unfiltered Gantt window.
- Do not change the Gantt awk.
- Do not filter `$2=="vendor"` timing rows by skill or task kind.
- Do not change token-ledger vendor cost parsing.
- Keep unreadable but present `round-meta.json` behavior delegated to the existing renderer degradation path.

### UPDATED: scripts/test-render-review-phase-detail.sh

- Add `assert_mermaid_valid "$OUT"` as a guarded helper.
- Add a `mermaid_required` predicate:
  - Required when `GITHUB_ACTIONS` is non-empty.
  - Required when `LARCH_MERMAID_REQUIRED=1`.
  - Optional otherwise.
- The helper should:
  - Return immediately when the file has no Mermaid fence.
  - Precheck for an existing Mermaid CLI before invoking the Python lint command.
  - Accept either:
    - the repo-local executable used by the linter at `mermaid-lint/node_modules/.bin/mmdc`.
    - `mmdc` on `PATH`.
  - If no existing CLI is found and validation is optional:
    - Print one visible skip line, for example `SKIP: Mermaid CLI unavailable; Mermaid parse validation skipped`.
    - Cache the optional skip state so repeated assertions do not repeatedly probe unavailable tooling.
    - Pass.
  - If no existing CLI is found and validation is required:
    - Call `fail` with a message that Mermaid CLI is unavailable in required validation mode.
    - Do not print a passing skip breadcrumb.
  - Run `python3 "$REPO/python/cli.py" lint mermaid-fences "$file"` only after the precheck passes.
  - If the command exits `0`, pass.
  - If the command exits `2` and validation is optional, print the same visible skip line and pass.
  - If the command exits `2` and validation is required, call `fail` with the linter output.
  - If the command exits any other non-zero status, call `fail` with the linter output.
- Do not make `mmdc` a hard dependency for local `test-render-review-phase-detail.sh`.
- Do not allow this test harness path to trigger `npm ci`, Mermaid package installation, or Chromium setup.
- Call `assert_mermaid_valid` after Gantt-producing cases:
  - Main Gantt output after Test 5b substring assertions.
  - Design skill Gantt fixture.
  - Gantt task-cap fixture.
  - Malformed ledger case only if the output contains a Mermaid fence.
- Do not call it for `--no-gantt` output.
- Add a regression fixture for skill-window contamination:
  - Create a completed `round-1/round-meta.json` with minimal valid tally and panel JSON.
  - Create `panel-manifest.ndjson` when needed for timing attribution.
  - Add one `implement` round row for round 1 with a short window.
  - Add one `design` round row for round 1 with a wider overlapping window.
  - Add a token-ledger vendor cost record that falls inside only the wider design window.
  - Run the renderer with `--skill implement --no-gantt`.
  - Assert the Time column uses only the implement window.
  - Assert it does not use the wider design window.
  - Assert the implement round Cost excludes the design-only token-ledger record.
  - Assert the Total cost excludes the design-only token-ledger record.
- Add or extend a Gantt preservation regression:
  - Use the same cross-skill round-window shape, or a dedicated fixture.
  - Include a vendor timing row that overlaps only the wider unfiltered round window.
  - Run with Gantt enabled.
  - Assert the reviewer timing chart still includes that overlapping vendor row.
- Keep the existing design fixture that proves Gantt vendor rows still join by overlap despite vendor skill mismatch.

### UPDATED: scripts/test-render-review-phase-detail.md

- Document the new Mermaid validation contract.
- State that local runs may skip generated Mermaid validation when no existing CLI is available.
- State that GitHub Actions CI must not skip generated Mermaid validation.
- State that the harness precheck exists to prevent the harness itself from running `npm ci`.
- State that CI is responsible for installing the Mermaid toolchain before the harness shard runs.

### UPDATED: .github/workflows/ci.yaml

- Update the `test-harnesses` job so the shard that currently runs `test-render-review-phase-detail` has Mermaid CLI available before `make test-harnesses-12`.
- Add conditional Node setup for `matrix.shard == 12`.
- Add conditional caches for:
  - `mermaid-lint/node_modules`.
  - `~/.cache/puppeteer`.
- Add a conditional `npm ci` step for `matrix.shard == 12`, using `mermaid-lint/package-lock.json`.
- Reuse the retry environment from the existing `lint-mermaid` job.
- Keep this install outside `scripts/test-render-review-phase-detail.sh`.
- Add a comment that this condition must stay in sync with the Makefile shard containing `test-render-review-phase-detail`.
- Do not rely on the separate `lint-mermaid` job to validate generated harness output, because it only lints changed Markdown files.

### UPDATED: docs/linting.md

- Update the CI description to mention generated Mermaid validation in the renderer harness.
- State that the Mermaid toolchain is installed for the relevant test-harness shard.
- Keep the existing distinction:
  - `lint-mermaid` validates changed committed Markdown fences.
  - `test-render-review-phase-detail` validates generated Mermaid fences from the renderer fixture.

### UPDATED: python/progress_report.py

- Add `_all_round_dirs_inflight(rounds_root: Path) -> bool`.
  - Use `_round_dirs(rounds_root)`.
  - Return `False` when no round dirs exist.
  - Return `True` only when every discovered `round-N` dir lacks `round-meta.json`.
  - Check for `round-meta.json` presence only.
  - Do not open or parse `round-meta.json`.
  - Treat a present but unreadable `round-meta.json` as completed for this skip guard when presence can be observed.
  - Catch filesystem errors and keep best-effort progress behavior.
- In `_render_step5`:
  - Keep the current liveness header behavior.
  - Compute the selected review rounds root with `_review_rounds_root(implement_tmpdir, run_id)`.
  - If `_all_round_dirs_inflight(selected_root)` is true, return the header only.
  - Otherwise call `_render_review_detail` as before.
- In `_render_design_plan_review`:
  - Keep the current liveness header behavior.
  - Before calling `_render_design_review_detail`, check `_all_round_dirs_inflight(design_tmpdir / "plan-review")`.
  - If true, return the header only.
  - Otherwise call `_render_design_review_detail` as before.
- Leave `_call_render_phase_detail_script` passing `--no-gantt`.
- Leave final report and final summary paths unchanged.

### UPDATED: python/test_progress_report.py

- Update existing tests that expect appended detail from a live in-progress round:
  - Add a minimal `round-meta.json` fixture when the test expects detail rendering.
- Add implement live-progress coverage:
  - Create a live `round-1` with `panel-manifest.ndjson`.
  - Do not create `round-meta.json`.
  - Monkeypatch `_render_review_detail` to fail if called.
  - Assert `_render_step5` returns the liveness header.
  - Assert the result does not include `No review rounds completed.`.
- Add implement mixed-state coverage:
  - Create one selected rounds root with at least one completed round containing `round-meta.json`.
  - Include another in-flight round without `round-meta.json`.
  - Monkeypatch `_render_review_detail` to return a sentinel detail string.
  - Assert detail rendering still occurs.
- Add design live-progress coverage:
  - Create `plan-review/round-1` with a fresh manifest.
  - Do not create `round-meta.json`.
  - Monkeypatch `_render_design_review_detail` to fail if called.
  - Assert `_render_design_plan_review` returns the liveness header.
  - Assert the result does not include `No review rounds completed.`.
- Add design mixed-state coverage if updated detail tests do not already cover it:
  - Include at least one completed `round-meta.json`.
  - Include one in-flight round without `round-meta.json`.
  - Assert detail rendering still occurs.

### UPDATED: skills/design/scripts/render-final-summary.md

- Apply after #4062 has merged.
- Clarify that final summaries do not pass `--no-gantt`.
- State that final summaries render reviewer timing Gantt charts when timing data is available.
- State that valid roots with zero completed rounds render `No review rounds completed.`.
- State that live progress may skip the renderer for in-flight-only plan reviews.
- State that this final-summary helper does not skip the renderer for that case.

### UPDATED: skills/implement/scripts/write-final-report.md

- Apply after #4062 has merged.
- Keep the existing final-report contract.
- Clarify that final reports still render `No review rounds completed.` for valid selected roots with zero completed rounds.
- Clarify that terminal progress is the caller that skips detail for in-flight-only rounds.
- Keep `--no-gantt` wording tied to terminal progress only.

## Edge cases

- Pre-#4062 trees may not have the Gantt harness call sites this plan references.
- A selected rounds root with no round dirs does not trigger the in-flight-only skip guard.
- A selected rounds root with round dirs but no `round-meta.json` returns only the live progress header.
- A selected rounds root with one completed round and one in-flight round still renders detail for completed rounds.
- Design live progress with a fresh manifest but no `round-meta.json` still shows reviewer counts.
- Final summaries and final reports still show `No review rounds completed.` for valid roots with zero completed rounds.
- Gantt charts still include reviewer vendor rows by overlap only.
- Gantt round windows still consider same-number round rows from other skills.
- Table Time and Cost ignore same-number round rows from other skills.
- Token-ledger cost records inside only a wider other-skill round window do not affect the selected skill table Cost or Total.
- Local hosts without Mermaid CLI still get an explicit `SKIP:` breadcrumb.
- GitHub Actions CI without Mermaid CLI fails instead of skipping.
- GitHub Actions CI validates generated Mermaid output from the renderer harness, not just changed committed Markdown files.

## Failure modes

- If #4062 is not merged, defer the Gantt harness, CI Mermaid toolchain setup for the renderer harness, and doc-sync parts rather than guessing missing call sites.
- If Mermaid CLI tooling is unavailable locally, the shell harness prints `SKIP:` and continues.
- If Mermaid CLI tooling is unavailable in GitHub Actions CI or `LARCH_MERMAID_REQUIRED=1`, the shell harness prints `FAIL:` and exits non-zero.
- If Mermaid CLI tooling is absent, the shell harness does not invoke the Python lint command.
- If Mermaid CLI tooling is available and parse/render validation fails, the shell harness prints `FAIL:` and exits non-zero.
- If `python3 python/cli.py lint mermaid-fences` exits `2` locally, treat it as unavailable tooling in this harness.
- If `python3 python/cli.py lint mermaid-fences` exits `2` in required validation mode, treat it as a real failure.
- If `python3 python/cli.py lint mermaid-fences` exits any other non-zero status, treat it as a real lint failure.
- If the CI shard toolchain install fails, CI fails before the harness can silently skip generated Mermaid validation.
- If round dir reads fail in `progress_report.py`, keep existing best-effort behavior and avoid raising.
- If `round-meta.json` is unreadable but present, treat it as completed for the progress skip guard.
- If `round-meta.json` is unreadable, let the renderer degrade as it already does.

## Testing strategy

- Confirm #4062 has merged before running or updating Gantt harness, CI Mermaid setup, and Gantt doc-sync cases.
- Run `bash scripts/test-render-review-phase-detail.sh`.
- Run `LARCH_MERMAID_REQUIRED=1 bash scripts/test-render-review-phase-detail.sh` on a host with the Mermaid toolchain installed.
- Verify the shell harness passes on hosts without Mermaid CLI tooling by observing the `SKIP:` breadcrumb outside required validation mode.
- Verify the shell harness fails when `LARCH_MERMAID_REQUIRED=1` and no Mermaid CLI is available.
- Verify the shell harness does not create or modify Mermaid dependency directories when Mermaid CLI tooling is absent.
- Verify Mermaid parse validation runs and hard-fails syntax errors when Mermaid CLI tooling is available.
- Verify the CI `test-harnesses` shard that contains `test-render-review-phase-detail` installs Mermaid CLI before running the harness.
- Run `PYTHONPATH=python pytest -q python/test_progress_report.py`.
- Run `bash scripts/relevant-checks.sh`.


## Acceptance

- [ ] `scripts/render-review-phase-detail.sh`: dual window split (skill-filtered `table_rrange` for Time/Cost, unfiltered `gantt_rrange` for Gantt) passes test harness
- [ ] `scripts/test-render-review-phase-detail.sh`: skill-window contamination test passes; `assert_mermaid_valid` runs after all Gantt-producing cases; Gantt preservation regression passes
- [ ] `python/progress_report.py`: `_all_round_dirs_inflight()` returns correct values; live progress returns header-only when all dirs inflight; returns detail when mixed state
- [ ] `python/test_progress_report.py`: in-flight and mixed-state tests pass for both implement and design paths
- [ ] `skills/design/scripts/render-final-summary.md`: documents in-progress-vs-no-rounds distinction, no-gantt suppression contract, and final-summary Gantt behavior
- [ ] `skills/implement/scripts/write-final-report.md`: consistent with render-final-summary.md Gantt/no-rounds contract
- [ ] `.github/workflows/ci.yaml`: shard 12 installs Mermaid toolchain before test-render-review-phase-detail harness
- [ ] `docs/linting.md`: mentions generated Mermaid validation in renderer harness alongside existing lint-mermaid distinction
- [ ] `scripts/test-render-review-phase-detail.md`: documents optional-vs-required Mermaid validation contract
- [ ] `bash scripts/relevant-checks.sh` passes

diff_lines: 238

## Test plan
(no test plan section in plan-file)
