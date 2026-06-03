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


### FINDING_10: No structural pin for `set +e` / `_argv_rc` capture in Step 0-pre fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` does not pin the Step 0-pre fence’s `set +e` / `_argv_rc` / `VALIDATION_ERROR` handling. Removing `set +e` would trip `set -e` before validation handling; CI would not catch it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep/contains pins like design-postplan-emit set +e coverage.


### FINDING_12: `CLAUDE_PLUGIN_ROOT` empty-only guard misses unexpanded template literal
- **Reviewer(s)**: dyn-skill-fence-kv-protocol-output.txt
- **Severity**: important
- **Concern**: Step 0-pre uses `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` and aborts only when empty. If the skill loader fails to expand the template, Bash assigns the literal string `${CLAUDE_PLUGIN_ROOT}` (non-empty), the guard does not fire, and the parser invoke resolves to a bogus path instead of failing closed before session setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-fence-kv-protocol-output.txt: After export, reject the literal unexpanded token (e.g. `[ "$CLAUDE_PLUGIN_ROOT" = '${CLAUDE_PLUGIN_ROOT}' ]`) and/or require `-x "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/parse-design-argv.sh"` before running the parser, matching a path-exists check rather than emptiness alone.


### FINDING_14: Top-of-skill Flags prose conflicts with Step 0-pre parser authority
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: SKILL.md lines 12–27 still instruct mental `$ARGUMENTS` parsing while Step 0-pre/0b use `parse-design-argv.sh` KVs only. Operators reading the intro could misinterpret flag/positional semantics (e.g. `/design 3249 --hard`) despite parser output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a one-line authority note at the Flags intro pointing to Step 0-pre parse-design-argv.sh and POSITIONAL_KIND/POSITIONAL_VALUE.


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


### FINDING_9: Harness omits plan-listed `--` and `--run-id`+verbal cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-parse-design-argv.sh` lacks cases for lone end-of-options (`--hard --` → `POSITIONAL_KIND=none`) and `--run-id` with verbal tail (`--run-id r1 add a thing`). Regression in `--` or run-id+verbal parsing could ship despite green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness cases for --hard -- (POSITIONAL_KIND=none) and --run-id r1 add a thing (verbal + RUN_ID).


