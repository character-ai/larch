# Review Round 1

- Mode: `diff`
- 11 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_1: --snapshot-original honored on non-step2b sites
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_shared_step2b_postplan_body` appends `--snapshot-original` whenever `parsed.snapshot_original` is true, even for non-`step2b` sites (e.g. gate-b, discussion-round2). Bash only keyed off site name. A forwarded `--snapshot-original` on those sites can re-seed the drift baseline and change `DRIFT_TRIGGER_FIRED` vs Bash parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Append `--snapshot-original` only for site `step2b` or empty site; do not honor the flag on other sites.


### FINDING_10: test-design-structure.sh G5 pins removed, not retargeted
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-launcher-docs-output.txt
- **Severity**: important
- **Concern**: The branch replaced a ~944-line structural guard with an ~81-line Step 0/1-only harness and dropped plan-required G5 pins (`assert_postplan_thin_fence`, `assert_step2b_drafter_folded_postplan_contract`, Gate B / settle argv pins, launcher fence validation, wrapper pause ordering, Step 2 CLI registry coverage). `skills/design/scripts/design-step35-settle.md:86` still claims settle contract coverage via `test-design-structure.sh`, which is no longer true. Regressions in `POSTPLAN_RC` pairing, drafter wrapper-row ordering, fatal emit rc mapping, or launcher `"$@"` forwarding can merge without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Implement the plan checklist pins before retiring Bash wrappers.
  - From cursor-specialist-testing-output.txt: Restore `assert_postplan_thin_fence` and `assert_step2b_drafter_folded_postplan_contract` pins against `design_lifecycle.py`; extend `ported_verbs`/`retired_paths` to Step 2 wrappers.
  - From codex-specialist-testing-output.txt: Restore the planned assertions and add launcher execution coverage.
  - From dyn-launcher-docs-output.txt: Restore the retargeted G5 assertion block from the plan checklist (pointing at `python/design_lifecycle.py`, `python/session_env.py`, and the argv-array settle call) instead of deleting the old harness wholesale; update settle-doc coverage prose to name the surviving pytest / structure pins.
  - From dyn-launcher-docs-output.txt: Extend the harness with the plan's companion assertion: exempt launcher-routed retired Step 2 names from on-disk wrapper requirements, and grep `session_env.py` / `cli.py` for each retired name → correct `python/cli.py` verb with `"$@"` forwarding.


### FINDING_11: Drafter pre-draft pause ordering diverges from Bash
- **Reviewer(s)**: dyn-postplan-rc-output.txt
- **Severity**: important
- **Concern**: Python always seeds `.step2b-postplan-fallback-used` before checking `.pause-requested`; Bash `exec`s pause-save before fallback seeding or the timing mark. On a pause-before-launch path, Python can leave `false` or `true` in that sentinel when Bash would not have written it yet. Not parity with the Bash contract and can interact with the rc `10` inline-retry gate (`fallback_used != "true"`) on resume/re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postplan-rc-output.txt: Move the `.pause-requested` short-circuit (with `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save`) to immediately after `design_require_plugin_root`, before fallback-used seeding and before `_maybe_timing_mark`, matching Bash order.


### FINDING_14: checks.py test-check-plan-size still maps to retired Bash
- **Reviewer(s)**: dyn-launcher-docs-output.txt
- **Severity**: important
- **Concern**: `test-check-plan-size` still maps to retired `skills/design/scripts/design-step2b5.sh` and its `.md` sibling, but `design step2b5` now lives in `python/design_lifecycle.py`. Relevant-check routing points operators and CI at stale Bash authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-docs-output.txt: Retarget the mapping to `python/design_lifecycle.py` and `python/test_design_lifecycle.py` (and drop the retired `design-step2b5.sh` paths), matching the plan's checks retarget recipe.


### FINDING_15: design-step35-settle drops PUBLIC_ARGV_WORDS tail
- **Reviewer(s)**: dyn-launcher-docs-output.txt
- **Severity**: important
- **Concern**: The settle wrapper parses `PUBLIC_ARGV_WORDS` after `--` but never forwards them into `POSTPLAN_CMD`. The plan's settle argv-array contract said to preserve caller tails (`"$@"` as needed). Any future or test-seam flags passed after `--` are dropped before `python/cli.py design step2b-postplan`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-docs-output.txt: Append `"${PUBLIC_ARGV_WORDS[@]}"` to the `POSTPLAN_CMD` invocation (after the fixed transport/site flags), and add a structure or settle harness pin that proves tail forwarding.


### FINDING_16: Orphan design-step2b-prelude.sh remains on disk
- **Reviewer(s)**: dyn-launcher-docs-output.txt
- **Severity**: important
- **Concern**: Prelude logic was folded into `python/cli.py design step2b-drafter`, the launcher has no mapping for `design-step2b-prelude.sh`, and the plan marked the prelude for deletion. The file remains as a second, unrouted authority and is still mentioned in `skills/design/SKILL.md` as retained inventory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-docs-output.txt: Delete `design-step2b-prelude.sh` / `.md` with the rest of the G5 retirement batch, or if kept temporarily, document it explicitly as non-runtime legacy and exclude it from agent-lint reachability inventory.


### FINDING_3: Insufficient pytest coverage for Step 2 drafter/postplan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/test_design_lifecycle.py` has far less Step 2 drafter/postplan coverage than the plan requires (only a handful of tests vs dozens of contract scenarios). Regressions in fallback-used seeding, dirty-tree handling, wrapper-row ordering, fatal postplan mapping, pause `sys.exit`, or rc `11`/`12`/`13` behavior could merge without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add planned drafter tests before deleting Bash harnesses.
  - From cursor-specialist-edge-cases-output.txt: Add plan-listed pytest cases for drafter success/fatal/pause/dirty-tree, postplan rc 11/12/13/fatal, and codex token sidecar behavior.


### FINDING_4: Step 2 Bash wrappers not retired per plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-launcher-docs-output.txt
- **Severity**: important
- **Concern**: Retired Bash wrappers (`design-step2a.sh`, `design-step2b-drafter.sh`, `design-step2b-postplan.sh`, `design-step2b5.sh`, `design-step-validator-autofix.sh`) and `python/migrated-scripts.tsv` entries were not removed per plan acceptance. The launcher routes to Python, but on-disk `.sh` files still contain full legacy Bash bodies. Direct `.sh` execution or stale harness references diverge from Python launcher authority and invite silent drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete manifest retirement after harness green or hard-fail direct wrapper execution.
  - From dyn-launcher-docs-output.txt: After restoring G5 structure coverage and confirming pytest green, append the retired paths to `migrated-scripts.tsv` and delete the Step 2 wrapper bodies, harness shells, and prelude per the plan's `REWRITTEN:` list.


### FINDING_5: WrapperArgs class shadowing breaks Step 2 launcher calls
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: A later `WrapperArgs` class (`argparse.Namespace` subclass at ~line 806) overwrites the `@dataclass` `WrapperArgs` used by `_parse_common_wrapper_args` for Step 2. Normal launcher calls with only `--session-env-path` and `--claude-pid` create a `Namespace` missing `plugin_root`/`site` defaults, then `_rehydrate_wrapper_env` raises `AttributeError` before Step 2 runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Rename one class or use a distinct initialized dataclass for `_parse_common_wrapper_args`.
  - From codex-specialist-edge-cases-output.txt: Rename one class or otherwise ensure `_parse_common_wrapper_args` constructs an object with all Step 2 defaults.
  - From codex-specialist-testing-output.txt: Rename one class and add a minimal launcher-argv regression test.


### FINDING_6: Session-env loaders reject launcher symlink path
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-env-rehydrate-output.txt
- **Severity**: blocking
- **Concern**: `_load_session_env` in `design_lifecycle.py` returns `{}` when `session-env-path` is a symlink. `_rehydrate_validator_env` in `plan_quality.py` only reads the file when `source.is_file() and not source.is_symlink()`. The design launcher always passes `~/.cache/larch/sessions/current-design-env-$PPID.sh`, which `write_design_env_main` creates as a symlink. Bash wrappers used `source "$SESSION_ENV_PATH"`, which follows symlinks. Step 0 verbs already resolve trusted symlinks via `resolve_trusted_design_session_env_source`, but Step 2 and validator paths do not. On a normal launcher-routed run, `DESIGN_TMPDIR`, `ISSUE_NUMBER`, `REPO`, and related keys are not merged/exported; pause-save, drafter/postplan, and validator autofix can run with empty or wrong context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Resolve trusted design env symlinks with `session_env.resolve_trusted_design_session_env_source` before parsing.
  - From codex-specialist-edge-cases-output.txt: Resolve trusted PID-keyed symlinks before parsing and fail closed when `DESIGN_TMPDIR` is empty or invalid.
  - From codex-specialist-testing-output.txt: Resolve trusted current-design symlinks with `claude_pid`, share the existing loader, and test generated launcher execution.
  - From dyn-env-rehydrate-output.txt: Reuse `_load_source_env(parsed.session_env_path, allow_keys=_SESSION_ENV_ALLOWLIST, claude_pid=parsed.claude_pid)` inside `_rehydrate_wrapper_env` (or teach `_load_session_env` to resolve trusted symlinks the same way), then apply argv overlays and export to `os.environ`.
  - From dyn-env-rehydrate-output.txt: Share the trusted symlink loader from `session_env.resolve_trusted_design_session_env_source` (pass `parsed["claude_pid"]`), or delegate validator rehydration to the same helper used by `_rehydrate_wrapper_env` after the design-side fix.


### FINDING_9: Step 2a sentinel newline handling lacks Bash parity
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2 sentinel checks require a trailing newline and legacy checks do not strip trailing newlines. One-line `NO_SKETCHES` without a final newline, or `NO_SKETCHES_CLASSIFIED_SIMPLE` with a newline, is rejected as conflicting content though Bash accepted it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Accept exactly one line with or without final newline, and strip trailing newlines for legacy sentinel comparison.
  - From codex-specialist-edge-cases-output.txt: Normalize one-line legacy sentinel content before comparison.


