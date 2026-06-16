## Plan

Implement the approved five-item scope with minimum changes, integrating accepted reviewer corrections for fence-aware bullet counting, `body_text` fallback test coverage, and size-trailer materialization fixtures.

1. Fix `step_7a.py`: parenthesize the `run_id` fallback so `LARCH_RUN_ID` is tried before `session-id`.
2. Fix `pr_body.py`: add one shared fence-aware bullet-count helper and use it for `execution-issues.md`, structured NDJSON rows, and `body_text` fallback.
3. Fix `execution_issues.py`: insert at the end of the matching section, before the next `### ` heading.
4. Fix `bootstrap.py`: strip only recognized `/design` provenance in the terminal metadata region (including above optional size trailers), not globally.
5. Fix `agents.py`: resolve CI launcher workdirs through `_resolve_review_codex_workdir`; preserve Cursor fix-role `stdout` stall semantics; use an omitted-argument sentinel for `launch_codex_exec_main --workdir`; apply workdir resolution before directory validation.

`plan-from-issue.txt` stays untouched so preflight can still read provenance metadata.

## Files to modify/create

### UPDATED: python/step_7a.py

Fix precedence of the `run_id` fallback expression.

- Wrap the `session-id` read in its own conditional expression.
- Ensure the `else ""` binds only to the `session-id` fallback.
- Result shape:
  - `run_id = _read_kv(session_env, "LARCH_RUN_ID") or ((implement_tmpdir / "session-id").read_text(...).strip() if (implement_tmpdir / "session-id").is_file() else "")`

### UPDATED: python/test_step_7a.py

Add a regression test for absent `session-id`.

- Write `session-env.sh` with `LARCH_RUN_ID=run-99`.
- Do not create `session-id`.
- Call `run_step7a(tmp_path)` without passing `run_id=`.
- Patch diagram, subprocess, and log-flush side effects as existing tests do.
- Assert `_run_log_flush` receives `run_id="run-99"`.

### UPDATED: python/pr_body.py

Align issue counting across all paths in `_refresh_issue_counts`.

- Add a small shared helper, for example `_count_markdown_bullets_outside_fences(text: str) -> int`.
- Track Markdown fence state (` ``` ` open/close toggles).
- Count lines matching `^- ` only outside fenced blocks.
- Do not count bullets inside fenced diagnostics (for example run-log append-failure tool output).
- Apply the helper to:
  - `execution-issues.md` section parsing (replace the bold-only `bullet_re` path).
  - Structured NDJSON row bodies via `str(row.get("body", ""))`, using `max(1, bullet_count)` per matching row.
  - `body_text` fallback section parsing (replace the bold-only regex there too).
- Preserve category split:
  - `Tool Failures` and `External Reviewer Issues` count as exec issues.
  - `Warnings` counts as warnings.
- Leave the non-section fallback category-string counting unchanged unless sharing the helper makes the edit smaller.

### UPDATED: python/test_pr_body.py

Add focused tests for consistent fence-aware bullet counts.

- Cover `execution-issues.md` with plain bullets `- a` and `- b`; assert `(2, 0)` or equivalent for the seeded section.
- Cover structured NDJSON rows:
  - one `Tool Failures` row with `- a\n- b\n`
  - one `Warnings` row with `- **step5**: c\n- **step5**: d\n`
- Assert `_refresh_issue_counts` returns `(2, 2)`.
- Add a structured matching row with no bullet lines; assert that row still counts as `1`.
- Add a fenced-diagnostics regression:
  - seed a `Tool Failures` body containing a fenced block with a line like `- failed check` inside the fence plus one real bullet outside
  - assert only the outside bullet is counted (not the fenced line).
- Add one `body_text` fallback regression:
  - write `execution-issues.ndjson` with at least one non-dict JSON row so `all(isinstance(row, dict) ...)` is false
  - include dict rows whose `body` contains `### Tool Failures` and plain `-` bullets
  - assert `_refresh_issue_counts` counts those bullets through the fallback path, not the per-record structured path.
- Keep tests isolated under `tmp_path`.

### UPDATED: python/execution_issues.py

Fix `append_execution_issue` section insertion.

- Keep the existing idempotency check.
- If `### {category}` is absent, create the heading at EOF as now.
- If `### {category}` exists:
  - Find that heading.
  - Find the next later line starting with `### `.
  - Insert the new entry before the next heading.
  - If no later heading exists, insert at EOF within the section.
- Preserve one trailing newline.

### UPDATED: python/test_execution_issues.py

Add a mid-file insertion regression test.

- Seed:
  - `### Tool Failures`
  - `- old`
  - `### Warnings`
  - `- warn`
- Append a new `Tool Failures` entry.
- Assert the new entry appears before `### Warnings`.
- Append the same entry again.
- Assert it is not duplicated.

### UPDATED: python/bootstrap.py

Strip materialized plan provenance only in the terminal metadata region.

- Add `_strip_plan_provenance_headers(text: str) -> str` near `_phase_plan`.
- Recognize only:
  - `review_status:`
  - `rounds_completed:`
- Locate the final `diff_lines: <N>` line.
- Walk backward through the terminal trailer region (same semantics as `python/design_publish.py` `_is_trailer_region_line` / optional size trailers).
- Remove only contiguous recognized provenance lines in that region.
- Preserve:
  - matching lines in plan prose, examples, and code fences
  - optional size trailers (`diff_added:`, `diff_deleted:`, `mechanical_churn:`)
  - `diff_lines:`
- Prefer reusing or factoring trailer-region detection from `python/design_publish.py` if practical.
- Replace `shutil.copyfile(plan_src, st.plan_file)` with read, strip, write.
- Do not modify `preflight/plan-from-issue.txt`.

### UPDATED: python/test_bootstrap.py

Add materialization coverage for trailer-region stripping.

- Create `preflight/plan-from-issue.txt` with:
  - body/prose lines starting `review_status:` and `rounds_completed:` (must survive)
  - terminal provenance lines in wire-format order above optional size trailers:
    - `review_status: complete`
    - `rounds_completed: 5`
    - `diff_added: 10`
    - `diff_deleted: 2`
    - `mechanical_churn: false`
    - `diff_lines: 10`
- Run `_phase_plan` with existing external side effects patched.
- Assert `impl/plan.txt` removes only the terminal provenance lines immediately above the size-trailer block.
- Assert body/prose provenance-looking lines survive.
- Assert optional size trailers and `diff_lines: 10` remain.
- Assert `preflight/plan-from-issue.txt` remains unchanged.

### UPDATED: skills/implement/references/preflight-plan-audit.md

Clarify audit handling of `/design` provenance.

- Keep `$PREFLIGHT_TMPDIR/plan-from-issue.txt` as the source.
- Instruct the audit to ignore recognized `/design` provenance only in the terminal metadata region near `diff_lines:` (above optional size trailers when present).
- Name exact prefixes:
  - `review_status:`
  - `rounds_completed:`
- State that matching lines in plan prose, examples, or code fences still count as plan content.
- Do not tell the audit to edit or strip the source file.

### UPDATED: scripts/test-plan-adequacy-audit.sh

Add structure assertions for the audit note.

- Assert the audit reference mentions `review_status:`.
- Assert it mentions `rounds_completed:`.
- Assert it scopes ignoring to the terminal metadata region or near `diff_lines:`.
- Retain existing assertions.

### UPDATED: python/agents.py

Resolve CI launcher workdirs through `_resolve_review_codex_workdir`.

For `launch_codex_ci_main`:

- Replace `workdir = str(Path.cwd())` with `workdir = _resolve_review_codex_workdir(str(Path.cwd()))`.
- Use `workdir` for `-C`, `--add-dir`, trust config, retry `cwd`, and `OUTER_LAUNCHER_WORKDIR`.

For `launch_cursor_ci_main`:

- Compute `workdir = _resolve_review_codex_workdir(str(Path.cwd()))`.
- Use `workdir` for `--workspace` and `OUTER_LAUNCHER_WORKDIR`.
- Preserve stall behavior:
  - `stdout` when `args.role == "fix"`
  - `tree:{workdir}` otherwise.

For `launch_codex_exec_main`:

- Make omitted `--workdir` distinguishable from explicit `--workdir` (`default=None` or an argparse sentinel).
- If omitted:
  - resolve `_resolve_review_codex_workdir(str(Path.cwd()))`
  - validate the resolved directory
  - launch with the resolved directory
- If supplied:
  - preserve the caller value unchanged (even when equal to `str(Path.cwd())`)
  - validate and launch with that explicit value
- Apply resolution before directory validation.
- Do not infer omission by comparing the value to `Path.cwd()`.

### UPDATED: python/test_agents.py

Add workdir-resolution assertions.

For `launch_codex_ci_main`:

- Set up a fake consumer repo; patch `_resolve_review_codex_workdir` to return it.
- Patch auth, model, binary, and external-run helpers to avoid launching Codex.
- Assert spawned argv uses the consumer repo for `-C`, `--add-dir`, and trust config.
- Assert `.meta` contains `OUTER_LAUNCHER_WORKDIR=<consumer_repo>`.

For `launch_cursor_ci_main` non-fix role:

- Assert `--workspace` and `.meta` use the consumer repo.
- Assert stall monitoring uses `tree:<consumer_repo>`.

For `launch_cursor_ci_main` fix role:

- Assert `--workspace` and `.meta` use the consumer repo.
- Assert stall monitoring still uses `stdout`.

For `launch_codex_exec_main` default workdir:

- Call without `--workdir`; arrange raw cwd differing from resolved consumer repo.
- Patch `_resolve_review_codex_workdir` to return the consumer repo.
- Assert directory validation and launch use the resolved repo.

For `launch_codex_exec_main` explicit workdir:

- Pass `--workdir` explicitly, including a value equal to `str(Path.cwd())`.
- Assert `_resolve_review_codex_workdir` is not used for that explicit value.
- Assert validation and launch preserve the explicit workdir.

## Edge cases

- `session-env.sh` has `LARCH_RUN_ID`, but `session-id` is absent.
- NDJSON body has plain bullets such as `- a` and bold-label bullets such as `- **step5**: a`.
- NDJSON matching row has no bullets (`max(1, 0)` → 1).
- Fenced diagnostics contain `- ...` lines that must not inflate counts.
- `body_text` fallback activates when NDJSON rows are not all dicts.
- Execution issue sections appear in any order.
- `review_status:` or `rounds_completed:` appears in normal plan content or code fences.
- `/design` provenance appears above optional size trailers before `diff_lines:`.
- Cursor CI fix role needs `stall_channel="stdout"`.
- Explicit `launch_codex_exec_main --workdir` must never be overridden.

## Failure modes

- Global provenance stripping can delete valid plan content.
- Trailer detection that only scans lines adjacent to `diff_lines:` can miss provenance above size trailers.
- Raw `^-` counting without fence tracking can inflate issue counts from fenced tool output.
- Missing `body_text` fallback tests can leave the fallback on the old bold-only regex.
- Per-record NDJSON counting undercounts multi-bullet rows.
- EOF insertion can put entries under the wrong execution-issue section.
- Equality-based `--workdir` omission detection can override explicit same-cwd values.
- Validating raw argparse default before resolution can launch from the plugin cache.
- Cursor CI stall changes can break fix-role stdout monitoring.

## Testing strategy

Run focused tests:

```bash
python3 -m pytest python/test_step_7a.py python/test_pr_body.py python/test_execution_issues.py python/test_bootstrap.py python/test_agents.py -x
```

Run the audit reference structure test:

```bash
make test-plan-adequacy-audit
```

Run full validation:

```bash
make py-lint
make py-test
make lint
```

## Acceptance

- `run_step7a` uses `LARCH_RUN_ID=run-99` when `session-id` is absent.
- All issue-count paths use fence-aware top-level `^- ` bullet counting.
- Fenced diagnostic lines do not inflate issue counts.
- Structured NDJSON rows count per bullet with `max(1, count)` per matching row.
- `body_text` fallback uses the same fence-aware bullet helper.
- Execution issue append inserts inside the target section.
- `IMPLEMENT_TMPDIR/plan.txt` strips only terminal provenance metadata above size trailers.
- Optional size trailers and `diff_lines:` survive materialization.
- `preflight/plan-from-issue.txt` remains unchanged.
- The plan audit ignores only terminal `/design` provenance near `diff_lines:`.
- Codex CI and Cursor CI launch from the resolved consumer repo.
- Cursor CI fix role keeps `stdout` stall monitoring.
- Default Codex exec resolves the consumer repo before validation.
- Explicit Codex exec `--workdir` is honored unchanged.
- Focused tests, `make test-plan-adequacy-audit`, `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 2
diff_added: 310
diff_deleted: 50
mechanical_churn: false
diff_lines: 360
