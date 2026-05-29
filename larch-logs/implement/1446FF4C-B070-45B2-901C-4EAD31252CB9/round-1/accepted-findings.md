### FINDING_1: dispatch-panel does not assert scout presence-flag forwarding
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan FINDING_5 requires asserting that `--codex-present` and `--cursor-present` reach `scout-dynamic-archetypes.sh` from `dispatch-panel`. `dispatch-panel.sh` forwards the flags, but `test-dispatch-panel.sh` only stubs the Claude launcher and never logs or checks scout argv. A regression that drops scout_args presence forwarding would not be caught by panel harnesses while design harnesses still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a scout argv-logging stub override and grep for --codex-present/--cursor-present in a dynamic panel case with --codex-available true.
  - From cursor-specialist-testing-output.txt: Add a scout wrapper or argv log in the harness and grep for --codex-present/--cursor-present on a dynamic dispatch case.
  - From cursor-specialist-plan-fidelity-output.txt: Add a scout-boundary stub or argv log and grep for --codex-present / --cursor-present in a dynamic-panel test.


### FINDING_10: Codex launcher failure mislabeled `claude-failed`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Codex tier launcher failures set `last_scout_status=claude-failed`. Logs and dispatch diagnostics attribute a Codex launch failure to `claude-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use codex-failed or launcher-failed for the Codex tier path.


### FINDING_12: harness does not assert `--read-tools` on Claude scout tier
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Scout integration does not assert `--read-tools` on the Claude launcher path. Removing `--read-tools` from `scout-dynamic-archetypes.sh` would pass harnesses but break large-diff Read-by-path in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Log argv in desc_launch or stub and assert --read-tools on waterfall Claude-tier runs.


### FINDING_13: `--read-tools` grants Read/Glob over full `SESSION_ROOT`, not staged-context only
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-staged-context-injection-output.txt
- **Severity**: important
- **Concern**: `--read-tools` grants `claude --print` read access to the entire `SESSION_ROOT` (`--add-dir "$SESSION_ROOT"`), not just `staged-context/`. For `/review`, `SESSION_ROOT` is `$REVIEW_TMPDIR`; for implement Step 5, `$IMPLEMENT_TMPDIR/round-N`. The scout prompt names staged paths, but the subprocess may use Read, Grep, and Glob over sibling files (diff artifacts, gather env, prior `.raw` outputs, prompts). A malicious or compromised staged diff/plan can instruct the model to search and read those siblings — lateral read not possible under embed-only scout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Narrow --add-dir to staged-context (or scout-only subdir); keep prompt on stdin
  - From dyn-staged-context-injection-output.txt: Narrow `--add-dir` to `"$SESSION_ROOT/staged-context"` (and, if the prompt must live outside that tree, stage or symlink-copy the prompt under the same tree). Drop **Glob** (and optionally **Grep**) from the scout allowlist if only path-directed **Read** is required.


### FINDING_14: plan-review scout `SESSION_ROOT` exposes `source-env.sh` via same `--add-dir`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Plan-review scout `SESSION_ROOT` equals `DESIGN_TMPDIR` where `source-env.sh` also lives. Session env exports become readable by Codex/Claude scout via Glob/Read alongside staged plan/description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Isolate scout artifacts and restrict --add-dir to staged-context; keep source-env outside added roots


### FINDING_15: multi-round review reuses `REVIEW_TMPDIR`; prior round artifacts readable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-round review reuses `REVIEW_TMPDIR` across rounds. Round N scout can Read round N-1 reviewer outputs and execution-issues under the same `--add-dir` root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Per-round scout dir or staged-context-only --add-dir; prune prior artifacts before scout


### FINDING_16: bulk context size gate removed; unbounded staged copies
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-staged-context-injection-output.txt
- **Severity**: important
- **Concern**: Bulk context file size gate removed with full copy staging (256 KB embed cap gone from validation; only path/symlink checks remain). Very large or hostile diffs cause large staged copies, long external reads, timeouts, cost, and larger prompt-injection surface when loaded via Read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add soft cap with warn or bounded staging policy
  - From dyn-staged-context-injection-output.txt: Add a separate high cap for staged bulk files (distinct from the removed embed gate), or enforce a post-stage size check before launching tiers; keep untrusted-data framing in the prompt and consider whether **Glob**/**Grep** are necessary for the scout task.


### FINDING_17: agentic Read/Glob increases exfiltration into scout JSON `prompt_body`
- **Reviewer(s)**: dyn-staged-context-injection-output.txt
- **Severity**: important
- **Concern**: Shifting untrusted diff/plan bytes from escaped prompt embedding to agentic Read increases the chance a scout follows in-file instructions and reflects discovered content into `{"archetypes":[…]}` `prompt_body` fields. Downstream `dispatch-panel` treats scout JSON as untrusted, but exfiltrated material can still flow into dynamic reviewer prompts as quoted context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-staged-context-injection-output.txt: Treat this as defense-in-depth: minimize `SESSION_ROOT` exposure (first bullet), avoid **Grep**/**Glob** for scout, and optionally scan/redact scout `prompt_body`/`rationale` before synthesis (existing secret redactors are on other paths, not this subprocess stdout).


### FINDING_18: harness should lock scout to Codex→Claude only (no `--tool cursor`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan requires proving no Cursor scout tier when `--cursor-present true`; harness only sets the flag. A future change could add a Cursor `launch-review` path without failing CI, violating the documented Codex→Claude-only scout contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Record LAUNCH_REVIEW_SH argv in the Codex stub and assert --tool codex only, never --tool cursor.
  - From cursor-specialist-plan-fidelity-output.txt: Use a launch-review stub that records argv and fails on --tool cursor, with --cursor-present true in a waterfall case.


### FINDING_2: dead `print_escaped_file` after staged Read-tool prompts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `print_escaped_file` is dead code after staged Read-tool prompts; only `escape_prompt_data` is used for inline description text. It confuses maintainers into thinking bulk files might still be embedded via `print_escaped_file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove print_escaped_file; keep escape_prompt_data for inline --description-text only.


### FINDING_22: Codex tier omits staged `--description-file` for launch-review
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Codex tier does not pass staged `--description-file` to `launch-review`; only inline `--description-text` is forwarded. `/design` plan review with `--description-file` and `--codex-present true`: Codex may return valid JSON without reading staged description; archetypes omit description context until Claude fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pass staged description into launch-review (new flag or bounded cat) or require Claude tier when description-file mode is used.


### FINDING_4: context staging before `--max-archetypes 0` early exit
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Context staging runs before `--max-archetypes 0` early exit. Calls with max archetypes 0 still copy large diff/description files unnecessarily.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move max-archetypes zero check before staging, or skip stage_context_file when cap is zero.


### FINDING_8: multi-tier terminal `SCOUT_STATUS=empty` hides final-tier launcher failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Multi-tier terminal branch prefers `SCOUT_STATUS=empty` whenever `had_probe_miss` is set, even if the last tier failed to launch or timed out. Example: Codex returns exit-0 non-JSON prose then Claude times out or fails to launch — status is `empty` not `timeout`/`claude-failed`, hiding the real failure in scout telemetry and dispatch-panel diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: When the last attempted tier fails launch, emit last_scout_status (timeout/claude-failed) instead of empty, or add a composite status/diag field.
  - From cursor-specialist-testing-output.txt: Add Codex launch-fail + Claude launch-fail stubs and assert terminal claude-failed/timeout without SCOUT_FAIL_REASON.
  - From cursor-specialist-edge-cases-output.txt: Only emit empty on all-tier probe exhaustion; if the final tier has last_launch_rc != 0 or empty raw, emit that tier's launcher status. Add a harness for Codex prose + Claude launch failure.


### FINDING_9: `--read-tools` read-only guarantee relies on weak permission mode + substring harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-staged-context-injection-output.txt
- **Severity**: important
- **Concern**: `--read-tools` uses `--permission-mode default`; read-only behavior relies mainly on `--allowedTools`. On hosts where default allows writes, scout subprocess might not be as read-only as `SECURITY.md` implies, especially combined with broad `--add-dir` on `SESSION_ROOT`. Harness only asserts `CMD_JSON` substrings, not mechanical denial of Edit/Write/Bash or verified read-only mode — contrary to verify-external-tool-invocations expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Verify and pin an explicit read-only permission mode; extend harness beyond CMD_JSON substring checks.
  - From cursor-specialist-security-output.txt: Use verified read-only permission-mode and a denial smoke test
  - From dyn-staged-context-injection-output.txt: After `claude --help`/probe on supported hosts, switch to a verified read-only `--permission-mode` (document the exact value beside the invocation), and add a harness or manual check that a disallowed tool is mechanically denied—not just omitted from argv.


