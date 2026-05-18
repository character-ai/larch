# scripts/test-lint-bash32.sh - contract

Black-box regression harness for `scripts/lint-bash32.sh`. It invokes `bash scripts/lint-bash32.sh --root "$TMPROOT"` against isolated `mktemp -d` fixture roots, verifies a clean Bash 3.2-compatible script passes, verifies every forbidden construct class emits a violation, verifies full-line comments plus same-line `# lint-bash32: ok <reason>` suppressions are ignored, and verifies git-worktree enumeration scans untracked non-ignored shell scripts when `git` is on `PATH`.

The harness itself contains forbidden tokens only as fixture content. Those fixture lines carry the linter's own inline suppression before the harness strips the suppression into a generated bad fixture under `$TMPROOT`; this keeps full-repo `make lint-bash32` from flagging the regression harness while still testing unsuppressed violations.

Wiring expectations are Makefile target `test-lint-bash32`, one `test-harnesses-N` shard entry, and `agent-lint.toml` exclusions for the Makefile-only linter and harness. The primary contract is `scripts/lint-bash32.md`.
