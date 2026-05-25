### Add test-breadcrumb-monitor.sh + sibling test harnesses (issue #2790 item 4)

**Surfaced by**: /design plan review panel (Codex-Arch, Codex-Requirements, Codex-Innovation, Codex-Pragmatic)
**Phase**: design (for issue #2790)
**Vote tally**: 4-reviewer OOS consensus (OOS_1, OOS_2, OOS_5, OOS_9, OOS_10 in /design plan review of #2790)

Item 4 from issue #2790: add the dedicated test harnesses for the breadcrumb-propagation infrastructure that PR #2786 punted on. The core rollout (issue #2790 itself) lands with manual smoke coverage only.

**Scope**:
- Create `scripts/test-breadcrumb-monitor.sh` (with sibling `scripts/test-breadcrumb-monitor.md`) covering:
  - Stream growth latency
  - Partial-byte retention
  - Truncation/rotation
  - DONE-sentinel exit timing
  - Failure-tail surfacing with PEM redaction intact
  - Surfaced-sentinel pre-existing → silent exit (foreground-duplication guard)
  - Redactor non-zero exit fail-closed semantics
  - Path-scope rejection (symlink rejection, escape rejection)
  - Category enforcement (unknown-category drop)
- Create `scripts/test-breadcrumb-monitor-bash32.sh` (with sibling `.md`) running the same coverage under `/bin/bash` (macOS Bash 3.2) when present; no-op gracefully when `/bin/bash` is unavailable.
- Extend `scripts/test-redact-secrets.sh` with streaming-mode PEM cases:
  - Complete PEM block in a single line
  - PEM split across multiple `--state-file` calls
  - Stream tail starting mid-PEM
- Extend `scripts/test-larch-log.sh` asserting raw breadcrumb secrets never reach the committed copy under `larch-logs/<run-id>/breadcrumbs/`.
- Cover byte-identical stdout/stderr regression for `scripts/run-step5-review.sh` and `skills/implement/scripts/run-step2-dispatch.sh` after their `lib-quiet.sh` source-only adoption in #2790.

**Acceptance**:
- All listed test cases pass on CI (Linux + macOS).
- `make test-breadcrumb-monitor` and `make test-breadcrumb-monitor-bash32` targets exist and pass — depends on issue #2790 item 7 follow-up landing (Makefile/lint plumbing) for the Makefile targets themselves.
- `make test-redact-secrets` extends to cover the three new streaming PEM cases.
- `make test-larch-log` extends to cover the breadcrumb-redaction commit invariant.
- Byte-identical stdout/stderr regression tests pass for the two wrapper-adoption scripts.

**Why deferred from #2790**: per the user's "Core only + multiple follow-ups" scope decision at /design Step 1c (Q1), formal test harnesses are out-of-scope for the core slice. Manual smoke verification (`/implement` on a tiny issue end-to-end) substitutes in the #2790 PR.

### Add Makefile / docs/linting.md / agent-lint.toml plumbing for breadcrumb-monitor tests (issue #2790 item 7)

**Surfaced by**: /design plan review panel (Codex-Arch, Codex-Innovation, Cursor-dyn-deferred-ci-gap × 2)
**Phase**: design (for issue #2790)
**Vote tally**: 4-reviewer OOS consensus (OOS_3, OOS_4, OOS_6, OOS_11, OOS_12 in /design plan review of #2790)

Item 7 from issue #2790: register the new test harnesses + helper scripts in the project's Makefile, linting docs, and agent-lint allow-list so they are discoverable and CI-enforced.

**Scope**:
- `Makefile`:
  - Add `.PHONY` and recipe for `test-breadcrumb-monitor` invoking `bash scripts/test-breadcrumb-monitor.sh`.
  - Add `.PHONY` and recipe for `test-breadcrumb-monitor-bash32` invoking `bash scripts/test-breadcrumb-monitor-bash32.sh` (with a `/bin/bash` availability guard).
  - Register both targets in exactly one `test-harnesses-N` shard so they run in CI.
- `docs/linting.md`: add target rows for the two new harnesses with one-line descriptions.
- `agent-lint.toml`: add allow-list entries for:
  - `scripts/breadcrumb-monitor.{sh,md}`
  - `scripts/lib-redact-streaming.{sh,md}`
  - `scripts/test-breadcrumb-monitor.{sh,md}`
  - `scripts/test-breadcrumb-monitor-bash32.{sh,md}`
- Without these allow-list entries, `agent-lint` G004 would flag the new test files as "dead" (same pattern as `scripts/test-lib-quiet.sh:661-664`).

**Acceptance**:
- `make test-breadcrumb-monitor` and `make test-breadcrumb-monitor-bash32` defined and runnable.
- `agent-lint` passes on the new paths without warnings.
- `docs/linting.md` lists the new targets.
- CI test-harnesses-N shard execution includes the new harnesses.

**Why deferred from #2790**: depends on item 4 (test harnesses themselves) landing first. Per user "Core only + multiple follow-ups" scope decision.

### Document breadcrumb stream redaction in SECURITY.md and docs/run-logs.md (issue #2790 item 8)

**Surfaced by**: /design plan review panel (Codex-Arch, Codex-Innovation)
**Phase**: design (for issue #2790)
**Vote tally**: 2-reviewer OOS consensus (OOS_3, OOS_7 in /design plan review of #2790)

Item 8 from issue #2790: add durable security and operator documentation for the breadcrumb-propagation contract that PR #2786 + #2790 (core) implements.

**Scope**:
- `SECURITY.md`: add a "Breadcrumb stream redaction" section covering:
  - Raw breadcrumb stream files live in per-run tmpdirs ONLY (under `$DESIGN_TMPDIR/breadcrumbs/`, `$IMPLEMENT_TMPDIR/breadcrumbs/`, etc.) — never committed without redaction.
  - Monitor-side per-line redaction is fail-closed at the line level (drop-line on `lib-redact-streaming.sh` exit 1); the foreground monitor never surfaces partial PEM blocks.
  - Committed copies under `larch-logs/<run-id>/breadcrumbs/` are produced by `scripts/larch-log.sh write --batch breadcrumbs` which pipes each `*.ndjson` file through `redact-secrets.sh --streaming --state-file <tmp>`. Atomic mktemp+mv ensures partial files never appear in the destination.
  - Per-file skip + warn fail-closed semantics: a redactor non-zero exit on any one breadcrumb file removes that file from the commit, logs a `Warnings` entry to `execution-issues.md`, and continues with the rest of the batch.
  - Residual sensitive-content risk: redaction is pattern-based (PEM, common token shapes like `sk-*`, `ghp_`, JWTs); reviewer-supplied non-pattern secrets in breadcrumb text can still survive. Operators are responsible for not embedding non-pattern secrets in breadcrumb messages.
- `docs/run-logs.md`:
  - Document the new `breadcrumbs/` per-run directory under `larch-logs/<run-id>/`.
  - Document the `--streaming`-redacted commit contract (path resolution, filter pattern `*.ndjson` only, basename mapping, partial-success semantics).
  - Cross-reference SECURITY.md "Breadcrumb stream redaction" section.

**Acceptance**:
- `SECURITY.md` "Breadcrumb stream redaction" section landed with the 4 sub-points above.
- `docs/run-logs.md` documents the new `breadcrumbs/` directory + commit contract.
- Cross-references between the two files are accurate.

**Why deferred from #2790**: per user "Core only + multiple follow-ups" scope decision. Documentation lands after the implementation (#2790 core) is stable.

### Expand foreground-banner rewrite surface across .claude/skills/**/SKILL.md and .claude/rules/*.md (issue #2790 item 9)

**Surfaced by**: /design plan review panel (Codex-Arch, Codex-Innovation, Cursor-dyn-deferred-ci-gap)
**Phase**: design (for issue #2790)
**Vote tally**: 3-reviewer OOS consensus (OOS_4, OOS_8 in /design plan review of #2790)

Item 9 from issue #2790: exhaustively re-run the lint-foreground-markers static scan + a manual `rg "Foreground required"` audit across the development-only `.claude/skills/**/SKILL.md` and `.claude/rules/*.md` surfaces (which are NOT scanned by the current `list_md_files` set in `scripts/lint-foreground-markers.sh:64-82`).

**Scope**:
- Re-run `scripts/lint-foreground-markers.sh` static scan after #2790 (core) lands.
- Manual `rg "Foreground required"` + `rg "Background pair required"` across `.claude/skills/**/SKILL.md` and `.claude/rules/*.md`.
- For each stale foreground-banner / foreground-comment / Family-B invocation that still teaches the old pattern, rewrite to the new background+monitor contract per `BASH_AUTHORING.md §4`:
  - Banner above the fence: `**⚠ Background required — must be paired with breadcrumb-monitor.sh.**`
  - Per-anchor in-fence comment within 5 lines: `# Background pair required: see BASH_AUTHORING.md §4`
  - `run_in_background: true` documented in the same fence
  - Paired `breadcrumb-monitor.sh` invocation with `--stream`, `--done-sentinel`, `--status-file`, `--quiet-log`, `--surfaced-sentinel` arguments in the same fence or within 10 markdown lines after the closing fence
- Consider extending `scripts/lint-foreground-markers.sh` scan scope to include `.claude/skills/**/SKILL.md` and `.claude/rules/*.md` so future regressions are caught by CI.

**Acceptance**:
- `scripts/lint-foreground-markers.sh` static scan + manual `rg` audit returns ZERO stale foreground-banner patterns on `.claude/skills/**/SKILL.md` and `.claude/rules/*.md`.
- (Optional) `scripts/lint-foreground-markers.sh` `list_md_files` includes these paths going forward.

**Why deferred from #2790**: per user "Core only + multiple follow-ups" scope decision. The expanded rewrite surface is broader than the in-scope script + library changes in #2790 (core).
