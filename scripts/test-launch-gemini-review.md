# scripts/test-launch-gemini-review.sh — contract

Regression harness for `scripts/launch-gemini-review.sh`.

## Coverage

- Stubs `gemini` on PATH and verifies JSON `.response` is normalized to plain text.
- Verifies a requested 1800-second timeout is clamped to 600 seconds in the raw launcher metadata.
- Verifies reviewer Gemini argv includes `--approval-mode yolo` and `--admin-policy <path-ending-in-gemini-reviewer-policy.toml>` and that the policy path exists and is non-empty.
- Verifies `{"error": ...}` fails closed with empty output, diagnostic text, and non-zero `.done`.
- Verifies the fail-closed process exit code matches `.done` on Gemini `.error`, empty `.response`, and missing-`jq` paths.
- Verifies forced missing-`jq` fails closed with `MISSING_JQ` and exit code 127 in `.done`.
- Verifies unsafe `--output` values containing `=` and LF exit 2 before creating normalized or raw output artifacts.
- Verifies the prompt-hardening preamble is prepended to the caller-provided prompt (Gemini stub records `-p` argument; assertions pin the first line `HARD CONSTRAINTS — your role is read-only review.` and pin the original prompt body's last line at the tail).
- Verifies the snapshot guard detects and reverts a new-untracked-file mutation injected via `LARCH_TEST_GEMINI_PRE_OUTPUT_HOOK`. Assertions: process exit code `1`, `.done` sidecar `1`, `$OUTPUT` cleared (matches `fail_closed` contract), `SNAPSHOT_GUARD_TRIGGERED:` diag with the mutated path named, file removed post-test, and `git status --porcelain` clean.
- Verifies the snapshot guard detects and reverts a tracked-mutation case (one tracked file overwritten + one tracked file deleted) injected via the same hook. Same assertion shape as the new-untracked case, with both file contents restored to their HEAD values.
- Verifies the snapshot guard detects an index-only mutation (reviewer runs `git add` against an already-worktree-modified tracked file) and clears the reviewer-added index entries via `git reset HEAD --`. The on-disk content hash is unchanged in this scenario; the I-record schema in `capture_snapshot` is the load-bearing detection signal.
- Verifies the launcher's non-git fail-open posture: when invoked outside any git working tree, the snapshot guard skips with the documented diagnostic and the run still succeeds end-to-end.
- Verifies model-rejection paths via `scripts/lib-gemini-model-resolver.sh` (the launcher now sources this helper instead of inlining the env-precedence chain). Blank `LARCH_GEMINI_MODEL`, whitespace-only, and control-byte values are rejected via `fail_closed` before `gemini` runs. Each rejection asserts the canonical sidecar set — non-zero process exit code matching `.done`, empty `$OUTPUT`, and a `.diag` diagnostic anchored on the resolver's stderr message identifying the rejected source. The empty-model rejection case additionally asserts the dirty-tree sidecar (`STATUS=unknown`, `MODE=baseline`, `REASON=fail-closed-no-agent-ran`) so the no-agent-ran sidecar contract is exercised on at least one resolver-rejection path symmetric with the `MISSING_JQ` case.
- Verifies `LARCH_TIMING_TASK_KIND=--prompt` from the environment falls back
  silently to `gemini-review` in the timing TSV, while the CLI
  `--timing-task-kind` path still rejects empty and flag-shaped values with
  exit 2.
- Verifies the dirty-tree sidecar contract introduced for Cursor/Codex by #1437 and extended to Gemini by #1487. Two assertion blocks: the success path asserts `${OUTPUT}.dirty-tree` exists with `STATUS=` (any detector value) and `MODE=baseline`; the `LARCH_TEST_FORCE_MISSING_JQ=true` short-circuit asserts `STATUS=unknown`, `MODE=baseline`, and `REASON=fail-closed-no-agent-ran`. The EXIT-trap reason `REASON=exit-trap-no-agent-ran` is documented in the launcher's sibling `.md` but is not exercised by an explicit assertion here — it would require provoking a SIGINT/SIGTERM mid-launcher, which is beyond the scope of a stubbed harness.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure. Gated on `LARCH_RUN_TEST_LAUNCH_GEMINI_REVIEW=1` so the harness does not fire by default outside `make test-launch-gemini-review` / CI.

## Edit-in-sync

Update with `scripts/launch-gemini-review.sh`, `scripts/launch-gemini-review.md`, `scripts/gemini-reviewer-policy.toml`, `scripts/run-external-agent.sh`, `scripts/lib-validate-meta-path.sh`, `scripts/lib-gemini-model-resolver.sh`, `scripts/lib-gemini-model-resolver.md`, and the Gemini CLI JSON schema. Any change to the snapshot-guard semantics (record schema, restore branches, exit codes, env-var validation, EXIT-trap cleanup, prompt preamble text) requires updating the four guard/preamble test cases above in lockstep. Any change to the resolver's rejection rules (blank/whitespace/cntrl gates, env precedence) requires updating both this harness's resolver-rejection cases and the parallel cases in `scripts/test-check-reviewers.sh` and `skills/implement/scripts/test-gemini-implementer.sh`.
