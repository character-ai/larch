Reviewing the cited files to confirm merge groupings and extract verbatim revision text.
### FINDING_1: `usage()` and exit 2 are dead / contract drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `parse-design-argv.sh` defines `usage()` and the contract documents exit **2**, but no code path invokes `usage()` or exits 2 (empty argv is valid `POSITIONAL_KIND=none`). Operators cannot get usage diagnostics; docs and tests promise behavior that never fires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove usage() or wire it to a real misuse path; align parse-design-argv.md exit table with behavior.
  - From cursor-specialist-correctness-output.txt: Call `usage` + exit 2 only for true internal misuse if desired, or drop exit 2 from the contract and docs.
  - From cursor-specialist-testing-output.txt: Remove dead usage() or add a misuse harness case for exit 2.
  - From cursor-specialist-edge-cases-output.txt: Wire usage on misuse or remove exit 2 from contract.
  - From cursor-specialist-plan-fidelity-output.txt: Wire usage() on invalid invocation or remove until needed.

### FINDING_2: Numeric issue path silently drops trailing positional tokens
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-partial-emission-coverage-output.txt
- **Severity**: latent
- **Concern**: After the flag scan, the parser joins remaining argv into `positional_value`, but when `first_positional` matches `^[0-9]+$` it sets `POSITIONAL_KIND=issue` and `POSITIONAL_VALUE=first_positional` only, discarding later tokens without error (e.g. `/design 3249 extra words` → issue `3249`, trailing text lost). Verbal classification keeps the full joined tail; issue classification does not. This is a silent footgun if the user meant a multi-token verbal tail starting with digits, and the join loop is misleading structure that increases future-edit risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document issue-only-first-token in parse-design-argv.md or simplify code; optionally treat numeric-first multi-token as verbal.
  - From cursor-specialist-correctness-output.txt: Either document in `parse-design-argv.md` that extra tokens after a numeric issue are ignored, or treat “first token all-digit + more tokens” as `verbal` with the full joined tail (only if product intent changes).
  - From cursor-specialist-edge-cases-output.txt: Document in parse-design-argv.md; add harness case or reject extra tokens after numeric issue.
  - From cursor-specialist-plan-fidelity-output.txt: Document issue-first-token-only semantics and add a harness case or change classification rules.
  - From dyn-partial-emission-coverage-output.txt: Document the discard rule explicitly in `parse-design-argv.md` and `references/flags.md` if it is intentional; add a harness case pinning `POSITIONAL_VALUE=3249` for `3249 extra` (and optionally `3249 --hard` vs verbal `3249 --hard` via `--`). If trailing words should be preserved or rejected, change classification accordingly and test that behavior.
  - From dyn-partial-emission-coverage-output.txt: Either skip the join loop when `first_positional` matches `^[0-9]+$`, or classify issue vs verbal before joining so the implementation matches the documented contract in one place.

### FINDING_3: `<PUBLIC_ARGV_WORDS>` substitution lacks mechanical guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-skill-fence-kv-protocol-output.txt
- **Severity**: important
- **Concern**: Step 0-pre passes argv through the orchestrator-only `<PUBLIC_ARGV_WORDS>` placeholder with no CI pin that the rendered fence contains real shell-quoted words. If the orchestrator leaves the placeholder literal, substitutes a single re-tokenized string, or mis-quotes verbal tails, Bash can treat `<PUBLIC_ARGV_WORDS>` as stdin redirection or otherwise mis-invoke the parser; `POSITIONAL_VALUE` diverges from user intent while script-level tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add structural grep or renderer lint for the placeholder; keep prose quoting discipline in parse-design-argv.md.
  - From cursor-specialist-correctness-output.txt: Keep the documented quoting discipline in `parse-design-argv.md`; consider a structural pin that the Step 0-pre fence must not contain a literal `<PUBLIC_ARGV_WORDS>` after render (or document the loader contract in `test-design-structure.sh`).
  - From cursor-specialist-testing-output.txt: Keep .md handoff discipline; consider structural anti-pattern pin on unquoted ARGUMENTS in 0-pre fence.
  - From cursor-specialist-security-output.txt: Enforce printf %q-style substitution via lint or pass argv through a non-interpolated channel.
  - From cursor-specialist-edge-cases-output.txt: Pin against literal placeholder in SKILL.md; document required quoted-token expansion in parse-design-argv.md.
  - From dyn-skill-fence-kv-protocol-output.txt: Add a `test-design-structure.sh` grep pin forbidding literal `<PUBLIC_ARGV_WORDS>` in the Step 0-pre fence, document a concrete before/after example in `parse-design-argv.md` (e.g. three-token verbal tail → `'--hard' 'add' 'a foo'`), and/or pass argv via a dedicated env var or newline-delimited stdin protocol so the fence is not LLM-interpolated.

### FINDING_4: `assert_no_flag_kvs` only checks two success KV prefixes on exit 3
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-partial-emission-coverage-output.txt
- **Severity**: latent
- **Concern**: On validation failure (exit 3), the contract requires stdout to emit only `VALIDATION_ERROR=<token>`, but `assert_no_flag_kvs` greps only `HARD_REQUESTED` and `POSITIONAL_KIND`. A regression that emitted any of the other six success keys (`PARTITION_REQUESTED`, `BRAINSTORM_REQUESTED`, `MANUAL_REQUESTED`, `NO_DEDUP_REQUESTED`, `RUN_ID`, `POSITIONAL_VALUE`) alongside or before `VALIDATION_ERROR` would still pass harness tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert stdout on exit 3 matches only VALIDATION_ERROR= or grep -v all eight success key names.
  - From cursor-specialist-testing-output.txt: Assert no success KV lines on validation failure (full key set or exact one-line stdout).
  - From cursor-specialist-edge-cases-output.txt: Assert exact stdout shape on exit 3 (only VALIDATION_ERROR= line).
  - From dyn-partial-emission-coverage-output.txt: Replace the two-key grep with a denylist of all eight success KV prefixes (or assert stdout is exactly one `VALIDATION_ERROR=` line plus optional trailing newline), and add a harness case that deliberately expects failure if any success KV appears on exit 3.

### FINDING_5: Empty sole positional classified as `none`, not `verbal`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A sole positional argument that is an empty string (`parse-design-argv.sh ""`) is classified as `POSITIONAL_KIND=none` because `[ -z "$first_positional" ]` runs before the verbal branch. The “non-empty non-numeric → verbal” rule never applies to an empty first token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If empty verbal tails matter, treat `first_positional` present-but-empty as `verbal` with `POSITIONAL_VALUE=`; otherwise document that empty argv tokens collapse to `none`.

### FINDING_6: Embedded newlines in emitted KV values enable stdout smuggling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-skill-fence-kv-protocol-output.txt
- **Severity**: important
- **Concern**: `parse-design-argv.sh` emits `POSITIONAL_VALUE` (and other values) via `printf '%s\n'` without rejecting embedded newlines/CR. A verbal argv token like `$'foo\nHARD_REQUESTED=true'` produces extra stdout lines; the Step 0-pre `while read` loop then mis-binds or accepts spoofed keys while the parser exit code remains 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document “no embedded newlines in verbal argv tokens,” or use a delimiter-safe parse (e.g. require the orchestrator to pass JSON, or read only known keys and treat everything after `POSITIONAL_VALUE=` on the first line as the value until the next known key prefix).
  - From cursor-specialist-security-output.txt: Reject newline/CR in all emitted values or encode values; add harness cases for smuggling.
  - From cursor-specialist-edge-cases-output.txt: Reject newlines in parser output values or use a safer transport than line-KV for values.
  - From dyn-skill-fence-kv-protocol-output.txt: Reject or escape embedded newlines in `parse-design-argv.sh` (validation error or encode), or switch the machine contract to length-prefixed/base64/JSON lines; add a harness case for `POSITIONAL_VALUE` with `=` and document that newlines are unsupported.

### FINDING_7: Step 0-pre KV loop lacks allowlist / fail-closed parsing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The Step 0-pre fence accepts any `KEY=value` line from captured stdout via a generic `case` and last-wins assignment. Injected lines in `_argv_out` can override `HARD_REQUESTED`, `POSITIONAL_KIND`, or `VALIDATION_ERROR` without a failed parser exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse only an allowlisted fixed key set; fail closed on extra lines; require _argv_rc=3 for validation errors.

### FINDING_8: Success path does not fail-closed when expected KVs are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `_argv_rc=0`, the Step 0-pre fence does not assert that all eight success KVs were present. Truncated stdout or missing keys leave defaults (`hard_requested=false`, `POSITIONAL_KIND=none`, etc.) and `/design` continues with wrong flags and positional kind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After parsing, require non-empty `POSITIONAL_KIND` and that `HARD_REQUESTED` (and optionally all five `*_REQUESTED` keys) appeared in `_argv_out` before Step 0a.
  - From cursor-specialist-edge-cases-output.txt: Fail closed unless POSITIONAL_KIND is valid and all expected KVs were parsed.

### FINDING_9: Harness omits plan-listed `--` and `--run-id`+verbal cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-parse-design-argv.sh` lacks cases for lone end-of-options (`--hard --` → `POSITIONAL_KIND=none`) and `--run-id` with verbal tail (`--run-id r1 add a thing`). Regression in `--` or run-id+verbal parsing could ship despite green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness cases for --hard -- (POSITIONAL_KIND=none) and --run-id r1 add a thing (verbal + RUN_ID).

### FINDING_10: No structural pin for `set +e` / `_argv_rc` capture in Step 0-pre fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` does not pin the Step 0-pre fence’s `set +e` / `_argv_rc` / `VALIDATION_ERROR` handling. Removing `set +e` would trip `set -e` before validation handling; CI would not catch it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep/contains pins like design-postplan-emit set +e coverage.

### FINDING_11: Success path does not assert exactly eight stdout KV lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness success paths do not assert exactly eight stdout KV lines or one occurrence per contract key on exit 0. Extra stdout lines could confuse orchestrator KV parsing without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert line count 8 and one occurrence per contract key on exit 0.

### FINDING_12: `CLAUDE_PLUGIN_ROOT` empty-only guard misses unexpanded template literal
- **Reviewer(s)**: dyn-skill-fence-kv-protocol-output.txt
- **Severity**: important
- **Concern**: Step 0-pre uses `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` and aborts only when empty. If the skill loader fails to expand the template, Bash assigns the literal string `${CLAUDE_PLUGIN_ROOT}` (non-empty), the guard does not fire, and the parser invoke resolves to a bogus path instead of failing closed before session setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-fence-kv-protocol-output.txt: After export, reject the literal unexpanded token (e.g. `[ "$CLAUDE_PLUGIN_ROOT" = '${CLAUDE_PLUGIN_ROOT}' ]`) and/or require `-x "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/parse-design-argv.sh"` before running the parser, matching a path-exists check rather than emptiness alone.

### FINDING_13: `POSITIONAL_KIND=none` does not gate before session-setup / `gh issue view`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `/design` with only flags or empty argv yields `POSITIONAL_KIND=none` but still proceeds to Step 0a session setup and later `gh issue view` with unset/empty `ISSUE_NUMBER` instead of aborting early with an explicit cancel path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Abort before session-setup or define explicit cancel path when POSITIONAL_KIND=none.

### FINDING_14: Top-of-skill Flags prose conflicts with Step 0-pre parser authority
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: SKILL.md lines 12–27 still instruct mental `$ARGUMENTS` parsing while Step 0-pre/0b use `parse-design-argv.sh` KVs only. Operators reading the intro could misinterpret flag/positional semantics (e.g. `/design 3249 --hard`) despite parser output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a one-line authority note at the Flags intro pointing to Step 0-pre parse-design-argv.sh and POSITIONAL_KIND/POSITIONAL_VALUE.

### FINDING_15: `--run-id` value not validated as log slug at parse time
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--run-id` accepts arbitrary strings without slug validation. Future wiring of `RUN_ID` to larch-logs paths could allow path traversal or invalid directory names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply larch_log_slug_is_valid at parse time; test ../bad and newline run-id.

### OOS_1: [OUT_OF_SCOPE] `assert_no_flag_kvs` gap is test-hardening only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `assert_no_flag_kvs` only greps for `HARD_REQUESTED` and `POSITIONAL_KIND`, not all eight success keys — out of scope for parser behavior; test-hardening only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (No separate fix beyond noting test-hardening scope; in-scope reviewers cover the same gap in FINDING_4.)

### OOS_2: [OUT_OF_SCOPE] `test-design-structure.sh` missing Step 0-pre contract pins
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Structural pins cover script presence, `VALIDATION_ERROR` / `POSITIONAL_KIND` in the script, SKILL wiring, and removal of `remaining tokens after flags`, but not the plan’s `set +e` / `_argv_rc` capture or full acceptance-level CI parity with Step 0a pins. Verdict: no in-scope Important defect on primary issue/flag paths; remaining items are latent edge cases and orchestrator hardening gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (Out of scope unless acceptance-level CI parity with Step 0a pins is desired; see FINDING_10 for the actionable pin gap.)

### OOS_3: [OUT_OF_SCOPE] `references/flags.md` positional tail not updated for parser semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Positional tail section not updated for parser/`--`/no-reparse semantics. Operators reading flags.md alone may misunderstand vs parse-design-argv.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update positional tail when flags.md is next edited for #3133 follow-ups.

### OOS_4: [OUT_OF_SCOPE] Step 0a duplicates weak `CLAUDE_PLUGIN_ROOT` guard
- **Reviewer(s)**: dyn-skill-fence-kv-protocol-output.txt
- **Severity**: latent
- **Concern**: Step 0a uses the same `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` + empty-only guard pattern; Step 0-pre duplicates a pre-existing weakness rather than introducing a new guard style.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-fence-kv-protocol-output.txt: (Pre-existing Step 0a pattern; see FINDING_12 for Step 0-pre hardening direction.)

### OOS_5: [OUT_OF_SCOPE] Structural pins do not require harness full stdout on validation failure
- **Reviewer(s)**: dyn-partial-emission-coverage-output.txt
- **Severity**: latent
- **Concern**: `test-design-structure.sh` pins assert parser script contains `VALIDATION_ERROR=` and `POSITIONAL_KIND=` and SKILL wiring, but do not require the offline harness to enforce full stdout on validation failure. Harness strengthening would close that gap without changing runtime behavior; `validation_error()` today correctly emits only `VALIDATION_ERROR` and exits 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-partial-emission-coverage-output.txt: (Harness strengthening gap; see FINDING_4 for actionable test fix.)

---

**Subsumed / not elevated**: Input FINDING_2 (embedded `=` breaks `${_line#*=}`) is contradicted by dyn-skill-fence-kv-protocol-output.txt (single-line `%%=*`/`#*=` preserves values after the first `=`) and folded into FINDING_6 only for the newline/`=` harness gap where still relevant. Input FINDING_39 recorded as non-actionable OOS confirmation only and not duplicated above.
