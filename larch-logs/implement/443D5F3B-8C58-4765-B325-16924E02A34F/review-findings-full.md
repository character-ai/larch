### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/dispatch-with-waterfall.sh:148` passes `--competition-notice "$COMPETITION_NOTICE"` to `launch-review.sh`, but `scripts/launch-review.sh:119` defines `--competition-notice` as a valueless flag. When `/review` has `competition-notice.md`, `skills/review/scripts/review-core.sh:189` forwards it, every external phase launch sees the notice path as an unknown flag, fails Phase 1 and Phase 2, and the whole panel falls through to Claude. Fix by forwarding only `--competition-notice` to `launch-review.sh` and add a waterfall test covering `--competition-notice`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/dispatch-with-waterfall.sh:148` passes `--competition-notice "$COMPETITION_NOTICE"` to `launch-review.sh`, but `scripts/launch-review.sh:119` defines `--competition-notice` as a valueless flag. When `/review` has `competition-notice.md`, `skills/review/scripts/review-core.sh:189` forwards it, every external phase launch sees the notice path as an unknown flag, fails Phase 1 and Phase 2, and the whole panel falls through to Claude. Fix by forwarding only `--competition-notice` to `launch-review.sh` and add a waterfall test covering `--competition-notice`.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: scripts/dispatch-with-waterfall.sh:61-68

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No validation of NDJSON slot schema beyond jq parse Malformed slot rows yield silent Phase-3 Claude fallback or null paths Add post-parse validation and fail fast on invalid rows
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `security` `skills/design/SKILL.md:647` evals raw KV output from `dispatch-with-waterfall.sh`, whose `ALL_OUTPUT_FILES` values are unquoted paths emitted by `scripts/dispatch-with-waterfall.sh:300-307`. A session path derived from `XDG_CACHE_HOME`/`HOME` with shell metacharacters, e.g. `XDG_CACHE_HOME='/tmp/larch;touch /tmp/pwn'`, can be reflected into `ALL_OUTPUT_FILES=...` and executed by the `eval`. Replace the eval with the line-by-line allowlist parser pattern already used in `skills/review/scripts/dispatch-panel.sh:117-126`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` `skills/design/SKILL.md:647` evals raw KV output from `dispatch-with-waterfall.sh`, whose `ALL_OUTPUT_FILES` values are unquoted paths emitted by `scripts/dispatch-with-waterfall.sh:300-307`. A session path derived from `XDG_CACHE_HOME`/`HOME` with shell metacharacters, e.g. `XDG_CACHE_HOME='/tmp/larch;touch /tmp/pwn'`, can be reflected into `ALL_OUTPUT_FILES=...` and executed by the `eval`. Replace the eval with the line-by-line allowlist parser pattern already used in `skills/review/scripts/dispatch-panel.sh:117-126`.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## correctness: skills/research/SKILL.md:132-143

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 0 incomplete migration from probe/health to presence Orchestrator is told to use fallback_probe_failed and sanitize *_PROBE_ERROR though new branches emit fallback_presence_failed and probes are no longer parsed Update the status enum text to include fallback_presence_failed and drop or retarget the *_PROBE_ERROR sanitization paragraph to keys that still exist
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: skills/review/scripts/dispatch-panel.sh:111-112 and scripts/dispatch-with-waterfall.sh:43-44,148-152

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] --competition-notice is wired with a file path into launch-review.sh which only accepts a boolean flag; the next token is treated as an unknown flag and external launches fail. Any run with --competition-notice-file set causes launch-review to exit 2 for affected slots; panel dispatch breaks instead of applying the notice. Pass only the boolean --competition-notice to launch-review.sh; inject file contents via prompt rendering or a dedicated --competition-notice-file contract on the launcher/renderer.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: skills/shared/dialectic-protocol.md:144

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Scoping bullets corrupted (invalid SESSION_ENV_PATH concatenation; empty ``). Operators lose the no-session-env-mutation rule or misinterpret required collector behavior. Restore two explicit, syntactically valid bullets: forbid mutating session env; describe collect-agent-results invocation without placeholder corruption.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## correctness: skills/shared/dialectic-protocol.md:248

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Wrong `${SESSION_ENV_PATH}session-env` interpolation in collector note. Misidentifies which file must not be updated during dialectic collection. Use the canonical session-env path variable/name consistent with session-setup/write-session-env.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## risk-integration: docs/linting.md (test-dispatch-with-waterfall row)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Doc claims stubbed launch-review/launch-claude-review; harness uses real scripts. False confidence about test isolation. Describe PATH-stubbed codex/cursor/claude with real launcher scripts.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## risk-integration: docs/linting.md:182

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Doc claims PATH-stubbed launch-claude-subprocess and broader harness coverage than implemented. Maintainers skip needed tests for --agent-file and context forwarding. Update docs or extend test-launch-claude-review.sh to match claims.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## risk-integration: scripts/dispatch-code-voters.md:1-48

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contract documents obsolete parallel launch wait-for-reviewers and wrong DISPATCH_OK meaning Mis-implemented fixes or wrong operational runbooks based on stale contract Rewrite dispatch-code-voters.md to match dispatch-code-voters.sh waterfall behavior
- **Suggested revision**: Address the concern above.

### FINDING_29: panel [code-review/accepted]

## risk-integration: scripts/dispatch-plan-voters.md:5-16

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contract documents obsolete run-external-agent and wait path Same as above for plan-review voter ops Rewrite dispatch-plan-voters.md to match dispatch-plan-voters.sh
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## risk-integration: scripts/test-dispatch-code-voters.sh;scripts/test-dispatch-plan-voters.sh (post-change)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Removed argv-shape and multi-case integration coverage from stub-plugin harnesses. Wrapper flag regressions in real launches slip past CI. Reintroduce focused invocation-log assertions or a smaller stub-plugin slice.
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## risk-integration: scripts/test-dispatch-with-waterfall.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No all-phase1-OK baseline case. Phase gating bugs when all externals succeed could go unnoticed. Add one success-only case with FALLBACK_COUNT=0 and expected tools.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## risk-integration: skills/review/scripts/dispatch-panel.sh (vs main make_prompt)

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] COMPETITION_NOTICE_FILE is no longer concatenated into any prompt; only the static template from render-specialist-prompt --competition-notice applies. Operators lose custom competition instructions that previously reached at least the Claude scratch path on main. Re-add explicit safe inclusion of the file into prompts for each tool tier that must see it, or drop the CLI and document the behavior change.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## risk-integration: skills/review/scripts/test-dispatch-panel.sh (post-change)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness dropped hard panel, both-down, stdout cap, and sentinel assertions. 12-slot wiring or waterfall stdout regressions may reach main undetected. Add hard and both-absent cases; restore bounded stdout check if still required.
- **Suggested revision**: Address the concern above.

### FINDING_38: panel [code-review/accepted]

## risk-integration: skills/shared/dialectic-protocol.md:139

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Prose says not present/responding while presence is PATH-static. Reintroduces deprecated health semantics for judge gating. Align wording with presence-only model; drop responding language.
- **Suggested revision**: Address the concern above.

