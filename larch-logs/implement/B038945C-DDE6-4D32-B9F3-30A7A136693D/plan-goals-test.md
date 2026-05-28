## Goal
Implement issue #3077: [IMPLEMENTING] [BUG] /design SKILL.md ↔ shipped-script contract drift hides silent fallbacks\n\n# Summary.

## Implementation Plan
## Plan

## Approach

Three coordinated changes that resolve issue #3077's two bug clusters and add regression scaffolding to prevent recurrence. Bias is minimum-change (SIMPLE tier): no refactors beyond what each acceptance criterion requires.

1. **Section B (Option A) — extend `write-run-params.sh` + abort on contract drift.** Add 5 new flags (`--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`) to the script's argv-parse `case` block; bump `schema_version` 2→3; write 5 new corresponding JSON fields (`design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, `workflow_path`); keep existing 5 flags + 5 existing JSON fields backward-compatible. Add explicit SIMPLE/HARD tier-derived value assignments in `skills/design/SKILL.md` Step 0b **before** the canonical call so optional flags never receive empty strings on normal flows. Replace the SKILL.md Step 0b "default to HARD" recovery block with a loud abort + clear contract-drift error.

2. **Section A — audit + convert unsafe `${var//pat/$rep}` callsites.** Grep all `.sh` under `scripts/` and `skills/*/scripts/` for `${VAR//pattern/$replacement}`; convert each file-derived-replacement site to the `%%`/`##` split pattern. Add the bash 5.x `&` behavior note to `BASH_AUTHORING.md` §3.

3. **Section C — two new CI linters.** Add `lint-skill-md-flag-signature.sh` (catches Section B class) and `lint-renderer-substitution-safety.sh` (catches Section A class). Each ships sibling `.md` + offline harness. Register both in `make lint` and pre-commit. Both pre-commit hooks must be wired with `always_run: true` (mirrors `lint-readability-preamble`) so scoped `pre-commit run --files` invocations still scan the cross-repo surface.

## Files to modify/create

### UPDATED: `scripts/write-run-params.sh`

Extend the argv `case` block to accept 5 new flags. Add enum validation for the three constrained flags. Accept the two string flags as free-form. Bump `schema_version` to `3`. Extend the `jq -n` invocation with 5 new optional fields. Update usage string.

**Argv parsing — empty-string tolerant** (FINDING_4). The existing optional-flag pattern uses `${2:?--flag requires a value}`, which exits non-zero when `$2` is the empty string. For nullable optional fields (`--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`), use a Bash 3.2-safe value reader that distinguishes "missing argv" from "empty string":

```bash
# Bash 3.2-safe pattern: detect missing arg using parameter-expansion `${2-}` (unset → empty without error)
# instead of `${2:?...}` (errors on empty). Empty values are accepted and emitted as JSON null.
take_value() {
    local flag="$1"
    if [[ $# -lt 2 ]]; then
        larch_err "write-run-params.sh: $flag requires a value"
        exit 2
    fi
    printf '%s' "$2"
}

# In the case block:
        --reason)
            REASON="$(take_value --reason "${2-}")"
            shift 2
            ;;
        # ... same shape for --source, --sketch-budget, --review-budget, --workflow-path
```

Required `--classification` and `--output` keep the strict `${2:?}` form because empty values are not meaningful there.

Enum validation only when the captured value is non-empty:
```bash
if [[ -n "$SKETCH_BUDGET" ]]; then require_enum "--sketch-budget" "$SKETCH_BUDGET" 0 2 4; fi
if [[ -n "$REVIEW_BUDGET" ]]; then require_enum "--review-budget" "$REVIEW_BUDGET" quick full; fi
if [[ -n "$WORKFLOW_PATH" ]]; then require_enum "--workflow-path" "$WORKFLOW_PATH" SIMPLE HARD; fi
```

**Exact v3 JSON field names** (FINDING_7). The five new fields are pinned with their full names — do NOT shorten to `reason`/`source` or similar:
- `design_classification_reason` (string or null)
- `design_classification_source` (string or null)
- `sketch_budget` (integer 0/2/4 or null)
- `review_budget` (string "quick"/"full" or null)
- `workflow_path` (string "SIMPLE"/"HARD" or null)

Schema v3 jq:
```bash
jq -n \
    --arg classification "$CLASSIFICATION" \
    --arg reason "${REASON:-}" \
    --arg source "${SOURCE:-}" \
    --arg sketch_budget "${SKETCH_BUDGET:-}" \
    --arg review_budget "${REVIEW_BUDGET:-}" \
    --arg workflow_path "${WORKFLOW_PATH:-}" \
    --arg partition_requested "${PARTITION_REQUESTED:-false}" \
    --arg brainstorm_requested "${BRAINSTORM_REQUESTED:-false}" \
    --arg manual_gate_b "${MANUAL_GATE_B:-false}" \
    '{
      schema_version: 3,
      design_classification: $classification,
      design_classification_reason: (if $reason == "" then null else $reason end),
      design_classification_source: (if $source == "" then null else $source end),
      sketch_budget: (if $sketch_budget == "" then null else ($sketch_budget | tonumber) end),
      review_budget: (if $review_budget == "" then null else $review_budget end),
      workflow_path: (if $workflow_path == "" then null else $workflow_path end),
      partition_requested: ($partition_requested == "true"),
      brainstorm_requested: ($brainstorm_requested == "true"),
      manual_gate_b: ($manual_gate_b == "true")
    }' > "$TMP"
```

Usage string updated to list all 10 flags with `[optional]` markers on the 8 optional ones.

### UPDATED: `scripts/write-run-params.md`

Update Invariants to document schema v3 + 5 new optional flags (with enums and default-null behavior for `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`). Pin the exact v3 JSON keys: `design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, `workflow_path`. Remove the "Does not emit derived or legacy fields" line. Document the empty-string-tolerant parser behavior (`--reason ""` accepts and emits JSON null). Update Harness section to note new test coverage. Update Edit In Sync rule. Add a one-line note that readers MUST accept `schema_version >= 2` for backward compatibility (no breaking changes to v2 fields).

### UPDATED: `scripts/test-write-run-params.sh`

Additive test cases (mirror existing `--partition-requested` patterns). **All test invocations use space-separated `--flag value` form** (FINDING_6) — the writer parser does not support `--flag=value` equals form, so equals-form invocations would test unknown-flag handling instead of enum validation.

- Default `schema_version` assertion changes from `2` to `3` (one-line edit on existing case).
- Full-flag-set: invoke with all 10 flags using space-separated form (e.g., `--sketch-budget 4 --review-budget full --workflow-path HARD --reason "argv tier: --hard" --source caller-forwarded`); assert v3 JSON has all 5 new fields populated with the exact pinned field names.
- Default behavior: omit new flags; assert all 5 new JSON fields exist (use jq `has(...)`) and equal `null` (not missing, not empty string).
- Invalid `--sketch-budget 5` (space form) exits 2 with enum error message.
- Invalid `--review-budget medium` exits 2 with enum error.
- Invalid `--workflow-path MEDIUM` exits 2 with enum error.
- Empty-tolerant: `--reason ""` and `--source ""` accept empty strings; assert resulting JSON has `design_classification_reason: null` and `design_classification_source: null` (FINDING_4).
- `--reason "free form"` and `--source caller-forwarded` accept any non-empty string.
- Round-trip: jq-read each of the 5 new fields by exact name, assert it matches input value.

Existing test cases need `.schema_version == 3` updated where they assert it.

### UPDATED: `skills/design/SKILL.md`

Two coordinated edits in Step 0b sub-step 6:

**Edit 1 — explicit tier-derived value assignments before the canonical call** (FINDING_3). Before the `write-run-params.sh` invocation, ensure these in-memory mappings are bound (based on the tier resolved by the gate above):

```
- SIMPLE: `design_classification_reason="argv tier: --simple"`, `design_classification_source=caller-forwarded`, `sketch_budget=0`, `review_budget=full`, `workflow_path=SIMPLE`.
- HARD: `design_classification_reason="argv tier: --hard"`, `design_classification_source=caller-forwarded`, `sketch_budget=4`, `review_budget=full`, `workflow_path=HARD`.
```

The SIMPLE→`sketch_budget=0` mapping aligns with Step 2a's "SIMPLE branch (no sketches)" carve-out and supersedes any legacy `sketch_budget=2` documentation (FINDING_5). The HARD mapping is unchanged from current SKILL.md prose. These mappings ensure the canonical 9-flag call always receives non-empty values for the optional flags, eliminating the empty-string edge case as a normal-flow concern (the empty-string tolerance in the writer remains as defense-in-depth for callers that legitimately want JSON `null`).

**Edit 2 — replace the fallback block at line 312** (Section B abort). Old text:

```
If the helper exits non-zero, print `**⚠ 0: router — run-params write failed; defaulting to HARD sketch budget.**`, set in-memory defaults `design_classification=HARD`, `sketch_budget=4`, `review_budget=full`, `workflow_path=HARD`, and continue.
```

New text:

```
If the helper exits non-zero, treat it as **contract drift** between SKILL.md and `scripts/write-run-params.sh` (issue #3077). Print `**⚠ /design: SKILL.md ↔ write-run-params.sh contract drift detected; aborting before silent tier downgrade. Run \`bash scripts/test-write-run-params.sh\` to repro, then update either SKILL.md or the script to re-align.**` to stderr and exit 1. `$DESIGN_TMPDIR` is preserved (Step 6 cleanup is gated on `PLAN_WRITE_OK=true`, which is not set on this path).
```

The router-flag persistence merge block immediately below this paragraph is preserved unchanged because Option A makes the canonical call succeed — that block remains the recovery for partial subshell-rehydration cases.

### UPDATED: `skills/design/references/flags.md`

Update the `--simple` mapping to document `sketch_budget=0` instead of `sketch_budget=2`, consistent with SKILL.md Step 2a's SIMPLE-branch carve-out (FINDING_5). The current `flags.md` Public flags section says: `--simple` maps to `sketch_budget=2`. Change to `sketch_budget=0` and add a one-sentence note that this aligns with the SKILL.md Step 2a SIMPLE branch which writes the no-sketches sentinel. Update any cross-reference to `quick_mode=true` if still present (no behavior change — SKILL.md branches on classification, not budget).

Also add a short paragraph documenting the v3 schema additions (the 5 new optional fields) so the normative flag reference is self-consistent with the writer.

### UPDATED: `skills/design/scripts/render-plan-review-prompt.sh`

Convert the 3 remaining `${var//pat/$rep}` sites at lines 142-144 to the `%%`/`##` split pattern (consistent with the existing fix on lines 148-149 for `__READABILITY_STYLE_BLOCK__`). All three replacements (`$full_role`, `$tier_emphasis`, `$PLAN_FILE`) are either file-derived or could plausibly contain `&` if upstream content changes; converting all three eliminates future linter waiver burden.

Replace:
```bash
prompt_body="${prompt_body//__FULL_ROLE__/$full_role}"
prompt_body="${prompt_body//__TIER_EMPHASIS__/$tier_emphasis}"
prompt_body="${prompt_body//__PLAN_FILE__/$PLAN_FILE}"
```

With:
```bash
_fr_before="${prompt_body%%__FULL_ROLE__*}"; _fr_after="${prompt_body##*__FULL_ROLE__}"
prompt_body="${_fr_before}${full_role}${_fr_after}"
_te_before="${prompt_body%%__TIER_EMPHASIS__*}"; _te_after="${prompt_body##*__TIER_EMPHASIS__}"
prompt_body="${_te_before}${tier_emphasis}${_te_after}"
_pf_before="${prompt_body%%__PLAN_FILE__*}"; _pf_after="${prompt_body##*__PLAN_FILE__}"
prompt_body="${_pf_before}${PLAN_FILE}${_pf_after}"
```

If audit-grep (run during implementation) finds additional unsafe sites in other `.sh` files under `scripts/` or `skills/*/scripts/`, convert them with the same pattern in the same PR. The plan reserves up to ~20 additional lines of changes across grep-discovered sites.

### NEW: `scripts/lint-skill-md-flag-signature.sh`

Bash 3.2-compatible linter. Scope: walks `skills/**/SKILL.md` only (mirror the minimum-change SIMPLE scope; reference-file coverage deferred to a follow-up if needed). Behavior:

1. For each `skills/<skill>/SKILL.md` file, scan for fenced ` ```bash `, ` ```sh `, or ` ```shell ` blocks (track open/close fence state).
2. Inside fenced blocks, find logical-command lines that match an invocation shape: a script-path token (absolute path containing `/scripts/<name>.sh` OR `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh` OR `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<name>.sh`) followed by one or more `--<flag>` args. **Multi-line invocation handling**: assemble a logical command by concatenating consecutive lines ending in `\` (continuation marker), then extract all `--<flag>` args from the assembled command — this matches the canonical `/design` SKILL.md call shape where the script path is on the first line and flags are on continuation lines (FINDING_10).
3. For each unique `(script_path, flag)` pair extracted, locate the target script file in the repo (resolve `${CLAUDE_PLUGIN_ROOT}` against repo root). If the script does not exist, log a `WARN` line and skip. If it exists, grep for `--<flag>)` as a `case` arm; if not found, emit a finding.
4. Skip findings on lines containing `# lint-skill-md-flag-signature: ok <reason>` (same logical-command or immediately preceding line in the SKILL.md).
5. Exit 0 on no findings; exit 1 on findings.

Output format: `<skill-md-path>:<line>: invocation uses --<flag> but <script-path> does not declare it`.

Argv: `--root <repo-root>` (default: parent of script dir, mirroring `lint-readability-preamble.sh`). `--help`/`-h`.

Style: mirror `scripts/lint-readability-preamble.sh` exactly for argv parsing, root resolution, exit codes, and error formatting.

### NEW: `scripts/lint-skill-md-flag-signature.md`

Sibling contract (~30 lines). Documents:
- Purpose: catch SKILL.md ↔ shipped-script flag drift (issue #3077 Section B class). PR #3024 introduced the drift; this linter prevents recurrence.
- Scope: `skills/**/SKILL.md` (single statement matching behavior + hook wiring). Reference files (`skills/*/references/*.md`) are NOT scanned in this initial implementation.
- Multi-line invocation handling: logical commands are assembled across trailing-backslash continuation lines before flag extraction.
- Inputs: `skills/*/SKILL.md`; target scripts resolved at runtime.
- Output: machine-readable mismatch list on stderr; exit 1 on failure.
- Waiver convention: `# lint-skill-md-flag-signature: ok <reason>` inline comment.
- Harness: `scripts/test-lint-skill-md-flag-signature.sh`.
- Edit In Sync: update this file when adding new script invocation patterns to recognize.

### NEW: `scripts/test-lint-skill-md-flag-signature.sh`

Hermetic harness. Creates fixture SKILL.md + script pairs in `$TMPROOT/skills/<fixture>/`. Test cases:
1. **Pass — flag in script**: SKILL.md invokes script with `--known-flag`; script `case` declares `--known-flag)`; linter exits 0.
2. **Fail — flag missing**: SKILL.md invokes script with `--unknown-flag`; script does NOT declare it; linter exits 1 with the expected `... invocation uses --unknown-flag but ... does not declare it` message.
3. **Multiple mismatches**: 3 missing flags across 2 SKILL.md files; linter reports all 3.
4. **Waiver**: SKILL.md line carries `# lint-skill-md-flag-signature: ok <reason>` on the same line; linter exits 0.
5. **Multi-line continuation fixture** (FINDING_10): SKILL.md invokes script across multiple lines using trailing-backslash continuations (mirror the current `write-run-params.sh` 10-flag call shape — script path on first line, `--<flag>` args on continuation lines). With drift (`--reason` missing from script case), the linter exits 1. Without drift (script declares all 10 flags), the linter exits 0.
6. **Regression pin for #3077**: fixture mirrors the broken `skills/design/SKILL.md` call-site (with `--reason`, `--source`, etc.) and the current `scripts/write-run-params.sh` `case` block; the linter MUST exit non-zero. After applying the Option A `write-run-params.sh` patch (also in this fixture), the linter exits 0.

Hermetic invariant: `$TMPROOT` is created via `mktemp -d`, trap-cleaned, no dependency on repo state.

### NEW: `scripts/test-lint-skill-md-flag-signature.md`

Sibling harness contract (~15 lines).

### NEW: `scripts/lint-renderer-substitution-safety.sh`

Bash 3.2-compatible linter. Inputs: scans `scripts/*.sh` and `skills/*/scripts/*.sh`. Behavior:

1. For each `.sh` file, grep for the unsafe pattern: `${VAR//PATTERN/$REPLACEMENT}` where `$REPLACEMENT` is a **shell variable expansion**, not an ANSI-C literal.

   **Tightened regex** (FINDING_2): the replacement position must match `\$[A-Za-z_][A-Za-z0-9_]*` (a bare `$name` expansion) OR `\$\{[A-Za-z_]` (a `${name}` expansion form). Replacements that begin with `$'` (ANSI-C escape sequences like `$'\n'`) are NOT flagged — they are byte-literal by definition and cannot contain user data. Concrete pattern: `\$\{[A-Za-z_][A-Za-z0-9_]*//[^/]*/(\$[A-Za-z_][A-Za-z0-9_]*|\$\{[A-Za-z_])`.

2. For each match, check the same line OR the immediately preceding line for `# lint-renderer-safe: ok <reason>`. Skip if present.
3. Skip matches inside other test fixtures: any line inside a heredoc body delimited by `<<'EOF'` or similar quoted delimiters (track heredoc state). This avoids false positives on linter harness fixtures.
4. Exit 0 on no findings; exit 1 on findings with one-line-per-finding output: `<path>:<line>: unsafe \${VAR//pat/$rep} substitution; use %%/## split or add inline # lint-renderer-safe: ok <reason>`.

Argv: `--root <repo-root>`, `--help`/`-h`. Style: mirror `lint-readability-preamble.sh`.

### NEW: `scripts/lint-renderer-substitution-safety.md`

Sibling contract (~25 lines). Documents purpose (Section A class — bash 5.x `&` corruption), inputs, output format, waiver convention, harness, Edit In Sync. Explicitly states that `$'...'` ANSI-C escapes in the replacement position are excluded from the unsafe class.

### NEW: `scripts/test-lint-renderer-substitution-safety.sh`

Hermetic harness. Test cases:
1. **Pass — safe pattern**: fixture uses `${var%%PATTERN*}` + `${var##*PATTERN}` split → linter exits 0.
2. **Pass — ANSI-C escape** (FINDING_2): fixture uses `${out//$'\n'/$'\n    '}` (matches the existing safe site at `skills/implement/scripts/test-check-review-changes.sh:119`) → linter exits 0 without requiring a waiver.
3. **Fail — unsafe bare expansion**: fixture uses `${var//PATTERN/$rep}` (variable replacement) without waiver → linter exits 1 with expected message.
4. **Fail — unsafe braced expansion**: fixture uses `${var//PATTERN/${rep}}` (braced variable replacement) without waiver → linter exits 1.
5. **Fail — unsafe array indexing**: fixture uses `${var//PATTERN/$arr[0]}` without waiver → linter exits 1.
6. **Waiver pass (same line)**: fixture has `# lint-renderer-safe: ok <reason>` on the same line as the unsafe call → linter exits 0.
7. **Waiver pass (preceding line)**: waiver comment on the line above the unsafe call → linter exits 0.
8. **Heredoc tolerance**: unsafe pattern inside a `<<'EOF'` heredoc fixture body → linter exits 0 (heredoc fixtures must not trigger findings).
9. **Regression pin for PR #3051**: fixture mirrors pre-PR-#3051 `render-plan-review-prompt.sh` with `${prompt_body//__READABILITY_STYLE_BLOCK__/$readability_style}`; linter MUST exit 1. Post-#3051 `%%`/`##` shape MUST exit 0.

### NEW: `scripts/test-lint-renderer-substitution-safety.md`

Sibling harness contract (~15 lines).

### UPDATED: `BASH_AUTHORING.md`

Add a new sub-section appended to the existing §3 (Bash 3.2 Portability), placed immediately before `## 4. Background+propagate markers ...`:

```
### `${var//pat/rep}` and `&` in the replacement (bash 5.x divergence)

Bash 5.x treats `&` in the replacement string of `${var/pat/rep}` and `${var//pat/rep}` as the matched text (same semantics as `sed`'s `&`). Bash 3.x and 4.x treat it as a literal `&`. A file-derived replacement containing `&` (e.g., `"Strunk & White"`) silently corrupts to the matched pattern token on bash 5.x — tests pass on macOS bash 3.2 but fail in Ubuntu CI bash 5.x. Issue #3077 documents the original repro chain (PR #3051 fixed `render-plan-review-prompt.sh`).

For substitutions where `$rep` may contain `&` (file-derived content, user input, anything not statically literal), use the `%%`/`##` split pattern, which is bash 3.2 / 4.x / 5.x identical:

```bash
_before="${VAR%%PATTERN*}"
_after="${VAR##*PATTERN}"
VAR="${_before}${REPLACEMENT}${_after}"
```

`make lint-renderer-substitution-safety` enforces this for `.sh` files under `scripts/` and `skills/*/scripts/`. ANSI-C `$'...'` escapes in the replacement position are not flagged (they are byte-literal). Add `# lint-renderer-safe: ok <reason>` inline justification only when `$rep` is provably literal and cannot contain `&`.
```

### UPDATED: `Makefile`

Three coordinated edits:

1. Extend the long `.PHONY:` line (around line 4) to include `test-lint-skill-md-flag-signature` and `test-lint-renderer-substitution-safety`.
2. Extend the separate `.PHONY:` line for lint targets (around line 13-19) to include `lint-skill-md-flag-signature test-lint-skill-md-flag-signature lint-renderer-substitution-safety test-lint-renderer-substitution-safety`.
3. Update the `lint:` rule (line 23) to chain both new linters:
   ```
   lint: test-harnesses lint-bash32 lint-foreground-markers lint-readability-preamble lint-skill-md-flag-signature lint-renderer-substitution-safety lint-only
   ```
4. Add two new rule blocks (mirror `lint-readability-preamble:` exactly):
   ```
   lint-skill-md-flag-signature:
   	@bash scripts/lint-skill-md-flag-signature.sh

   lint-renderer-substitution-safety:
   	@bash scripts/lint-renderer-substitution-safety.sh

   test-lint-skill-md-flag-signature:
   	@bash scripts/test-lint-skill-md-flag-signature.sh

   test-lint-renderer-substitution-safety:
   	@bash scripts/test-lint-renderer-substitution-safety.sh
   ```
5. Append `test-lint-skill-md-flag-signature test-lint-renderer-substitution-safety` to one of the `test-harnesses-N` chains so `make test-harnesses` picks them up. Pick the shard with the lightest existing load.

### UPDATED: `agent-lint.toml`

Add the four new script paths to the dead-script allowlist (FINDING_8) so `make lint` does not fail with "dead script" findings after wiring the targets. Mirror the existing exclusion pattern for `lint-readability-preamble` and `lint-foreground-markers`. Paths to add (siblings to existing entries):

- `scripts/lint-skill-md-flag-signature.sh`
- `scripts/lint-renderer-substitution-safety.sh`
- `scripts/test-lint-skill-md-flag-signature.sh`
- `scripts/test-lint-renderer-substitution-safety.sh`

The sibling `.md` files are documentation and follow the existing `.md` exclusion rules (not subject to dead-script analysis).

### UPDATED: `.pre-commit-config.yaml`

Add two new local hooks mirroring the existing `lint-readability-preamble` and `lint-foreground-markers` entries. **Both new hooks set `always_run: true`** (FINDING_1) so scoped `pre-commit run --files` invocations cannot skip the cross-repo scan; this matches the existing `lint-readability-preamble` hook shape.

```yaml
      - id: lint-skill-md-flag-signature
        name: lint-skill-md-flag-signature
        entry: bash scripts/lint-skill-md-flag-signature.sh
        language: system
        pass_filenames: false
        always_run: true

      - id: lint-renderer-substitution-safety
        name: lint-renderer-substitution-safety
        entry: bash scripts/lint-renderer-substitution-safety.sh
        language: system
        pass_filenames: false
        always_run: true
```

`pass_filenames: false` because both linters walk the repo themselves; `always_run: true` because they scan the full surface, not just the modified files.

## Edge cases

- **Bash 3.2 portability**: all new shell scripts use only Bash 3.2-compatible constructs (no `${var^^}`, no associative arrays, no `mapfile`). `make lint-bash32` covers this; both new linters' source files are subject to it.
- **Schema v2 → v3 read compatibility**: existing readers (e.g., `scripts/read-design-classification.sh`) must accept `schema_version >= 2`. Audit during implementation; expected: most readers use `jq -r '.design_classification // "HARD"'` and don't pin the version. Add an explicit `schema_version >= 2` jq guard if any reader rejects unknown schema versions.
- **Empty `--reason` / `--source`** (FINDING_4): accept empty strings; the empty-tolerant parser captures `""` and `jq` converts it to JSON `null`. The `${2:?}` strict form is only used for required flags (`--classification`, `--output`).
- **`--sketch-budget` enum**: 0/2/4 only per `flags.md`. Reject other integers (including negative numbers and non-numeric values). SIMPLE maps to `0` (no sketches), HARD to `4` (FINDING_5).
- **Test argv form** (FINDING_6): all test invocations use space-separated `--flag value` form. The writer parser explicitly does not support `--flag=value` equals form, so equals-form invocations would silently fall through the `case` block as unknown flags.
- **Waiver comment syntax**: both new linters accept the inline comment on the same line OR the immediately preceding line. Multi-line waivers are not supported (keep grep cheap).
- **Renderer-safety linter scope-pinning** (FINDING_2): the unsafe-replacement regex matches only shell variable expansions in the replacement position — bare `$name` or `${name...}`. ANSI-C `$'...'` escape sequences are byte-literal and excluded. The existing safe site at `skills/implement/scripts/test-check-review-changes.sh:119` (`${out//$'\n'/$'\n    '}`) MUST NOT trigger a finding without a waiver.
- **SKILL.md ↔ script linter scope**: only check invocations where the script path is fully resolvable (absolute or `${CLAUDE_PLUGIN_ROOT}/...` form). Skip ambiguous interpolated paths with a `WARN` log entry — the harness fixture for ambiguous paths must NOT cause a false-positive finding. Linter scope is `skills/**/SKILL.md` only (single consistent statement across behavior, docs, and hook wiring).
- **Pre-commit hook performance**: both linters should complete in <2s on the full repo. The flag-signature linter walks `skills/**/SKILL.md` (small set); the renderer-safety linter walks `scripts/*.sh` and `skills/*/scripts/*.sh` (also small). Avoid heavyweight `find` traversals.
- **Linter harness fixtures must not self-trip**: both test scripts contain unsafe-pattern fixture text. The renderer-safety linter must skip heredoc bodies; the flag-signature linter's fixture lives in `$TMPROOT`, outside the repo scan root.
- **Tier-derived assignment in Step 0b** (FINDING_3): the SKILL.md edit pins SIMPLE→sketch_budget=0 and HARD→sketch_budget=4. The empty-string-tolerant parser in `write-run-params.sh` remains as defense-in-depth for direct script invocations, but the canonical SKILL.md call always supplies non-empty values for all 10 flags.

## Failure modes

1. **write-run-params.sh schema migration breaks downstream readers.** Earliest warning: `make test-harnesses` failure on harnesses that parse `run-params.json` (e.g., a test that pins `schema_version == 2`). Mitigation: audit `read-design-classification.sh` and any other readers before merging; harness must include a v2-tolerant-but-v3-aware round-trip test.

2. **SKILL.md ↔ script linter false-positives on legitimate invocations.** Earliest warning: linter flags a `--<flag>` that the script intentionally rejects (e.g., a documented-removed flag retained in docs for deprecation messaging). Mitigation: ship with the inline `# lint-skill-md-flag-signature: ok <reason>` waiver convention; document common false-positive shapes in the sibling `.md`; add a fixture for the deprecation-doc case.

3. **Renderer-safety linter under- or over-matches `${var//pat/$rep}` syntax variants.** Earliest warning: harness fixtures in `test-lint-renderer-substitution-safety.sh` expose a variant the linter doesn't catch (under) or a safe variant the linter wrongly flags (over). Mitigation: include multiple syntax variants in the fixture (bare `$name`, braced `${name}`, array indexing `${arr[0]}`, ANSI-C `$'...'` escapes); start strict on the regex and add fixture-driven waivers as the implementation lands.

## Testing strategy

- **`scripts/test-write-run-params.sh`**: extend to cover all 5 new flags + schema v3 fields + invalid-value rejection (space-form, not equals-form) + empty-string tolerance. Run via `make test-write-run-params`.
- **`scripts/test-lint-skill-md-flag-signature.sh`**: new hermetic harness. Run via `make test-lint-skill-md-flag-signature`. Includes the #3077 regression-pin fixture (broken SKILL.md call site → linter exit 1; fixed call site → exit 0) AND the multi-line continuation fixture (trailing-backslash invocation shape).
- **`scripts/test-lint-renderer-substitution-safety.sh`**: new hermetic harness. Run via `make test-lint-renderer-substitution-safety`. Includes the PR #3051 regression-pin fixture (pre-fix `${var//__READABILITY_STYLE_BLOCK__/$readability_style}` → linter exit 1; post-fix `%%`/`##` shape → exit 0) AND the ANSI-C escape pass fixture (mirrors the existing safe site at `test-check-review-changes.sh:119`).
- **End-to-end repro**: after the fix lands, run `/larch:design --simple <test-issue>`; assert `run-params.json` contains `design_classification: "SIMPLE"` with `schema_version: 3` and all 5 new v3 fields populated; assert the SIMPLE flow runs (no sketches, no dialectic).
- **`make lint`**: verify the full chain (`make lint`) exits 0 on the working tree with all new linters active.
- **`make test-harnesses`**: extend to include both new test harnesses; verify shard CI green.


## Acceptance

- **Section A**: `BASH_AUTHORING.md` §3 documents the `${var//pat/rep}` + `&` bash 5.x divergence; all unsafe `${var//pat/$rep}` callsites under `scripts/` and `skills/*/scripts/` either use the `%%`/`##` split pattern or carry an inline `# lint-renderer-safe: ok <reason>` justification; the new `lint-renderer-substitution-safety.sh` linter exits 0 on the working tree and exits 1 on a fixture that mirrors pre-PR-#3051 `render-plan-review-prompt.sh`.
- **Section B**: `scripts/write-run-params.sh` accepts all 10 SKILL.md-documented flags and emits `schema_version: 3` JSON with 5 new optional fields (`design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, `workflow_path`); `bash scripts/test-write-run-params.sh` exits 0; `/larch:design --simple <issue>` produces `run-params.json` with `design_classification: "SIMPLE"` and `schema_version: 3` and runs the SIMPLE flow (no sketches, no dialectic); the Step 0b "fall back to HARD" recovery branch is replaced with a loud abort.
- **Section C**: `scripts/lint-skill-md-flag-signature.sh` and `scripts/lint-renderer-substitution-safety.sh` are registered in `make lint` and `.pre-commit-config.yaml` (with `always_run: true`); `make lint` exits 0 on the PR's working tree; reverting the SKILL.md call site in `git show 5a2e463b` makes `lint-skill-md-flag-signature.sh` exit non-zero (covered by harness fixture).

diff_lines: 680

## Test plan
(no test plan section in plan-file)
