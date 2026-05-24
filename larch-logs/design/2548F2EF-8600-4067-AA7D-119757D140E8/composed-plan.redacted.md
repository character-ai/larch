## Plan

### Approach

Introduce a two-helper validator pipeline driven through `design-driver.sh` as a new `ACTION=VALIDATE_PLAN_COMMANDS` with an explicit `--plan-file` CLI:

1. **`skills/design/scripts/parse-plan-commands.sh`** — deterministic, side-effect-free markdown parser. Walks the input file's fenced ` ```bash ` and ` ```sh ` blocks, joins backslash continuations, suppresses heredoc bodies (`<<EOF…EOF` and `<<'EOF'…EOF`), splits each command line on `|`, `&&`, `||`, `;`. **Token normalization**: before filtering, strip outer single/double quotes; peel interpreter prefixes (`bash`, `sh`, `dash`, `env`, each with optional `-c` and optional `--`); map `${CLAUDE_PLUGIN_ROOT}/`, `$CLAUDE_PLUGIN_ROOT/`, and absolute checkout-root prefixes (e.g., `<OPERATOR_REPO_PATH>/`) to repo-relative paths. The first non-flag token AFTER normalization is the script path. **Allow-list inputs**: parser reads BOTH `### NEW: <path>` / `### UPDATED: <path>` headings AND the bullet form used by current /design plans — `- **NEW**: <path>` / `- **UPDATED**: <path>` inside `### Files to create` / `### Files to update` sections, including indented `- Adds flag: <flag>` sub-bullets under UPDATED entries. PARSE_NOTE rows for subshells `$(...)` and process substitution `<(...)`.

2. **`skills/design/scripts/validate-plan-commands.sh`** — consumes the parser's TSV plus the merged allow-list. Filters rows to repo scripts (paths matching `scripts/`, `skills/*/scripts/`, `.claude/skills/*/scripts/` after normalization); drops system commands silently. **NEW-script handling**: rows whose `script_path` matches a `row_type=new_script` allow-list entry are skipped from BOTH Tier 2 and Tier 3; emit `SKIPPED script=<path> reason=new-script` log line per skipped row. For each remaining repo-script row:
   - **Tier 2 (existence + flag check) — deterministic rule**:
     - **Existence**: confirm the script exists on disk; if not, `DEFECT script=<path> kind=missing-script`.
     - **Help probe**: run `<script> --help` with a 10s timeout, capturing stdout+stderr.
     - **Help unavailable** → `SKIPPED_FLAG_CHECK script=<path> reason=no-help` log line. "No-help" means exactly one of: non-zero exit, empty stdout (after trimming), or timeout.
     - **Help available (non-zero stdout, exit 0 or recognized usage exit)**: for each flag named in the plan command, grep the captured help text for `--<flag-name>`. **Flag absent from non-empty help → `DEFECT script=<path> kind=unknown-flag flag=<flag>`**, UNLESS the flag is allow-listed via a `row_type=updated_flag script_path=<path> flag=<flag>` allow-list entry — in which case it's silently allowed.
     - There is no `SKIPPED_FLAG_CHECK reason=flag-not-in-help` rule. Terse `--help` output that omits a real flag is handled exclusively via UPDATED allow-listing in the plan body, NOT by silent runtime tolerance.
   - **Tier 3 (opt-in dry-run) — argv-array, no eval**: when (a) the script is listed in `scripts/dry-runnable-scripts.tsv`, (b) Tier 2 produced no `DEFECT` for that row, AND (c) the source file is `plan.txt` (Tier 3 is **disabled on pre-redaction `composed-plan.md`** to avoid secret leakage via subprocess env or log capture):
     - Reject rows whose tokens contain shell metacharacters outside allow-listed flag values: `$`, backtick, `;`, `|`, `&`, `>`, `<`, `(`, `)`, glob `*` / `?` / `[`. Reject any token containing `..`. Defect emitted as `DEFECT script=<path> kind=unsafe-token token=<redacted>`.
     - Construct argv as a token array from the TSV row (no string concatenation; no `bash -c`; no `eval`). Prepend `LARCH_DRY_RUN=1` via `env` (or apply the registry's `hook=--validate-only` convention).
     - Execute with `cwd` pinned to the repo root (`CLAUDE_PROJECT_DIR` or `git rev-parse --show-toplevel`), 10s timeout, inherited PATH but no inherited custom env beyond `LARCH_DRY_RUN`.
     - Non-zero exit → `DEFECT script=<path> kind=dry-run-failed exit=<N>` with captured stdout/stderr appended to the log.

3. **`skills/design/scripts/validate-plan.sh`** — driver-action wrapper. Accepts a **required `--plan-file FILE`** flag; runs parser → validator; copies the log to `$DESIGN_TMPDIR/validate-plan-commands.log`. **Exit-code contract**: exits **0** whenever the validator infrastructure ran successfully, regardless of defect count. The KV summary distinguishes outcomes: `VALIDATE_STATUS=ok` (zero defects) or `VALIDATE_STATUS=defects-found` (≥1 defect). Driver `STEP_FAILED=VALIDATE_PLAN_COMMANDS` only fires on infrastructure failure — never on defects-found. SKILL.md's failure flow keys solely off `VALIDATE_STATUS=defects-found`. Always re-runnable (`no_sentinel=true`).

4. **`design-driver.sh`** — extend the action whitelist (`EMIT_PLAN|TALLY|FINALIZE|VALIDATE_PLAN_COMMANDS`), add the `run_action()` arm dispatching to `validate-plan.sh "$@"` (preserves `--plan-file` arg pass-through), and mark `VALIDATE_PLAN_COMMANDS` as `no_sentinel=true`.

5. **`skills/design/SKILL.md`** — invoke `ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file …` at THREE points, all gated by `review_budget != quick` (skips on `--trivial`):
   - **Step 2b**: immediately AFTER the existing `ACTION=EMIT_PLAN` block, against `$DESIGN_TMPDIR/plan.txt`.
   - **Step 3.5 / Gate B applied-set EMIT_PLAN re-runs**: after every Gate B Apply (all or per-finding) that revises `plan.txt`, the existing post-revision `ACTION=EMIT_PLAN` call is immediately followed by `ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file "$DESIGN_TMPDIR/plan.txt"`. Same applies to Gate A discussion-mode re-entry plan revisions (`discussion-rounds.md:121`).
   - **Step 5c**: AFTER composing `$DESIGN_TMPDIR/composed-plan.md` and BEFORE `redact-secrets.sh` runs, with `ARGS=--plan-file "$DESIGN_TMPDIR/composed-plan.md"`. Tier 3 is disabled here.

   Insert the AskUserQuestion failure body (Fix-and-retry / Override / Cancel) once and reference it from all sites. **Fix-and-retry semantics**: when the operator edits `plan.txt` (or `composed-plan.md`) to address defects, the SKILL re-runs `ACTION=EMIT_PLAN` first (refreshes `diff_lines.txt`) THEN `ACTION=VALIDATE_PLAN_COMMANDS`. **Override** logs to `$DESIGN_TMPDIR/execution-issues.md` under `Warnings` via `append-tool-failure.sh --site "design Step <N>" --category Warnings`. **Cancel** in Step 2b returns to Gate A; in Step 5c it preserves `$DESIGN_TMPDIR` and skips Step 6 cleanup.

### TSV schema (normative)

`parse-plan-commands.sh` emits a single TSV file. Single header row, then mixed rows:

```
row_type	source_line	script_path	flag	flag_value	note
```

- **`row_type=invocation`** — one row per (command × flag) pair. `source_line` = 1-based line number in the plan where the fenced block opens. `script_path` = normalized repo-relative path. `flag` = long flag name without leading `--`. `flag_value` = value if `--foo=bar` or `--foo bar`, else empty. `note` = empty.
- **`row_type=invocation_no_flags`** — one row per command that has no flags. `flag` and `flag_value` are empty.
- **`row_type=parse_note`** — emitted instead of an invocation row when a construct is skipped (`subshell`, `process_substitution`, `eval`, etc.). `script_path` and `flag` empty; `note=<reason>`.
- **`row_type=new_script`** — allow-list entry from a `### NEW: <path>` heading OR a `- **NEW**: <path>` bullet. `script_path` = the declared new path. `flag` empty.
- **`row_type=updated_flag`** — allow-list entry from `### UPDATED: <path>` + `- Adds flag: <flag>` OR `- **UPDATED**: <path>` + indented `- Adds flag: <flag>` sub-bullet. `script_path` = the updated path; `flag` = flag name without `--`.

**Field constraints**: paths and flags MUST NOT contain literal tab, newline, or carriage return. Parser rejects rows that would violate this with `PARSE_NOTE` and a stderr warning. **Single allow-list file**: parser emits one TSV (no plural sidecars); the validator consumes a single `--tsv-file` argument and segments by `row_type`.

**Validator stdout summary** (last line):

```
VALIDATE_STATUS=ok|defects-found	DEFECT_COUNT=<N>	SKIPPED_COUNT=<N>	UNSAFE_TOKEN_COUNT=<N>
```

Wrapper `validate-plan.sh` parses that final KV line and forwards as `VALIDATE_STATUS=…`, `VALIDATE_DEFECT_COUNT=…`, `VALIDATE_SKIPPED_COUNT=…`, `VALIDATE_LOG_FILE=…`. Harness fixtures pin byte-exact TSV outputs and KV line shape.

### Files to create

- **NEW**: `skills/design/scripts/parse-plan-commands.sh` — markdown-state-aware fenced-block extractor; normalizes tokens (interpreter prefixes, plugin-root prefixes, quotes); emits the single TSV schema above; Bash 3.2-portable; `set -euo pipefail`; sources `scripts/lib-quiet.sh` via `source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"`.
- **NEW**: `skills/design/scripts/parse-plan-commands.md` — sibling contract documenting CLI (`--plan-file FILE --output FILE`), the TSV schema verbatim, allow-list bullet AND heading grammars, token-normalization rules, charset constraints, exit codes, and primary callers.
- **NEW**: `skills/design/scripts/validate-plan-commands.sh` — TSV consumer; Tier 2 (existence + `--help` flag-check with the deterministic rule) followed by Tier 3 (argv-array dry-run with metacharacter rejection, disabled when `--source=composed-plan`); emits `DEFECT`/`SKIPPED`/`SKIPPED_FLAG_CHECK` log rows + the single KV summary line.
- **NEW**: `skills/design/scripts/validate-plan-commands.md` — sibling contract documenting CLI (`--tsv-file FILE --log-file FILE [--dry-runnable-registry FILE] [--source-kind plan|composed] [--help-timeout SEC] [--dry-run-timeout SEC]`), defect-row schema, the Tier 2 deterministic rule, the Tier 3 argv invariant, the metacharacter denylist, the composed-plan exclusion, the registry format, and the Tier 2 → Tier 3 ordering rule.
- **NEW**: `skills/design/scripts/validate-plan.sh` — driver wrapper. Required `--plan-file FILE` flag; infers `source-kind` from the basename (`plan.txt` → `plan`; `composed-plan.md` → `composed`); calls parser → validator; copies log to `$DESIGN_TMPDIR/validate-plan-commands.log`; emits `VALIDATE_STATUS=…`, `VALIDATE_DEFECT_COUNT=…`, `VALIDATE_SKIPPED_COUNT=…`, `VALIDATE_UNSAFE_TOKEN_COUNT=…`, `VALIDATE_LOG_FILE=…`. Exit-code contract per #2674.
- **NEW**: `skills/design/scripts/validate-plan.md` — sibling contract documenting the wrapper CLI, the exit-code contract, the source-kind inference, the Fix-and-retry re-EMIT_PLAN protocol, the no-new-Family-B-denylist rationale, and the re-runnable invariant.
- **NEW**: `scripts/dry-runnable-scripts.tsv` — opt-in registry. Header: `script_path<TAB>hook<TAB>doc_anchor`. Initially empty (no rows). Sibling `.md` documents schema and the opt-in workflow.
- **NEW**: `scripts/dry-runnable-scripts.md` — sibling contract: schema, two supported hook conventions (`LARCH_DRY_RUN=1` env var, `--validate-only` flag), per-row `doc_anchor`, and the rule that adding a row requires the script's `.md` sibling to declare the dry-run convention.
- **NEW**: `skills/design/scripts/test-parse-plan-commands.sh` — offline harness with golden fixtures covering all grammars, prefixes, NEW/UPDATED forms, subshell PARSE_NOTE, byte-exact TSV assertions.
- **NEW**: `skills/design/scripts/test-parse-plan-commands.md` — harness contract.
- **NEW**: `skills/design/scripts/test-validate-plan-commands.sh` — offline harness covering all Tier 2 paths, Tier 3 argv hardening, demonstration assertion (`scripts/launch-claude-review.sh --context-files` → `DEFECT kind=unknown-flag`), injection probes, cwd-pin probe, `--source-kind composed` Tier-3-disable.
- **NEW**: `skills/design/scripts/test-validate-plan-commands.md` — harness contract.

### Files to update

- **UPDATED**: `skills/design/scripts/design-driver.sh` — extend the action whitelist + dispatcher arm; mark `VALIDATE_PLAN_COMMANDS` re-runnable.
  - Adds flag: (none — new ACTION enum value only; the wrapper accepts `--plan-file FILE` passed via ACTION ARGS)
- **UPDATED**: `skills/design/scripts/design-driver.md` — document the new ACTION, ARGS contract, re-runnable invariant, exit-code contract.
- **UPDATED**: `skills/design/SKILL.md` — insert Step 2b validator invocation block after EMIT_PLAN; insert Step 5c validator block before redact-secrets.sh; define the AskUserQuestion failure-flow body once; extend the "Plan helper contracts" footer with new helper bullets (literal paths for agent-lint reachability); update SKILL.md line 287 narrative.
- **UPDATED**: `skills/design/references/flags.md` — document the tier rule (`--trivial` skips; `--simple`/`--hard` run) and the AskUserQuestion options.
- **UPDATED**: `skills/design/references/approval-gates.md` — add the post-Apply EMIT_PLAN+VALIDATE pairing to Gate B procedures.
- **UPDATED**: `skills/design/references/discussion-rounds.md` — add the post-revision EMIT_PLAN+VALIDATE pairing to the Round 2 plan-revision authority block.
- **UPDATED**: `Makefile` — add `test-parse-plan-commands` and `test-validate-plan-commands` targets wrapped via `scripts/harness-timer.sh`; append both to a `test-harnesses-N:` shard line (operator picks the lightest shard); append to the root `.PHONY` manifest line.
- **UPDATED**: `agent-lint.toml` — add the two new test harness `.sh` paths AND their `.md` siblings to the `exclude` list, mirroring existing `skills/design/scripts/test-*.sh` entries.
- **UPDATED**: `scripts/test-design-structure.sh` — extend Check 14b's grep assertions for `ACTION=VALIDATE_PLAN_COMMANDS` in SKILL.md AND for the action-whitelist arm in design-driver.sh. Add structural assertions: (a) VALIDATE_PLAN_COMMANDS appears AFTER EMIT_PLAN in Step 2b; (b) AskUserQuestion failure block exists with three labels Fix-and-retry / Override / Cancel; (c) Step 5c invocation appears before redact-secrets.sh; (d) Cancel path in Step 5c preserves `$DESIGN_TMPDIR`.
- **UPDATED**: `skills/shared/topology.tsv` — add a row documenting the new `/design` validator phase. Regenerates `docs/topology.md` via `bash scripts/generate-topology-docs.sh` in the same change set.
- **UPDATED**: `docs/topology.md` — regenerated from `topology.tsv`.
- **UPDATED**: `SECURITY.md` — add a "Tier 3 plan-command dry-run trust model" section describing: registry opt-in + sibling-doc declaration; argv-array execution invariant; cwd pinning; metacharacter rejection; 10s timeout; `LARCH_DRY_RUN=1` env model; Override forensics; Tier 3 disabled on pre-redaction composed-plan.md.

### Edge cases

- **No fenced blocks**: empty TSV (header only); `VALIDATE_STATUS=ok DEFECT_COUNT=0`.
- **`### NEW:` heading with a typo**: path enters allow-list verbatim; different typo elsewhere → `DEFECT kind=missing-script`.
- **`### UPDATED:` without `- Adds flag:` bullet**: no allow-list row; existing flags still validate; missing-help flag → `DEFECT kind=unknown-flag`.
- **Script with `--help` arm but terse usage omits a real flag**: `DEFECT kind=unknown-flag`. Resolution: add `- Adds flag:` bullet or fix the script's help text (overhaul tracked in #2679).
- **Pipe with system-command components** (`script.sh --flag | jq '.foo'`): repo script validated; system command silently dropped.
- **Heredoc body containing what looks like a command**: suppressed.
- **Multiple invocations in one run** (Step 2b + Gate B Apply + Step 5c + Fix-and-retry): `no_sentinel=true` re-runs each time.
- **`${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh --flag`**: normalized to `scripts/foo.sh`; standard Tier 2 path.
- **`bash scripts/foo.sh --flag`**: interpreter peeled; `scripts/foo.sh` is the target.
- **NEW row's script invoked elsewhere in plan**: Tier 2 + Tier 3 both skip; emit `SKIPPED reason=new-script` log.
- **Tier 3 invocation token contains `;` / `|` / `$(` / backtick**: rejected pre-execution as `DEFECT kind=unsafe-token`. No subprocess fires.
- **Tier 3 on Step 5c `composed-plan.md`**: skipped entirely; only Tier 2 runs.
- **Help-text caching**: validator caches `--help` output per resolved script path per run to bound wall time.
- **Script `--help` prints empty stdout**: treated as no-help; `SKIPPED_FLAG_CHECK reason=no-help`.

### Failure modes

1. **External-tool flag drift breaks the validator's own `--help` probe** (helper renames `--help` to `-h` only). Earliest warning: harness fixture for that script emits `SKIPPED_FLAG_CHECK reason=no-help` even though the script has a help arm. Mitigation: `validate-plan-commands.md` documents `--help` as the contract; short-flag-only scripts get a graceful skip; long-term fix lives in #2679 overhaul.
2. **Operator picks Override on a real defect** breaking `/implement`. Mitigation: every Override decision logs to `$DESIGN_TMPDIR/execution-issues.md` under `Warnings` via `append-tool-failure.sh`. Design-log publish carries the forensics to GitHub via `larch-logs/design/<RUN_ID>/`. The `larch:plan` block does NOT carry override decisions.
3. **Tier 3 dry-run has unintended side effects**. Mitigation: registry entries require sibling `.md` to declare the dry-run convention; harness verifies no working-tree writes; metacharacter rejection; cwd pinning; 10s timeout; Tier 3 disabled on pre-redaction composed-plan.
4. **Parser drift relative to evolving /design plan format**. Mitigation: harness fixtures use byte-exact copies of real /design plan structure; both bullet AND heading grammars tested; charset-violation guard.

## Acceptance

- `skills/design/scripts/parse-plan-commands.sh` extracts a TSV of (script_path, flags) for every fenced bash block per the normative TSV schema above; skips system commands; recognizes BOTH `### NEW:` headings and `- **NEW**:` bullets (and the UPDATED equivalents with `- Adds flag:` sub-bullets); emits `PARSE_NOTE` for subshells/process-substitution; normalizes interpreter prefixes (`bash`/`sh`/`env`) and `${CLAUDE_PLUGIN_ROOT}/` paths; rejects fields containing tab/newline/CR.
- `skills/design/scripts/validate-plan-commands.sh` Tier 2 deterministic rule: existence missing → `DEFECT kind=missing-script`; help unavailable → `SKIPPED_FLAG_CHECK reason=no-help` (existence verified); flag absent from non-empty help → `DEFECT kind=unknown-flag` unless UPDATED-allow-listed.
- `validate-plan-commands.sh` Tier 3 (opt-in via `scripts/dry-runnable-scripts.tsv`): argv-array execution (no shell eval); rejects shell metacharacters with `DEFECT kind=unsafe-token`; pins cwd to repo root; 10s timeout; disabled when `--source-kind composed`.
- `skills/design/scripts/validate-plan.sh --plan-file FILE` always exits 0 on successful pipeline; KV outputs `VALIDATE_STATUS=ok|defects-found`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`.
- `design-driver.sh` action whitelist includes `VALIDATE_PLAN_COMMANDS`; dispatcher arm passes through `ARGS=--plan-file FILE` to `validate-plan.sh`; action marked `no_sentinel=true`.
- `skills/design/SKILL.md` invokes the validator at Step 2b (after `EMIT_PLAN`, against `plan.txt`), at Gate B post-Apply EMIT_PLAN re-runs (against `plan.txt`), and at Step 5c (against `composed-plan.md`, before `redact-secrets.sh`). All three gated by `review_budget != quick`.
- AskUserQuestion failure flow defined once with three options (Fix-and-retry / Override / Cancel); Fix-and-retry re-runs `EMIT_PLAN` before re-validating; Override logs to `execution-issues.md` under `Warnings`; Cancel in Step 5c preserves `$DESIGN_TMPDIR` and skips Step 6 cleanup.
- Demonstration test (`test-validate-plan-commands.sh`): a plan containing `scripts/launch-claude-review.sh --context-files <path>` produces exactly `DEFECT script=scripts/launch-claude-review.sh kind=unknown-flag flag=context-files`.
- Both new test harnesses (`test-parse-plan-commands.sh`, `test-validate-plan-commands.sh`) are wired into `make lint` via Makefile targets in a `test-harnesses-N:` shard; root `.PHONY` manifest line includes both; `test-harness-shards-coverage.sh` passes.
- `agent-lint.toml` excludes both new test harness `.sh` paths AND their `.md` siblings; new helper scripts are reachable via SKILL.md "Plan helper contracts" literal-path bullets.
- `scripts/test-design-structure.sh` Check 14b asserts `ACTION=VALIDATE_PLAN_COMMANDS` in SKILL.md and the action-whitelist arm in `design-driver.sh`; structural assertions pin Step 2b ordering, AskUserQuestion option labels, Step 5c position before `redact-secrets.sh`, and Cancel-path preservation of `$DESIGN_TMPDIR`.
- `SECURITY.md` documents the Tier 3 trust model (registry opt-in, argv-array invariant, cwd pinning, metacharacter denylist, timeout, env minimalism, override forensics, composed-plan exclusion).
- Validator does NOT run on `--trivial` tier; runs on `--simple` and `--hard`.
- `skills/shared/topology.tsv` has a row for the new validator phase; `docs/topology.md` regenerated in the same change set.

diff_lines: 1200
