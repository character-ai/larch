### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:553 and python/design_summary.py:89-122
- **Concern**: Plan extends `_FLAG_NAMES` with per-model `claude_sub` families but omits the Codex mini tri-surface updates in `pr_body._TOKEN_COST_ARGS` and `design_summary._build_cost_args`. Scenario: Codex mini already requires all three: `report_tokens_cost._FLAG_NAMES`, `pr_body._TOKEN_COST_ARGS` (includes `--codex-mini-*`), and `design_summary` bucket routing. After `BUCKETS_claude_sub_by_model` lands, `token_cost_argv` / `progress_report` / `final_report` can emit Sonnet/Haiku/Fable subprocess flags, but `/design` still forwards only aggregate `CS_*` flags through `invoke_render` → `render_run_summary_main`, and argparse drops any new flags not listed in `_TOKEN_COST_ARGS`
- **Proposed resolution**: Add `### UPDATED: python/design_summary.py` mirroring the Codex block in `_read_token_report` / `_build_cost_args`; extend `pr_body._TOKEN_COST_ARGS` with the new per-model `claude_sub` flag families; pin the exact flag strings in the plan (same step as `_FLAG_NAMES`)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/report_tokens_cost.py:297-321
- **Concern**: Plan never pins the exact per-model `claude_sub` CLI flag token strings. Scenario: Implementers must invent names for Sonnet/Haiku/Fable families. `token_cost_argv`, `_claude_sub_argv`, `progress_report`, `design_summary`, and `pr_body` can diverge from `_FLAG_NAMES`, silently omitting buckets (plan failure mode #3)
- **Proposed resolution**: Name the flags explicitly in the plan, following the Codex precedent (`--codex-mini-input-tokens`, etc.), e.g. `--claude-sub-sonnet-input-tokens` / `--claude-sub-haiku-*` / `--claude-sub-fable-*` (or document the chosen slug rule once) and require the same strings in `_FLAG_NAMES`, tests, and every argv emitter

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:471-483
- **Concern**: `render_cost_line_from_args()` still feeds argv directly to `_parse_count_args()`; plan only adds `_parse_pricing_argv()` to `token_cost_from_args()`. Scenario: Any caller of `python/cli.py token render-cost-line` that forwards `--claude-model` (or new per-model `claude_sub` flags) will hit `ValueError: unknown or incomplete flag` and return cost N/A, the same failure mode accepted for FINDING_7 on the `token cost` path
- **Proposed resolution**: Route `render_cost_line_from_args()` through the same `_parse_pricing_argv()` strip/return contract before `_parse_count_args()`, or delegate to `token_cost_from_args()` and format its KV output

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_summary.py:46-122
- **Concern**: /design final-summary cost assembly omits claude_sub by-model split and is absent from the plan. Scenario: `design_summary._read_token_report` mirrors `BUCKETS_codex_by_model` into `D_MINI_*` buckets but only reads aggregate `BUCKETS_claude_sub`; `_build_cost_args` emits flat `--claude-sub-*` only. Plan adds `BUCKETS_claude_sub_by_model` in `tokens.py` and mirrors pricing in `final_report.py` and `progress_report.py` but lists no `design_summary.py` or `test_design_summary.py` work. `/design` final summaries keep subprocess Claude on one Opus rate row after ledger MODEL= recording lands.
- **Proposed resolution**: Add `### UPDATED: python/design_summary.py` (and tests): read/enrich `BUCKETS_claude_sub_by_model`, route buckets through the same rules as `_claude_sub_argv()` (or a shared helper), and extend `_build_cost_args` with the new per-model flag families. Main-lane `--claude-model` from `pr_body` manifest resolution does not replace this subprocess split.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:553-577
- **Concern**: `render_run_summary_main` `_TOKEN_COST_ARGS` whitelist not in plan. Scenario: Plan adds model-specific `claude_sub` count flags in `report_tokens_cost._FLAG_NAMES` but does not extend `pr_body._TOKEN_COST_ARGS` or the argparse loop. `design_summary.invoke_render` splats `*cost_args` into `render run-summary`; unknown flags make argparse fail and the cost line becomes N/A, or new buckets never reach `token_cost_from_args`.
- **Proposed resolution**: Extend `_TOKEN_COST_ARGS` (and any parallel allowlist) with every new `claude_sub` per-model flag plus optional `--claude-model` passthrough; add `test_pr_body.py` coverage that `render_run_summary_main` accepts the new argv and prices subprocess buckets.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:297-321
- **Concern**: Plan still does not pin exact per-model `claude_sub` CLI flag names. Scenario: Codex uses concrete tokens like `--codex-mini-input-tokens` in `_FLAG_NAMES` and `_codex_argv`. Plan says add Sonnet/Haiku/Fable families but never names the argv strings. Implementers can emit flags from `_claude_sub_argv()` that `_FLAG_NAMES` or `pr_body` omit, silently dropping a subprocess bucket from `_pricing_from_counts`.
- **Proposed resolution**: Pin the full flag set in the plan (mirror codex-mini naming, e.g. `--claude-sub-sonnet-input-tokens` through `--claude-sub-sonnet-output-tokens`, plus haiku/fable/opus-aggregate families), one `_FLAG_NAMES` entry per flag, and a test asserting `token_cost_argv` output round-trips through `_parse_pricing_argv` + `_parse_count_args`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_summary.py:46-122
- **Concern**: Plan omits design_summary claude_sub by-model argv mirroring that already exists for Codex. Scenario: /design calls render run-summary with cost_args from _read_token_report/_build_cost_args; Codex splits BUCKETS_codex_by_model into --codex-mini-* flags but claude_sub still emits flat --claude-sub-* from BUCKETS_claude_sub only, so subprocess tokens misprice once BUCKETS_claude_sub_by_model lands
- **Proposed resolution**: Add ### UPDATED: python/design_summary.py: split BUCKETS_claude_sub_by_model like Codex, route Sonnet/Haiku/Opus buckets to the same flag families as _claude_sub_argv(), and add python/test_design_summary.py coverage

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:553-576
- **Concern**: pr_body _TOKEN_COST_ARGS allowlist not extended for new claude_sub model families. Scenario: render_run_summary_main only accepts token flags in _TOKEN_COST_ARGS; new model-specific --claude-sub-* families forwarded via cost_args (from design_summary or tests) are dropped by argparse or never reach token_cost_from_args, silently omitting subprocess buckets
- **Proposed resolution**: Extend _TOKEN_COST_ARGS with every new model-specific claude_sub flag plus tests in test_pr_body.py mirroring codex-mini parser coverage

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:296-321
- **Concern**: Plan does not pin exact claude_sub per-model CLI flag names. Scenario: Codex uses --codex-mini-* slugs in _FLAG_NAMES; unpinned Sonnet/Haiku/Fable families can drift between _claude_sub_argv, _parse_pricing_argv, progress_report, and final_report, silently dropping buckets from pricing
- **Proposed resolution**: Document exact flag tokens in the plan (e.g. --claude-sub-sonnet-input-tokens mirroring --codex-mini-input-tokens) and require _FLAG_NAMES/_parse_pricing_argv/_TOKEN_COST_ARGS to list the same set

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:471-483
- **Concern**: render_cost_line_from_args still calls _parse_count_args without _parse_pricing_argv. Scenario: Only token_cost_from_args is slated for --claude-model stripping; render-cost-line CLI or callers passing --claude-model hit unknown or incomplete flag and return N/A costs
- **Proposed resolution**: Apply the same _parse_pricing_argv pre-pass in render_cost_line_from_args (and add a regression test)

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_summary.py:46-122
- **Concern**: Plan mirrors Codex per-model cost argv in final_report.py and progress_report.py but omits design_summary.py, which already splits BUCKETS_codex_by_model in _read_token_report and _build_cost_args.. Scenario: After tokens.py writes BUCKETS_claude_sub_by_model, /design final-summary still forwards only aggregate --claude-sub-* flags from BUCKETS_claude_sub, so mixed Sonnet/Opus subprocess usage on design runs stays mispriced despite the new buckets.
- **Proposed resolution**: Add ### UPDATED: python/design_summary.py (and test_design_summary.py): read/enrich BUCKETS_claude_sub_by_model like Codex, emit model-specific claude_sub flag families in _build_cost_args, and keep manifest-path + pr_body --claude-model prepend for main-lane pricing.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:553-576
- **Concern**: pr_body._TOKEN_COST_ARGS still lists only aggregate claude-sub flags; the plan adds Sonnet/Haiku/Fable subprocess families in report_tokens_cost.py but does not extend the render run-summary argparse allowlist (Codex mini flags are already listed).. Scenario: design_summary passes cost_args through invoke_render; any model-specific --claude-sub-* argv is dropped by argparse before token_argv is built, so subprocess buckets are silently omitted from /design cost lines even after _claude_sub_argv exists.
- **Proposed resolution**: Extend _TOKEN_COST_ARGS with every new model-specific claude_sub flag family (mirror --codex-mini-* coverage) and add test_pr_body coverage that render_run_summary_main accepts and prices them.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:297-321
- **Concern**: Plan warns about _FLAG_NAMES drift but never pins the exact new claude_sub per-model CLI tokens (Codex precedent: --codex-mini-input-tokens, etc.).. Scenario: Implementers can emit argv flags from _claude_sub_argv that _parse_count_args / _FLAG_NAMES omit, silently dropping a model bucket from CLAUDE_SUB_COST with no test failure unless every family is guessed correctly.
- **Proposed resolution**: Specify the full flag-name matrix in the plan (e.g. --claude-sub-sonnet-input-tokens and parallel cache/output/5m/1h names for Sonnet, Haiku, Fable) and require tests that assert token_cost_argv and _FLAG_NAMES stay in lockstep.
