# Review Round 3

- Mode: `diff`
- 11 accepted, 11 rejected (10 exonerated)

## Accepted Findings

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


### FINDING_4: Codex tier passes unused context flags on prompt-file path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Codex tier passes `--diff-file` / `--scope-files` / `--plan-file` alongside `--prompt-file`; if launch-review does not embed diff on the prompt-file path, these flags are no-ops and mislead maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Omit unused context flags for scout Codex launches or document as intentional no-ops


### FINDING_9: `SESSION_ENV_PATH` exported after max-archetypes zero early exit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SESSION_ENV_PATH` is exported after the max-archetypes 0 exit path; that path may break timing-ledger `SESSION_ENV_PATH` fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Export `SESSION_ENV_PATH` before the zero-cap early exit


