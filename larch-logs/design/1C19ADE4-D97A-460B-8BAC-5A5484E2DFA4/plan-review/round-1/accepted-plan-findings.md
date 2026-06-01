### FINDING_1: agent-lint dead-script exclusions missing for new step-telemetry-mark harness (and possibly runtime helper)
- **Reviewer(s)**: Cursor-Arch, Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-ledger-semantics, Cursor-dyn-harness-wiring, Codex-dyn-harness-wiring
- **Severity**: important
- **Concern**: The plan adds a Makefile-only test harness (`scripts/test-step-telemetry-mark.sh` and sibling `.md`) and a runtime helper invoked from `skills/implement/SKILL.md`, but does not update `agent-lint.toml` dead-script/orphan exclusions. agent-lint G004 does not follow Makefile target edges or (per some reviewers) SKILL.md fence invocations, so `make lint` / `bash scripts/relevant-checks.sh` can fail with false dead-script/orphan flags on the new files even when Makefile wiring and runtime call sites are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml` `exclude =` with the same Makefile-only comment pattern as `scripts/test-lib-quiet.sh` (runtime `scripts/step-telemetry-mark.sh` should stay off exclude — it is referenced from `skills/implement/SKILL.md`)
  - From Codex-Edge: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml`'s exclude list with the same Makefile-only comment pattern as `scripts/test-implement-timing-rehydration.sh`/`.md`
  - From Cursor-Innovation: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to the `agent-lint.toml` dead-script exclude list with a Makefile-only comment, mirroring `test-implement-timing-rehydration`
  - From Codex-Pragmatic: Add scripts/test-step-telemetry-mark.sh and scripts/test-step-telemetry-mark.md to the same Makefile-only allowlist near test-implement-timing-rehydration
  - From Codex-Requirements: Add `scripts/test-step-telemetry-mark.sh` and `scripts/test-step-telemetry-mark.md` to `agent-lint.toml` with the adjacent Makefile-only harness exclusions, or add another agent-lint-recognized structural reference
  - From Codex-dyn-ledger-semantics: Add agent-lint.toml to the UPDATED files and exclude scripts/step-telemetry-mark.sh, scripts/step-telemetry-mark.md, scripts/test-step-telemetry-mark.sh, and scripts/test-step-telemetry-mark.md with the same Makefile-only/runtime-fence rationale.
  - From Cursor-dyn-harness-wiring: Add `scripts/step-telemetry-mark.sh`, `scripts/step-telemetry-mark.md`, `scripts/test-step-telemetry-mark.sh`, and `scripts/test-step-telemetry-mark.md` to the dead-script exclude list with the same Makefile-only / G004 comment pattern as `scripts/rebase-checkpoint-probe.sh` and `scripts/test-implement-timing-rehydration.sh`
  - From Codex-dyn-harness-wiring: Add explicit agent-lint.toml exclusions for scripts/step-telemetry-mark.sh, scripts/step-telemetry-mark.md, scripts/test-step-telemetry-mark.sh, and scripts/test-step-telemetry-mark.md, or add an agent-lint-recognized structural reference


### FINDING_2: Runtime helper executable-bit contract not enforced despite direct SKILL.md invocation
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-ledger-semantics, Cursor-dyn-harness-wiring
- **Severity**: important
- **Concern**: Converted `skills/implement/SKILL.md` call sites execute `scripts/step-telemetry-mark.sh` directly and swallow failures with `|| true`. If the helper lands without the executable bit (e.g. mode 0644), runtime calls return 126 and telemetry marks for Steps 5/16/17/18 are silently dropped. A harness that only invokes the script via `bash` can pass while production call sites fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a minimal harness assertion like [[ -x "$HELPER" ]] and run the happy path through "$HELPER" rather than bash "$HELPER"; ensure the new file is committed executable
  - From Codex-Pragmatic: Make the helper executable in git and have test-step-telemetry-mark invoke it directly by path, not only via bash
  - From Codex-dyn-ledger-semantics: Require scripts/step-telemetry-mark.sh to be committed executable and add a [ -x "$HELPER" ] assertion to scripts/test-step-telemetry-mark.sh, or switch the SKILL.md call sites to bash "$HELPER" consistently.
  - From Cursor-dyn-harness-wiring: In scripts/test-step-telemetry-mark.sh, assert [ -x "$SCRIPT" ] and invoke "$SCRIPT" directly in the happy-path test before checking both ledger rows


### FINDING_3: Omitted `--implement-tmpdir` can abort under `set -u` despite never-fatal contract
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: The plan promises exit 0 when `--implement-tmpdir` is omitted, but the proposed helper may reference `$IMPLEMENT_TMPDIR` before initialization under `set -uo pipefail`, causing a non-zero abort on the first `"$IMPLEMENT_TMPDIR/session-env.sh"` expansion. That contradicts the never-fatal contract and planned edge-case behavior. The harness only covers bad tmpdir paths, not the omitted-flag case, so CI would not catch it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Initialize IMPLEMENT_TMPDIR="" and LABEL="" before the arg loop; use "${IMPLEMENT_TMPDIR:-}" only where needed; add a harness case that invokes the helper with no --implement-tmpdir and asserts exit 0

