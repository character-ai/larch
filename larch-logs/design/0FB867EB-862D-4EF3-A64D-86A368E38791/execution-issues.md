### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=114 (baseline 32, ratio 3.56) / DIFF_LINES=185 (baseline 110, ratio 1.68) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=168 (baseline 32, ratio 5.25) / DIFF_LINES=215 (baseline 110, ratio 1.95) ≥ ×2, under absolute limits; proceeding.**
  ```


- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=223 (baseline 32, ratio 6.97) / DIFF_LINES=310 (baseline 110, ratio 2.82) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=237 (baseline 32, ratio 7.41) / DIFF_LINES=260 (baseline 110, ratio 2.36) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=278 (baseline 32, ratio 8.69) / DIFF_LINES=330 (baseline 110, ratio 3) ≥ ×2, under absolute limits; proceeding.**
  ```
### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
❌ cursor agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)
--- failed agent stderr tail ---
b: Provider Error We're having trouble connecting to the model provider. This might be temporary - please try again in a moment.
Failed with exit code 1 after 20s. Output size: 0 bytes.
--- end failed agent stderr tail ---
===== diag =====
b: Provider Error We're having trouble connecting to the model provider. This might be temporary - please try again in a moment.
Failed with exit code 1 after 20s. Output size: 0 bytes.
  ```

- **Step review Step 2 — codex-review failed (exit 124 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
Reading additional input from stdin...
⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1868s elapsed, output 0 bytes)
--- failed agent stderr tail ---
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1868s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
===== diag =====
Timed out after 1868s (limit: 1860s). Process was killed after exceeding the timeout. Output size: 0 bytes.
===== events.jsonl (filtered) =====
{"type":"item.started","item":{"id":"item_0","type":"command_execution","command":"/bin/bash -lc \"sed -n '1,240p' <TMPDIR>/plan.txt && printf '\\\\n---END PLAN CHUNK---\\\\n' && sed -n '241,520p' <TMPDIR>/plan.txt\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"/bin/bash -lc \"sed -n '1,240p' <TMPDIR>/plan.txt && printf '\\\\n---END PLAN CHUNK---\\\\n' && sed -n '241,520p' <TMPDIR>/plan.txt\"","aggregated_output":"## Plan\n\n## Files to modify/create\n\n### UPDATED: `python/progress_report.py`\n\nAdd `json` and `re` imports if needed.\n\nAdd shared script-invocation helpers before `_render_review_detail`:\n\n- `_latest_token_ledger(tmpdir)`: returns the newest `larch-tokens-*.jsonl`, or `None`.\n- `_call_render_phase_detail_script(rounds_root, skill, timing_ledger, token_ledger)`: builds and runs `scripts/render-review-phase-detail.sh`.\n- Refactor `_render_review_detail(implement_tmpdir, run_id)` to keep its signature and behavior, but delegate to the new helper with `skill=\"implement\"`.\n\nAdd design-specific review helpers:\n\n- `_is_design_plan_review_step(step_label)`: returns true only for the canonical plan-review timing label.\n  - Match `Step 3 — plan review`.\n  - Allow optional `design ` prefix.\n  - Allow optional trailing timing/detail text after the plan-review phrase.\n  - Do not match `Step 3.5`, `Step 3b`, or other Step 3 substeps.\n- `_manifest_output_paths(manifest)`: parse NDJSON with stdlib `json`, return valid `.output` paths in manifest row order.\n- `_paths_file_output_paths(path)`: read line-oriented output-path sidecars.\n- `_count_nonempty_paths(paths)`: count unique existing files with size greater than zero.\n- `_design_panel_manifest(design_tmpdir, round_dir)`: prefer `round_dir/panel-manifest.ndjson` when present and non-empty, else use `design_tmpdir/plan-review-slots.ndjson`.\n- `_fresh_output_sidecar(manifest)`: return `manifest.output-files` only when it exists and has `mtime >= manifest.mtime`.\n- `_design_returned_reviewers(design_tmpdir, round_dir, manifest)`: count returned reviewers from one authoritative source.\n  - If `manifest` has output paths and a fresh sidecar exists, prefer sidecar paths.\n  - Cap the returned count at the manifest slot count.\n  - If `manifest` has output paths and no fresh sidecar exists, count non-empty manifest `.output` paths.\n  - If no manifest output paths are available, return `0`.\n  - Do not fall back to globbing `design_tmpdir/*-plan-*-output.txt`.\n  - This avoids stale previous-round outputs and retry paths producing counts greater than the slot count.\n- `_design_elapsed(round_dir, step_start_s)`: use `round-start-s` when present; otherwise use the Step 3 timing mark start passed by `_render_design`.\n\nAdd `_render_design_review_detail(design_tmpdir)`:\n\n- Delegates to `_call_render_phase_detail_script`.\n- Uses `rounds_root=design_tmpdir / \"plan-review\"`.\n- Uses `skill=\"design\"`.\n- Passes `design_tmpdir / \"timing-ledger.tsv\"` when present.\n- Passes the latest design token ledger when present.\n\nAdd `_render_design_plan_review(design_tmpdir, start_s)`:\n\n- Resolve `rounds_root = design_tmpdir / \"plan-review\"` and `round_dir = _current_round_dir(rounds_root)`.\n- If no round dir exists, return `\"\"`.\n- Resolve `manifest = _design_panel_manifest(design_tmpdir, round_dir)`.\n- If no usable manifest exists or it has no output paths, return `\"\"` so generic progress renders.\n- Compute `total` from the selected manifest.\n- Compute `returned` from the selected manifest or its fresh sidecar only.\n- Compute elapsed from `round-start-s`, falling back to the Step 3 timing mark.\n- Render a header like:\n  - `Step 3 plan review - round N in progress`\n  - `reviewers: returned/total returned | elapsed: value`\n- Append `_render_design_review_detail` output when available.\n- Return `\"\"` when there is no round dir or no usable live design review manifest.\n\nUpdate `_render_design`:\n\n- Keep reading `step_label, start_s = _latest_timing_mark(...)`.\n- Call `_render_design_plan_review(run.tmpdir, start_s)` only when `_is_design_plan_review_step(step_label)` returns true.\n- Return that rich report when non-empty.\n- Otherwise fall through to `_render_generic(\"design\", step_label, start_s, run.tmpdir)`.\n\n### UPDATED: `python/test_progress_report.py`\n\nAdd tests for the design path:\n\n1. No `plan-review/round-N` dirs returns no rich plan-review report and falls through to generic.\n2. Header-only render with round-local `panel-manifest.ndjson` and no detail.\n3. Render with detail appends the stripped detail section.\n4. `_render_design` uses the rich view when the timing label is `design Step 3 — plan review`.\n5. `_render_design` skips the rich view for non-Step 3 labels.\n6. Step 3 plan-review label with no usable rounds falls through to generic.\n7. Design detail argv includes `--skill design`, `--rounds-root <design_tmpdir>/plan-review`, and the design timing ledger.\n8. Active live Step 3 regression:\n   - `plan-review/round-1/` exists.\n   - No round-local `panel-manifest.ndjson`.\n   - No `round-start-s`.\n   - `DESIGN_TMPDIR/plan-review-slots.ndjson` has three output paths.\n   - Two manifest output files are non-empty.\n   - Assert the report shows `2/3 returned`.\n   - Assert elapsed uses the Step 3 timing mark instead of `unknown`.\n9. Step 3.5 regression:\n   - Timing label is `design Step 3.5 — gate B`.\n   - A usable `plan-review/round-1/` and root manifest exist.\n   - Assert `_render_design` returns generic progress, not the rich plan-review view.\n10. Step 3b regression:\n   - Timing label is `design Step 3b — arch diagram`.\n   - A usable `plan-review/round-1/` and root manifest exist.\n   - Assert `_render_design` returns generic progress, not the rich plan-review view.\n11. Stale root output regression:\n   - Current `round-2/` exists.\n   - Current manifest is absent or empty.\n   - Old `*-plan-*-output.txt` files exist in `DESIGN_TMPDIR`.\n   - Assert rich rendering returns `\"\"` and `_render_design` falls through to generic.\n12. Stale sidecar regression:\n   - Manifest has one output path.\n   - `manifest.output-files` is older than the manifest and points at a non-empty old output.\n   - Manifest output is empty.\n   - Assert returned count is `0/1`.\n13. Fresh retry sidecar regression:\n   - Manifest has one output path.\n   - Manifest output and fresh sidecar retry output are both non-empty.\n   - Assert returned count is capped at `1/1`, not `2/1`.\n\n## Approach\n\nThe existing implement Step 5 renderer assumes round-local artifacts are live.\n\nDesign Step 3 differs:\n\n- Live reviewer slots are in `DESIGN_TMPDIR/plan-review-slots.ndjson`.\n- Live reviewer outputs are at paths listed by that manifest.\n- Round-local `panel-manifest.ndjson`, `round-meta.json`, and summary files may not exist until end-of-round synthesis.\n- `round-start-s` may be absent while the timing ledger already has the active Step 3 mark.\n\nThe design renderer should still use `plan-review/round-N/` to choose the current round number and to render completed detail tables.\n\nIt should not use broad Step 3 substring matching.\n\nIt should not use root glob fallback output files.\n\nFor active rounds, it should read design-native root artifacts:\n\n- Total reviewers: selected manifest row count.\n- Returned reviewers: non-empty authoritative output paths from the selected manifest, or from its fresh sidecar when present.\n- Elapsed: `round-start-s` when present, else the Step 3 timing mark start.\n\nThis preserves code reuse for generic round discovery and detail rendering while avoiding implement-only assumptions about round-local live artifacts.\n\n## Edge cases\n\n- `plan-review/` absent: return `\"\"`; `_render_design` uses generic progress.\n- Round dir exists but round-local manifest is absent: use `DESIGN_TMPDIR/plan-review-slots.ndjson`.\n- Root manifest is absent, empty, or unreadable: return `\"\"`; `_render_design` uses generic progress.\n- Output sidecar exists from a previous round: ignore it unless its mtime is at least the manifest mtime.\n- Fresh sidecar exists with retry paths: prefer sidecar paths, but cap returned count at total manifest slots.\n- Output file path is duplicated: count it once, and never exceed total slots.\n- `round-start-s` absent: use the Step 3 timing mark start.\n- Both round start and Step 3 timing start are absent: elapsed is `unknown`.\n- `render-review-phase-detail.sh` absent or returns non-zero: omit detail and keep the header.\n- Step 3.5 or Step 3b labels: always fall through to generic progress.\n- Step 3 plan-review label with an empty round dir and no usable manifest: return `\"\"` and fall through to generic.\n\n## Testing strategy\n\nRun `make py-test`.\n\nThe active-round regression must model the live `/design` layout, not only terminal metadata:\n\n- Empty `plan-review/round-1/`.\n- Root `plan-review-slots.ndjson`.\n- Root reviewer output files named by manifest `.output` paths.\n- Step 3 timing mark.\n- No round-local `panel-manifest.ndjson`.\n- No `round-start-s`.\n\nAdd focused regressions for:\n\n- Step 3.5 and Step 3b labels.\n- Stale root outputs when no current manifest exists.\n- Stale `.output-files` sidecars.\n- Fresh retry sidecars that must not count more than one return per slot.\n\nExisting `_render_review_detail` tests should continue to pass because its signature and external behavior remain unchanged.\n\ndiff_lines: 215\n\n---END PLAN CHUNK---\n","exit_code":0,"status":"completed"}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"/bin/bash -lc \"sed -n '1,260p' python/progress_report.py && printf '\\\\n---NEXT---\\\\n' && sed -n '261,620p' python/progress_report.py && printf '\\\\n---TESTS1---\\\\n' && sed -n '1,320p' python/test_progress_report.py && printf '\\\\n---TESTS2---\\\\n' && sed -n '321,760p' python/test_progress_report.py\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"/bin/bash -lc \"sed -n '1,260p' python/progress_report.py && printf '\\\\n---NEXT---\\\\n' && sed -n '261,620p' python/progress_report.py && printf '\\\\n---TESTS1---\\\\n' && sed -n '1,320p' python/test_progress_report.py && printf '\\\\n---TESTS2---\\\\n' && sed -n '321,760p' python/test_progress_report.py\"","aggregated_output":"\"\"\"On-demand progress reports for live larch runs.\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport os\nimport re\nimport shlex\nimport subprocess\nimport time\nfrom dataclasses import dataclass\nfrom datetime import UTC, datetime\nfrom pathlib import Path\n\nTIMING_MARK_MIN_COLS = 5\nSECONDS_PER_MINUTE = 60\nSECONDS_PER_HOUR = 3600\n\n_MD_TABLE_SEP_RE = re.compile(r\"^\\|[ :\\-|]+\\|$\")\n_MD_BOLD_RE = re.compile(r\"\\*\\*([^*\\n]+)\\*\\*\")\n_MD_ITALIC_RE = re.compile(r\"(?<![_\\w])_([^_\\n]+)_(?![_\\w])\")\n_MD_HEADING_RE = re.compile(r\"^#{1,6} \")\nSHIP_PR_PHASES = frozenset({\n    \"checks\",\n    \"ci-initial\",\n    \"ci-merge\",\n    \"pr-prep\",\n    \"pr-create\",\n    \"pr-push\",\n    \"merge\",\n    \"postmerge\",\n    \"rebase\",\n    \"rebase-failed\",\n    \"stalled\",\n    \"done\",\n})\n\n\ndef _strip_md_for_terminal(text: str) -> str:\n    \"\"\"Remove Markdown decorators for plain-text terminal display.\"\"\"\n    lines: list[str] = []\n    for raw in text.splitlines():\n        if _MD_TABLE_SEP_RE.match(raw.strip()):\n            continue\n        out = _MD_HEADING_RE.sub(\"\", raw, count=1)\n        out = _MD_BOLD_RE.sub(r\"\\1\", out)\n        out = _MD_ITALIC_RE.sub(r\"\\1\", out)\n        lines.append(out)\n    return \"\\n\".join(lines)\n\n\n@dataclass(frozen=True)\nclass LiveRun:\n    skill: str\n    tmpdir: Path\n    cwd: str\n    pointer: Path\n    mtime: float\n\n\ndef _sessions_root() -> Path:\n    return Path.home() / \".cache\" / \"larch\" / \"sessions\"\n\n\ndef _canonical_repo_path(path: str) -> str:\n    if not path:\n        return \"\"\n    try:\n        return os.path.realpath(path)\n    except OSError:\n        return path\n\n\ndef _read_env_file(path: Path) -> dict[str, str]:\n    data: dict[str, str] = {}\n    try:\n        lines = path.read_text(encoding=\"utf-8\", errors=\"replace\").splitlines()\n    except OSError:\n        return data\n    for raw_line in lines:\n        line = raw_line.strip()\n        if not line or line.startswith(\"#\"):\n            continue\n        if line.startswith(\"export \"):\n            line = line[len(\"export \") :].strip()\n        if \"=\" not in line:\n            continue\n        key, value = line.split(\"=\", 1)\n        if not re.match(r\"^[A-Z_][A-Z0-9_]*$\", key):\n            continue\n        try:\n            parsed = shlex.split(value, posix=True)\n        except ValueError:\n 
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-innovation (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED timing-ledger.sh: WARNING: unknown task-kind: cursor-phase1-cursor-plan-innovation 
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-innovation (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=TIMED_OUT timing-ledger.sh: WARNING: unknown task-kind: codex-phase1-codex-plan-innovation 
  ```
