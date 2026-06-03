Reviewing the cited files to verify merge groupings and preserve verbatim revision text.
### FINDING_1: Plan/doc drift — no `usage()` / exit 2; dead `lib-quiet` wiring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan and acceptance text call for a defensive `usage()` path (`larch_err` + exit **2**), and `parse-design-argv.md` still references `larch_err`, but the shipped script sources `lib-quiet.sh`, never calls `larch_err`, has no `usage()`, and only exits **0** or **3**. The contract doc simultaneously says the script “never exits `1` or `2`.” `SKILL.md` Step 0-pre still treats exit **2** as a distinct abort path, but the parser cannot emit it today — planned defensive misuse handling is unimplemented and docs contradict each other and the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove lib-quiet source/init and update parse-design-argv.md stdout-only section.
  - From cursor-specialist-plan-fidelity-output.txt: Add usage() calling larch_err with exit 2; update parse-design-argv.md exit-code table to include 2 (never 1); keep SKILL.md non-zero RC handling for exit 2.
  - From cursor-specialist-testing-output.txt: Either align the doc with the implementation (intentionally no exit `2`) or add a minimal `usage()` path and one harness case if exit `2` is still desired for misuse.

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

### FINDING_6: `POSITIONAL_KIND=none` not gated before Step 0b issue fetch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When Step 0-pre succeeds with `POSITIONAL_KIND=none`, Step 0b still flows into `gh issue view "$ISSUE_NUMBER"` and `design-route.sh --issue` with an empty issue number. `/design` with only flags and no positional runs session-setup in 0a, then fails or misbehaves at issue fetch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document orchestrator halt on none or add an explicit guard in a follow-up.
  - From cursor-specialist-edge-cases-output.txt: Add an explicit none branch before fetch/route that matches legacy empty-invocation handling.

### FINDING_7: Step 0-pre consumer does not validate boolean KV tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: The Step 0-pre consumer assigns `*_REQUESTED` KVs verbatim with no `true`/`false` validation. A corrupted line like `HARD_REQUESTED=yes` could propagate wrong tier or router flags into downstream init, disagreeing with Step 0b tier prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Validate hard_requested/partition_requested/etc. are exactly true or false after ingest, or re-use parser-only output without ad-hoc line mutation.
  - From dyn-kv-protocol-output.txt: In the `case` arms for the five `*_REQUESTED` keys, reject values other than `true`/`false` with the same abort path used for unexpected keys; keep `RUN_ID` / positional fields unrestricted aside from the parser’s newline guard.

### FINDING_8: Duplicate numeric-issue classification regex in parser
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `parse-design-argv.sh` applies `^[0-9]+$` twice in positional tail handling (lines 86–87 and 101–102). The two branches must stay in sync on future edits.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_9: Numeric issue positionals silently ignore trailing tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When the first positional is numeric, all tokens after the first digit run are ignored without error (e.g. `/design 3249 fix the parser` designs issue 3249 and drops trailing words). Either reject trailing tokens with `VALIDATION_ERROR` or document explicitly that extra words after an issue number are ignored.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_10: Duplicate `--run-id` silently last-wins
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Duplicate `--run-id` is allowed; last value wins (`--run-id a --run-id b` keeps only `b`) with no validation error, unlike duplicate `--hard` which is rejected.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_11: Harness gaps — `--medium`, exact KV count, `--run-id` newline
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-parse-design-argv.sh` retired `--simple` validation but not `--medium`; success-path cases assert individual KVs but never that stdout is exactly eight lines with no extras; `assert_safe_kv_value` newline smuggling is exercised for verbal positionals but not for `--run-id`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add --medium 3249 validation-error case mirroring --simple.
  - From cursor-specialist-testing-output.txt: Add a helper (e.g. `assert_success_kv_count 8`) on at least one representative success case so a partial or polluted stdout contract fails fast. Today coverage is spread across cases, so a regression that drops one KV line could slip through if only a subset of assertions run.
  - From cursor-specialist-testing-output.txt: Add `run_case --run-id $'bad\nid' 3249` expecting `VALIDATION_ERROR=newline-in-value` and exit `3`, mirroring the verbal newline case at lines 1033-1037 of the harness.

### FINDING_12: `flags.md` scope drift vs plan boundary
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan scoped `flags.md` to a one-line parser pointer without restating allowlist/positional rules; implementation also edits the Positional tail bullet with tail-ignore semantics. Behavior is documented in two places instead of one canonical pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep only the one-line pointer in flags.md and leave tail-ignore detail in parse-design-argv.md, or explicitly amend the plan/issue to allow the extra sentence.

### OOS_1: [OUT_OF_SCOPE] Empty `/design` invocation UX predates this refactor
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 0b fetches the issue even when `POSITIONAL_KIND=none`. `/design --hard` with no issue may fail at `gh issue view`; behavior unchanged by this branch and explicitly left out of refactor scope, but empty invocations remain fragile.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Positional tail doc omits numeric tail-ignore semantics
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: The top-level Positional tail bullet describes only “first non-flag token” and does not mention that a numeric issue consumes only the first positional token and ignores later tokens (documented in `references/flags.md` and `parse-design-argv.md`). Minor doc drift, not introduced by the KV consumer loop itself.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] No harness case for `=` inside `RUN_ID` / `POSITIONAL_VALUE`
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: Harness `kv_value` correctly uses `substr($0, length(k)+2)` (so `RUN_ID=a=b` would parse correctly), but there is no case covering `=` inside `RUN_ID` or `POSITIONAL_VALUE`. Protocol supports it; coverage gap only.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] `test-parse-design-argv` lacks explicit Makefile `contains` pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Some newer design harnesses (e.g. assessor family around lines 1250–1254) get explicit `Makefile` `contains` pins; `test-parse-design-argv` does not, though it is wired in `Makefile` and `test-harnesses-16`. Low risk given shard membership; optional consistency improvement only.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Numeric-first positional ignores later flags — operator footgun
- **Reviewer(s)**: dyn-template-expansion-output.txt
- **Severity**: nit
- **Concern**: `references/flags.md:29` and harness case `3249 extra words` document that a numeric first positional ignores trailing tokens (`3249 --hard` keeps `HARD_REQUESTED=false`). That matches the plan but is an operator footgun if users expect GNU-style “flags anywhere” parsing.
- **Suggested revisions (informational for voters; coder decides)**:
