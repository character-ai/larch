Merging overlapping reviewer findings by behavioral risk and severity, then producing the structured aggregator output.
### FINDING_1: Duplicate tier launch/probe logic in `run_codex_tier` / `run_claude_tier`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_codex_tier` and `run_claude_tier` duplicate launch, probe, empty-raw, and `had_probe_miss` handling; timeout or cap-hit fixes in one tier may not propagate to the other, yielding wrong `SCOUT_STATUS` or missed waterfall fallthrough.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared `run_scout_tier` helper; keep only argv assembly in tier-specific wrappers

### FINDING_2: Duplicated fenced-JSON probe vs post-winner validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `tier_raw_is_scout_json` duplicates fenced-JSON probing used again after a winner is chosen; per-tier probe and post-winner validation can diverge so the waterfall accepts raw one path would reject (or the reverse).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor `scout_raw_to_parse_input` (or similar) shared by tier probe and post-winner validation

### FINDING_3: No-winner status branching needs a documented truth table
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: No-winner status is a nested branch on `had_probe_miss` and `last_launch_rc`; future status-token changes can mis-classify probe exhaustion vs launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `finalize_waterfall_no_winner` helper with documented truth table matching harness cases

### FINDING_4: Codex tier passes unused context flags on prompt-file path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Codex tier passes `--diff-file` / `--scope-files` / `--plan-file` alongside `--prompt-file`; if launch-review does not embed diff on the prompt-file path, these flags are no-ops and mislead maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Omit unused context flags for scout Codex launches or document as intentional no-ops

### FINDING_5: Duplicated path canonicalization across coupled launchers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Path canonicalization helpers are duplicated between `launch-claude-subprocess.sh` and `scout-dynamic-archetypes.sh`; validation rules can drift between scout staging and Claude read-tools root checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract `scripts/lib-path-canonical.sh` on next touch of either file

### FINDING_6: Default 180s scout timeout may be too low for read-tools on large staged diffs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Default 180s timeout is unchanged for read-tools scout on large staged diffs (~900KB after larch-logs trim); Read loops can time out and yield zero dynamic reviewers (similar to the old 256KB embed gate) without signaling timeout distinctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Raise or scale scout timeout for `--read-tools`; optional distinct read-timeout status
  - From cursor-specialist-edge-cases-output.txt: Raise default or tier timeout when staged WARN fires; document operator override

### FINDING_7: Scout waterfall omits Cursor tier despite acceptance text
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Scout waterfall is Codex→Claude only while feature acceptance lists Codex→Cursor→Claude; Cursor-present hosts skip Cursor for dynamic archetypes though panel reviewers may still use Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add Cursor tier when launch-review supports it or update acceptance text

### FINDING_8: Mixed probe-miss plus final launcher failure emits launcher status, not `empty`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: When multiple tiers have probe misses and the final tier’s launcher fails (e.g. Codex non-JSON then Claude exit 7), `SCOUT_STATUS` is `claude-failed` (launcher status) rather than `empty`, diverging from issue acceptance and operator expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align plan with tests or emit `empty` when any probe miss occurred
  - From cursor-specialist-edge-cases-output.txt: Clarify in CHANGELOG/issue close; behavior is already in scout-dynamic-archetypes.md and harness

### FINDING_9: `SESSION_ENV_PATH` exported after max-archetypes zero early exit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SESSION_ENV_PATH` is exported after the max-archetypes 0 exit path; that path may break timing-ledger `SESSION_ENV_PATH` fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Export `SESSION_ENV_PATH` before the zero-cap early exit

### FINDING_10: No harness coverage for `launch-review.sh --codex-add-dir`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `--codex-add-dir` on `launch-review.sh` has no harness coverage per launcher-argv-test-coverage; breaking directory validation could ship undetected and give scout Codex wrong sandbox roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add accept/reject cases in `test-launch-review.sh` pinning argv and exact `--codex-add-dir is not a directory` stderr

### FINDING_11: Scout harness Claude stub largely ignores `--read-tools`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Most scout cases use a Claude stub that ignores `--read-tools`; only waterfall-fallthrough asserts the flag. Removing `--read-tools` from `run_claude_tier` could leave production scouts without tool reads while `make lint` stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Log Claude launcher argv in `run_case` paths and grep for `--read-tools` and `--read-tools-add-dir` on every tier launch

### FINDING_12: Waterfall tests do not assert Codex paths use staged-context
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Waterfall tests do not assert Codex `--diff-file` / `--scope-files` point at staged-context paths; Codex could read caller paths outside `SESSION_ROOT`, disagreeing with staging/prompt and failing out-of-workspace reads silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep `SCOUT_CODEX_ARGV_LOG` for `staged-context/diff.txt` and assert caller-only paths are absent

### FINDING_13: Staged bulk size is warn-only; docs and implementation disagree; disk/DoS and silent zero-dynamic risk
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Staged files over 1 MiB only WARN while `SECURITY.md` implies a hard cap; unbounded `cp` staging after input gate removal can fill disk; large post-trim diffs (2–5 MB) still stage fully, tiers may timeout or cap-hit, and scout can fail-open to zero dynamic reviewers with only WARN and no `parse-failed` diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Hard-fail staging over `MAX_STAGED_BYTES` or add stubbed tier-failure harness expecting non-ok scout status
  - From cursor-specialist-security-output.txt: Restore fail-closed staged byte cap or enforce budget before `cp`
  - From cursor-specialist-security-output.txt: Update `SECURITY.md` or reintroduce mechanical cap matching docs
  - From cursor-specialist-edge-cases-output.txt: Surface staged-size failures into execution issues when archetype count is 0, or add a separate configurable hard staging cap distinct from the removed 256 KB embed gate

### FINDING_14: Presence-flag test greps any `true` in argv log
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Presence flag test greps any `true` in argv log; broken `--codex-present false` forwarding could still match unrelated `true` tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `--codex-present true` and `--cursor-present true` literally in `SCOUT_SCOUT_ARGV_LOG`

### FINDING_15: `--codex-add-dir` lacks symlink rejection and session-root containment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `--codex-add-dir` lacks symlink rejection and session-root containment unlike `--read-tools-add-dir`; a caller could pass a symlink to `~/.ssh` and Codex read-only sandbox could still read secrets via `--add-dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use `canonical_existing_dir` + `under_root` against `CANON_OUTPUT_DIR`/`SESSION_ROOT`; restrict flag to scout staged-context

### FINDING_16: Scout read-only boundary relies on plan mode, not mechanical sandbox
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Scout read-only boundary relies on `--permission-mode plan` plus `allowedTools Read` without mechanical sandbox; a future Claude CLI widening plan-mode permissions could allow writes despite the allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pin CLI version in verification rule; add regression harness for disallowed tools

### FINDING_17: Multi-tier probe exhaustion emits `empty` without diagnostic telemetry
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-tier probe exhaustion emits `SCOUT_STATUS=empty` with no fail reason; large-diff runs get zero dynamic reviewers (including security archetypes) with no `parse-failed` diagnostic when Codex was present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add WARN/telemetry for probe exhaustion when `--codex-present true`

### FINDING_18: `commit-log.txt` includes larch-logs paths diff omits
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `diff.txt` and `file-list.txt` exclude larch-logs but `commit-log.txt` does not; review bundle can show add run-log commits while diff omits larch-logs paths, confusing scope for log-aware tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Filter git log with the same pathspec or document asymmetry and extend the gather-branch-context harness

### FINDING_19: Codex description-mode tier omits staged description file args
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Codex description-mode tier does not pass explicit description file args to `launch-review.sh`; Codex may systematically probe-miss in `/design` plan-review and waterfall always falls back to Claude with no distinct signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pass staged `--description-file` to launch-review or emit WARN on Codex probe-miss + Claude win

### FINDING_20: Plan text vs shipped scout argv (SESSION_ROOT / tool scope)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan text still specifies `SESSION_ROOT` add-dir and Read/Grep/Glob; code uses staged-context and Read-only. Operators auditing only the issue plan block may believe scout grants Grep/Glob over full `SESSION_ROOT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Align issue plan bullets with shipped behavior or add an explicit plan-delta note in scout-dynamic-archetypes.md

### FINDING_21: Plan file list omits `launch-review.sh` Codex sandbox changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `launch-review.sh --codex-add-dir` was required for scout but omitted from the plan file list; plan-only reviews may miss Codex sandbox surface when scoping blast radius.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add launch-review.sh and launch-review.md to the plan inventory on the tracking issue

### FINDING_22: Harness checks CMD_JSON substrings only for read-only verification
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Harness checks `CMD_JSON` substrings only while plan acceptance cites verify-external-tool-invocations mechanical verification; host or CLI changes could weaken read-only enforcement while tests still pass on `.meta` shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add stub or documented manual denial check for a forbidden tool per verify-external-tool-invocations

### FINDING_23: [OUT_OF_SCOPE] Branch mixes #3192 /design SIMPLE-default with scout work
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Branch includes #3192 `/design` SIMPLE-default work outside the scout plan; scout plan-fidelity reviews must filter unrelated tier-flag diffs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Track scout and tier changes separately or split PRs for review clarity
