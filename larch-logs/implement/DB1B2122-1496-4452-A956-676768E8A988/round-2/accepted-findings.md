### FINDING_1: Plan/doc drift — no `usage()` / exit 2; dead `lib-quiet` wiring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan and acceptance text call for a defensive `usage()` path (`larch_err` + exit **2**), and `parse-design-argv.md` still references `larch_err`, but the shipped script sources `lib-quiet.sh`, never calls `larch_err`, has no `usage()`, and only exits **0** or **3**. The contract doc simultaneously says the script “never exits `1` or `2`.” `SKILL.md` Step 0-pre still treats exit **2** as a distinct abort path, but the parser cannot emit it today — planned defensive misuse handling is unimplemented and docs contradict each other and the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove lib-quiet source/init and update parse-design-argv.md stdout-only section.
  - From cursor-specialist-plan-fidelity-output.txt: Add usage() calling larch_err with exit 2; update parse-design-argv.md exit-code table to include 2 (never 1); keep SKILL.md non-zero RC handling for exit 2.
  - From cursor-specialist-testing-output.txt: Either align the doc with the implementation (intentionally no exit `2`) or add a minimal `usage()` path and one harness case if exit `2` is still desired for misuse.


### FINDING_11: Harness gaps — `--medium`, exact KV count, `--run-id` newline
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-parse-design-argv.sh` retired `--simple` validation but not `--medium`; success-path cases assert individual KVs but never that stdout is exactly eight lines with no extras; `assert_safe_kv_value` newline smuggling is exercised for verbal positionals but not for `--run-id`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add --medium 3249 validation-error case mirroring --simple.
  - From cursor-specialist-testing-output.txt: Add a helper (e.g. `assert_success_kv_count 8`) on at least one representative success case so a partial or polluted stdout contract fails fast. Today coverage is spread across cases, so a regression that drops one KV line could slip through if only a subset of assertions run.
  - From cursor-specialist-testing-output.txt: Add `run_case --run-id $'bad\nid' 3249` expecting `VALIDATION_ERROR=newline-in-value` and exit `3`, mirroring the verbal newline case at lines 1033-1037 of the harness.


### FINDING_2: `SKILL.md` Positional tail prose still describes pre-0-pre parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The top-level Positional tail bullet still describes inline flag/tail parsing and mental flag-first scanning of `$ARGUMENTS`, despite Step 0-pre / `parse-design-argv.sh` being the sole authority. An orchestrator reading only the Flags section may re-scan argv after the fence and honor flags after an issue number, contrary to the parser contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Defer classification details to parse-design-argv.md; keep table as index only.
  - From cursor-specialist-correctness-output.txt: Rewrite Positional tail to reference POSITIONAL_KIND/POSITIONAL_VALUE and parse-design-argv.md.


### FINDING_3: Step 0-pre success path emits no orchestrator-visible KV stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-kv-protocol-output.txt
- **Severity**: important
- **Concern**: Step 0-pre captures `parse-design-argv.sh` stdout only via command substitution and never prints bound KVs on success, so the Bash tool returns empty output on the happy path. Bash variables set in the loop do not survive the subshell; Step 0b prose requires consuming `POSITIONAL_KIND` / `POSITIONAL_VALUE` from Step 0-pre, but there is no machine-readable artifact — only empty tool output plus LLM memory of `$ARGUMENTS`. That re-opens the re-parse drift the refactor removes at the script layer (e.g. `3249 --hard` pinned as issue + `HARD_REQUESTED=false`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After parsing, emit the eight KVs (or printf the full _argv_out) to stdout before the fence exits 0, matching Step 0a's visible KV stream pattern.
  - From dyn-kv-protocol-output.txt: On `_argv_rc=0`, `printf '%s\n' "$_argv_out"` (or emit the bound KVs) before the fence ends, so the next turn can parse the same stream Step 0b is required to trust; alternatively fold argv parse into the Step 0a block where session KVs are already echoed.


### FINDING_4: Step 0-pre does not fail closed on incomplete eight-KV success matrix
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-kv-protocol-output.txt
- **Severity**: important
- **Concern**: After `_argv_rc=0`, the Step 0-pre consumer loop never verifies that stdout contains the full eight-KV success matrix from `parse-design-argv.md`. If the script regresses (empty stdout, truncated output, or a partial line set) while still exiting 0, the fence keeps pre-loop defaults (`hard_requested=false`, `POSITIONAL_KIND=none`, empty `run_id`, etc.) and continues into session-setup without aborting — silently dropping flags or mis-classifying the positional tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After the parse loop, fail closed unless every required key is set and POSITIONAL_KIND is one of issue, verbal, or none.
  - From dyn-kv-protocol-output.txt: After the `while` loop on the success path, require all eight keys (count lines, or set `_seen_*` flags per key) and `exit 1` with a diagnostic if any are missing; mirror the “mandatory KV matrix” pattern used by `design-postplan-emit.sh` tests.


### FINDING_5: `<PUBLIC_ARGV_WORDS>` template expansion is fragile and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-template-expansion-output.txt
- **Severity**: latent
- **Concern**: Step 0-pre depends on runtime substitution of `<PUBLIC_ARGV_WORDS>` with per-token shell quoting enforced only by orchestrator discipline, not mechanical CI on rendered fences. Risks include: unexpanded `<PUBLIC_ARGV_WORDS>` being parsed as stdin redirection (empty argv → silent `POSITIONAL_KIND=none`); metacharacters in `POSITIONAL_VALUE` executing before the parser if verbal argv is not single-quoted per token; CI only pinning that the placeholder string exists in committed `SKILL.md`, not that loaders substitute or that fences include expansion guards; generic abort messages that do not distinguish template-substitution failure from other errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider runtime guard or stronger orchestrator checklist if mis-substitution is observed.
  - From cursor-specialist-testing-output.txt: Add a small integration harness (or extend `test-parse-design-argv.sh`) that invokes the parser the way the fence should after substitution (e.g. `parse-design-argv.sh '--hard' 'add a foo'`), and/or add a structural/renderer check that the skill loader never leaves the literal placeholder or re-tokenizes verbal tails into a single word. The plan’s failure-mode section already calls this out; CI currently only guarantees the placeholder string exists (`scripts/test-design-structure.sh:266-267`).
  - From cursor-specialist-security-output.txt: Add renderer/lint coverage or a structural test that rendered fences use quoted tokens; keep the documented handoff in parse-design-argv.md as the contract.
  - From dyn-template-expansion-output.txt: Avoid `<…>` shell-redirection syntax for argv entirely—e.g. end the fence with `"$@"` and have the orchestrator run the block with public argv as trailing parameters (`bash … -- --hard 3249`), or substitute quoted tokens before Bash and add a pre-invoke guard that aborts if the rendered command still matches `<PUBLIC_*>` / has zero args when `$ARGUMENTS` was non-empty. Mirror the `CLAUDE_PLUGIN_ROOT` “unexpanded template literal” pattern for whatever substitution mechanism you keep.
  - From dyn-template-expansion-output.txt: Add a pin for an argv expansion guard in the `step0pre_block` (e.g. forbid a bare `<PUBLIC_ARGV_WORDS>` token on the invoke line in rendered fences, or require a documented post-substitution sentinel), and/or add a small harness that renders a sample fence and asserts the invoke line contains quoted argv tokens and no `<PUBLIC_ARGV_WORDS>` redirection.
  - From dyn-template-expansion-output.txt: After capture, if `_argv_rc` is non-zero and stderr/stdout mentions `PUBLIC_ARGV_WORDS`, print an explicit “skill loader did not expand `<PUBLIC_ARGV_WORDS>`” diagnostic; optionally treat `POSITIONAL_KIND=none` plus non-empty user `$ARGUMENTS` as a hard abort in orchestrator prose (even if the script correctly classifies empty argv).


