### [Plan Review] FINDING_1

### FINDING_1: Plan omits `design_summary.py` claude_sub per-model cost argv mirroring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan adds `BUCKETS_claude_sub_by_model` and mirrors Codex per-model argv in `final_report.py` and `progress_report.py`, but does not update `design_summary.py`. Today `_read_token_report` splits `BUCKETS_codex_by_model` into `D_MINI_*` buckets and `_build_cost_args` emits `--codex-mini-*` flags, while claude_sub still reads only aggregate `BUCKETS_claude_sub` and emits flat `--claude-sub-*`. After by-model buckets land, `/design` final-summary cost assembly (`invoke_render` → `render run-summary`) will still forward aggregate subprocess flags, mispricing mixed Sonnet/Haiku/Fable subprocess usage even when ledger MODEL= recording exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/design_summary.py` mirroring the Codex block in `_read_token_report` / `_build_cost_args`; extend `pr_body._TOKEN_COST_ARGS` with the new per-model `claude_sub` flag families; pin the exact flag strings in the plan (same step as `_FLAG_NAMES`)
  - From Cursor-Innovation: Add `### UPDATED: python/design_summary.py` (and tests): read/enrich `BUCKETS_claude_sub_by_model`, route buckets through the same rules as `_claude_sub_argv()` (or a shared helper), and extend `_build_cost_args` with the new per-model flag families. Main-lane `--claude-model` from `pr_body` manifest resolution does not replace this subprocess split.
  - From Cursor-Pragmatic: Add ### UPDATED: python/design_summary.py: split BUCKETS_claude_sub_by_model like Codex, route Sonnet/Haiku/Opus buckets to the same flag families as _claude_sub_argv(), and add python/test_design_summary.py coverage
  - From Cursor-Requirements: Add ### UPDATED: python/design_summary.py (and test_design_summary.py): read/enrich BUCKETS_claude_sub_by_model like Codex, emit model-specific claude_sub flag families in _build_cost_args, and keep manifest-path + pr_body --claude-model prepend for main-lane pricing.


### [Plan Review] FINDING_2

### FINDING_2: Plan omits `pr_body._TOKEN_COST_ARGS` allowlist extension for per-model claude_sub flags
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `render_run_summary_main` only accepts token count flags listed in `_TOKEN_COST_ARGS` (Codex mini families are already whitelisted). The plan extends `report_tokens_cost._FLAG_NAMES` with per-model `claude_sub` families but does not extend `pr_body._TOKEN_COST_ARGS` or its argparse loop. When `design_summary.invoke_render` splats `*cost_args` into `render run-summary`, unknown flags are dropped by argparse or never reach `token_cost_from_args`, silently omitting subprocess buckets from `/design` cost lines (cost N/A or wrong totals).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/design_summary.py` mirroring the Codex block in `_read_token_report` / `_build_cost_args`; extend `pr_body._TOKEN_COST_ARGS` with the new per-model `claude_sub` flag families; pin the exact flag strings in the plan (same step as `_FLAG_NAMES`)
  - From Cursor-Innovation: Extend `_TOKEN_COST_ARGS` (and any parallel allowlist) with every new `claude_sub` per-model flag plus optional `--claude-model` passthrough; add `test_pr_body.py` coverage that `render_run_summary_main` accepts the new argv and prices subprocess buckets.
  - From Cursor-Pragmatic: Extend _TOKEN_COST_ARGS with every new model-specific claude_sub flag plus tests in test_pr_body.py mirroring codex-mini parser coverage
  - From Cursor-Requirements: Extend _TOKEN_COST_ARGS with every new model-specific claude_sub flag family (mirror --codex-mini-* coverage) and add test_pr_body coverage that render_run_summary_main accepts and prices them.


### [Plan Review] FINDING_3

### FINDING_3: Plan does not pin exact per-model claude_sub CLI flag token strings
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan says to add Sonnet/Haiku/Fable `claude_sub` flag families but never names the exact argv strings (Codex precedent: `--codex-mini-input-tokens`, etc.). Implementers must invent slugs; `token_cost_argv`, `_claude_sub_argv`, `progress_report`, `final_report`, `design_summary`, `pr_body`, and `_FLAG_NAMES` can diverge, silently dropping buckets from `_pricing_from_counts` with no test failure unless every surface guesses the same names (plan failure mode #3).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name the flags explicitly in the plan, following the Codex precedent (`--codex-mini-input-tokens`, etc.), e.g. `--claude-sub-sonnet-input-tokens` / `--claude-sub-haiku-*` / `--claude-sub-fable-*` (or document the chosen slug rule once) and require the same strings in `_FLAG_NAMES`, tests, and every argv emitter
  - From Cursor-Innovation: Pin the full flag set in the plan (mirror codex-mini naming, e.g. `--claude-sub-sonnet-input-tokens` through `--claude-sub-sonnet-output-tokens`, plus haiku/fable/opus-aggregate families), one `_FLAG_NAMES` entry per flag, and a test asserting `token_cost_argv` output round-trips through `_parse_pricing_argv` + `_parse_count_args`.
  - From Cursor-Pragmatic: Document exact flag tokens in the plan (e.g. --claude-sub-sonnet-input-tokens mirroring --codex-mini-input-tokens) and require _FLAG_NAMES/_parse_pricing_argv/_TOKEN_COST_ARGS to list the same set
  - From Cursor-Requirements: Specify the full flag-name matrix in the plan (e.g. --claude-sub-sonnet-input-tokens and parallel cache/output/5m/1h names for Sonnet, Haiku, Fable) and require tests that assert token_cost_argv and _FLAG_NAMES stay in lockstep.


### [Plan Review] FINDING_4

### FINDING_4: `render_cost_line_from_args()` bypasses `_parse_pricing_argv()` for `--claude-model` and new per-model flags
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `render_cost_line_from_args()` still feeds argv directly to `_parse_count_args()`; the plan only adds `_parse_pricing_argv()` stripping to `token_cost_from_args()`. Any caller of `python/cli.py token render-cost-line` (or other path through `render_cost_line_from_args`) that forwards `--claude-model` or new per-model `claude_sub` flags will hit `ValueError: unknown or incomplete flag` and return cost N/A, the same class of failure accepted for the `token cost` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Route `render_cost_line_from_args()` through the same `_parse_pricing_argv()` strip/return contract before `_parse_count_args()`, or delegate to `token_cost_from_args()` and format its KV output
  - From Cursor-Pragmatic: Apply the same _parse_pricing_argv pre-pass in render_cost_line_from_args (and add a regression test)


