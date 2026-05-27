## Plan

When `/implement` stalls (`STALL_TRACKING=true`), a new **recovery gate** runs as the first sub-step inside Step 18 (before the existing teardown). It classifies the stall, files (or prints) a sanitized larch bug issue, attempts a class-dependent recovery — which itself completes any remaining `/implement` steps inline (impl + commit + review + checks + ship-pr) using the existing wrapper scripts — and on success atomically clears `STALL_TRACKING` so the existing teardown takes the `[DONE]` branch. On exhausted recovery (or `unrecoverable` from the start), a terminal-failure comment is posted (or printed) and the existing teardown takes the `[STALLED]` branch unchanged.

### Files

#### NEW: `skills/implement/scripts/stall-recovery-report.sh`

Single helper with seven subcommands (closed enum):

- `classify` — flags: `--implement-tmpdir <path>` (required), `--in-memory-stall-tracking <true|false>` (when `ship-pr-state.sh` is absent), `--bail-reason <token>` (in-memory path), `--failure-detail-log <path>` (rejects non-absolute, non-canonical, non-regular, symlink, or outside-tmpdir paths), `--attempts-file <path>`. Reads `ship-pr-state.sh` when present, else falls back to in-memory + `session-env.sh`. Emits via `lib-quiet.sh` `emit_kv`: `FAILURE_CLASS` (closed enum: `transient-infra`, `test-failure`, `lint-failure`, `dispatch-failure`, `contract-failure`, `same-cause-repeat`, `unrecoverable`), `FAILURE_SIGNATURE`, `RESUME_HINT` (closed enum: `step2-impl`, `step5-review`, `step8-shippr`, `none`; `step3-checks` and `step6-checks` are NOT resume hints — they classify as `contract-failure`), `STALL_STEP`, `PHASE`, `STALL_TRACKING`, `BAIL_REASON`. Sets `FAILURE_CLASS=same-cause-repeat` (override) when the current signature matches the most recent `attempt.<N>.signature` in `--attempts-file`.
- `init-attempts` — atomically (mktemp + mv -f) creates the attempts file with `version=1`, `created_utc=<ISO8601>`, `attempt_count=0`. Idempotent.
- `record-attempt` — atomic append of `attempt.<N>.{class,signature,resume_hint,outcome,utc}` keys; increments `attempt_count`.
- `is-larch-dev-clone` — emits `LARCH_DEV_CLONE=true|false` from the canonical marker (working-tree root contains `skills/implement/SKILL.md`); shares predicate with `scripts/check-stale-plugin.sh` via a new `scripts/lib-larch-dev-clone.sh`.
- `bug-body` — composes public bug-report markdown from the `bug-body` surface allowlist (committed at `skills/implement/scripts/stall-recovery-report-allowlists.tsv`). Runs `scripts/redact-secrets.sh` as a mechanical backstop. Includes `<!-- larch-stall:signature=<hash> -->` for byte-exact dedup. Emits `BODY_FILE` + `DRY_RUN_DECISION`.
- `bug-comment` — composes the terminal-failure comment from a SEPARATE `bug-comment` surface allowlist (includes retry-attempt table from `--attempts-file`).
- `issue-input-file` — composes the generic batch-mode input file for `/larch:issue`: first line is `### [Bug] /implement stall: <class> at <step>` followed by the body content.
- `lint` (harness-only) — asserts the surface-key set in `stall-recovery-report-allowlists.tsv` equals the surface-key set emitted by the helper code AND the surface-key set documented in `stall-recovery-report.md`. Doc-vs-code-vs-tests parity.

Exit codes: `0` success; `1` argv error; `2` missing required input (e.g. `--implement-tmpdir`); `3` reserved EXCLUSIVELY for malformed/unparseable present `ship-pr-state.sh`. Missing `ship-pr-state.sh` is NOT exit 3 — it is a normal classified outcome (often `unrecoverable` with a bounded `BAIL_REASON`).

#### NEW: `skills/implement/scripts/stall-recovery-report.md`

Contract sibling. Sections: subcommand contracts, the four surface allowlists (verbatim TSV), classifier evidence sources per `FAILURE_CLASS`, the closed `RESUME_HINT` enum, the per-class retry caps table (single normative source — `references/stall-recovery.md` points here and never duplicates), exit-code table, `--failure-detail-log` validation rules, dry-run semantics, SECURITY.md cross-references.

Per-class retry caps (single normative source):
- `transient-infra`: 4 attempts, 5-second delay between (`sleep-seconds.sh 5`).
- `test-failure`: 8 attempts, no delay.
- `lint-failure`: 8 attempts, no delay.
- `dispatch-failure`: 3 attempts, no delay.
- `same-cause-repeat`: 1 attempt with alternate strategy (re-read `larch:plan`, restart failed step from scratch).
- `contract-failure`: 0 attempts.
- `unrecoverable`: 0 attempts.

#### NEW: `skills/implement/references/stall-recovery.md`

Orchestrator-facing reference loaded by SKILL.md Step 18a. Procedure (every sub-step ends with an explicit "continue to ..." anti-halt directive):

1. **Resolve `STALL_TRACKING`** from three layers (in-memory → `ship-pr-state.sh` → `session-env.sh`); gate fires if any layer reports `true`.
2. **`init-attempts`** BEFORE classify / issue filing / dispatch.
3. **Classify** with `--implement-tmpdir`, `--in-memory-stall-tracking`, `--bail-reason`, `--failure-detail-log` (only when validated via `realpath` + symlink check + tmpdir-prefix check), `--attempts-file`.
4. **First-detection issue filing** (only when `attempt_count==0`): call `is-larch-dev-clone`, then `bug-body`, then evaluate `DRY_RUN_DECISION`. Dry-run writes `$IMPLEMENT_TMPDIR/stall-recovery-bug-body.dry-run.md` and skips the call. Larch clone: invoke `/larch:issue --input-file <generated>` via Skill; capture stdout-only; persist `ISSUE_URL`/`ISSUE_NUMBER` to `$IMPLEMENT_TMPDIR/stall-recovery-issue.env`. Consumer repo: print body verbatim under `## Action required — file larch bug`.
5. **Dispatch on `RESUME_HINT`** (closed enum, exhaustive):
   - `step2-impl`: main Claude reads `$IMPLEMENT_TMPDIR/plan.txt`, performs the impl edits inline via Edit/Write, runs the relevant-checks helper, commits as Step 4 does, then continues into `step5-review` and `step8-shippr` automatically — recovery drives the run to merge inline.
   - `step5-review`: invoke `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round <next>` using the Family B background+monitor pair (six `LARCH_*` env vars allocated under `$IMPLEMENT_TMPDIR/breadcrumbs/`, `run_in_background: true` on the script call, foreground `breadcrumb-monitor.sh` paired). On success, continue into `step8-shippr`.
   - `step8-shippr`: re-invoke `${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh` with the same Step 8+ background+monitor envelope. Exit 6 → `transient-infra` retry; Exit 4 → `same-cause-repeat` retry once if signature matches, else terminal.
   - `none` (paired with `FAILURE_CLASS=contract-failure` or `unrecoverable`): no dispatch — proceed directly to terminal-failure handling.
6. **Retry loop**: increment via `record-attempt`, re-classify to detect `same-cause-repeat`, enforce per-class caps read from `stall-recovery-report.md`.
7. **Success path** (atomic ordering):
   1. Compose new `ship-pr-state.sh` content with `STALL_TRACKING=false` and `STALL_STEP=` cleared.
   2. Write to `ship-pr-state.sh.tmp.<rand>` in the same directory.
   3. Re-read temp via `read-session-env-key.sh --key STALL_TRACKING`; assert `false`.
   4. `mv -f` temp over `ship-pr-state.sh`.
   5. Re-read destination via `read-session-env-key.sh --key STALL_TRACKING`; assert `false`.
   6. Only then clear the in-memory orchestrator variable.
   7. Any of (3), (5), or `mv -f` failure → leave both layers `true` and route to terminal failure.
8. **Terminal-failure path**: `bug-comment` (with `--attempts-file`); evaluate `DRY_RUN_DECISION`; `gh issue comment` (larch clone) or chat-print (consumer); leave `STALL_TRACKING=true`.
9. **Continue to teardown**: regardless of success or terminal failure, continue to the existing Step 18b teardown body (token refresh, `restore-finalize-state.sh`, `implement-finalize.sh teardown`). Teardown branches on the on-disk `STALL_TRACKING` value unchanged.

**Safety constraints**: NEVER spawn Agent-tool subagents for code-writing during recovery (main Claude only); NEVER mutate `finalize-state.sh` (NEVER #13); NEVER call `ScheduleWakeup` (NEVER #9); ALWAYS use the Family B background+monitor pair when invoking `run-step5-review.sh` / `ship-pr.sh` (NEVER #16); NEVER recurse into Step 18 from inside the recovery loop.

#### NEW: `skills/implement/scripts/stall-recovery-report-allowlists.tsv`

Machine-readable allowlist table (TSV, four surfaces × N fields). Format: `surface\tfield_key\tsource\ttransform`. Loaded by the helper at startup and by the harness for parity diffing. Contract sibling (`stall-recovery-report.md`) documents the same table verbatim; the `lint` subcommand asserts no drift.

Surfaces and their fields:
- `bug-body`: `failing_step` (`STALL_STEP` → enum), `failing_phase` (`PHASE` → enum), `failure_class` (`FAILURE_CLASS`), `exit_code` (integer), `signature_hash` (hex), `inferred_root_cause` (classifier enum → fixed prose templates only), `suggested_mitigation` (classifier enum → fixed prose templates).
- `bug-comment`: all `bug-body` fields plus `attempt_count`, `attempt_table` (allowlisted attempt fields only — class/signature/outcome/utc, NOT raw stdout), `final_class`, `final_signature`.
- `issue-input-file`: synthesized title `[Bug] /implement stall: <class> at <step>` + body content.
- `chat-print` (consumer-repo path): same fields as `bug-body`.

#### NEW: `scripts/lib-larch-dev-clone.sh`

Shared shell library exposing `is_larch_dev_clone()`. Sourced by `scripts/check-stale-plugin.sh` (factored from its inline check) and by `skills/implement/scripts/stall-recovery-report.sh`. ~15 lines.

#### NEW: `skills/implement/scripts/test-stall-recovery-report.sh`

Hermetic offline harness wired via `scripts/harness-timer.sh`. 21 test cases:

1. `classify` returns `transient-infra` for gh rate-limit pattern + network-touching `PHASE`.
2. `classify` returns `test-failure` for pytest/jest markers.
3. `classify` returns `lint-failure` for lint-fix exhaustion markers.
4. `classify` returns `dispatch-failure` for invalid step2-implement envelope.
5. `classify` returns `contract-failure` with `RESUME_HINT=none` for `STALL_STEP=3` and `STALL_STEP=6`.
6. `classify` returns `unrecoverable` with `RESUME_HINT=none` for `BAIL_REASON=adopted-issue-closed` / `tracking-init-failed`.
7. `classify` returns `same-cause-repeat` when the prior `attempt.<N>.signature` matches the new signature.
8. `classify` falls back gracefully when `ship-pr-state.sh` is absent — emits bounded `FAILURE_CLASS=unrecoverable`, NOT exit 3.
9. `classify` rejects `--failure-detail-log` outside tmpdir / symlink / relative / non-regular with distinct errors.
10. `init-attempts` is idempotent.
11. `record-attempt` is atomic.
12. `is-larch-dev-clone` returns correct value for both paths.
13. **Deny-list parity**: inject unique sentinels into every classifier input; assert no sentinel appears in any of the four public outputs.
14. **Allowlist-source parity** via `lint` subcommand: TSV ≡ code ≡ doc.
15. `bug-body` is byte-stable for identical inputs (deterministic signature).
16. `redact-secrets.sh` backstop is invoked (inject `ghp_...`-shaped token, assert redaction).
17. `bug-comment` includes the retry-attempt table.
18. `DRY_RUN_DECISION` propagates correctly AND a `gh` stub on PATH records all calls — assert no real `/larch:issue` invocation under `LARCH_STALL_RECOVERY_DRY_RUN=1`.
19. Atomic state-rewrite ordering: simulate crash between in-memory clear and disk write — assert disk flips before in-memory.
20. `issue-input-file` output starts with `### [Bug] /implement stall: <class> at <step>` (batch-parser-compatible).
21. Argv exit codes: bad argv → 1; missing required → 2; malformed `ship-pr-state.sh` → 3 (and only that case).

#### NEW: `skills/implement/scripts/test-stall-recovery-report.md`

Harness contract sibling — fixtures, expected outputs, hermeticity invariants, sentinel-injection patterns, doc-vs-code parity invariant.

#### UPDATED: `skills/implement/SKILL.md`

- **Step 18 restructure**: split into **Step 18a — Stall recovery gate** (new) and **Step 18b — Teardown** (existing body). Step 18a is the first sub-step inside Step 18 on every entry. When in-memory `STALL_TRACKING=false` AND no disk fallback signal, prints `⏩ 18a: stall recovery — no stall detected` and proceeds. When any layer reports `true`, loads `references/stall-recovery.md` via MANDATORY directive and executes. Prelude uses existing `$IMPLEMENT_TMPDIR/session-env.sh` rehydration pattern (no `current-implement-env-$PPID.sh`).
- The 24 existing `STALL_TRACKING=true` bail-path bullets are not modified — they continue to "skip to Step 18 cleanup", and Step 18a runs unconditionally at Step 18 entry.
- Step 18b teardown prose: Branch A `[STALLED]` fires only when Step 18a left `STALL_TRACKING=true` on disk; Branch B `[DONE]` fires when Step 18a cleared it. No teardown-script logic change.
- Title-prefix lifecycle: updated to mention Step 18a.
- New NEVER bullet: NEVER spawn Agent-tool subagents for code-writing work during stall recovery (Round 1 decision 1).
- Anti-halt prose for Step 18a enumerates loop-continuation directives and "no recursion into Step 18".

#### UPDATED: `Makefile`

- Add `test-stall-recovery-report` to `.PHONY`.
- Define recipe with `scripts/harness-timer.sh`.
- Add target to exactly one `test-harnesses-N` shard line.

#### UPDATED: `SECURITY.md`

New "Stall recovery sanitization" section enumerating the four output surfaces, the allowlist invariant, the `redact-secrets.sh` backstop, `--failure-detail-log` validation rules, and links to `lint`/deny-list parity harness cases. Notes residual risk: inference templates are static maintainer-controlled prose; a malicious template patch is reviewer-visible by construction.

#### UPDATED: `scripts/check-stale-plugin.sh`

Replace inline marker check with `source scripts/lib-larch-dev-clone.sh` + `is_larch_dev_clone`. Behaviorally identical.

### Approach

Recovery gate is orchestrator-side prose (Step 18a in `SKILL.md` + `references/stall-recovery.md`) backed by a deterministic helper that owns classification, sanitization, dev-clone detection. The helper exposes a closed-enum API; the reference handles dispatch, retry control, atomic state writes, and downstream-step continuation. The 17 plan-review findings drove these decisions:

- Single intercept at Step 18a; all existing skip-to-Step-18 bullets pass through unchanged.
- `/larch:issue --input-file` batch shape with `### [Bug] /implement stall: <class> at <step>` heading.
- `step5-review` recovery uses the `run-step5-review.sh` wrapper with Family B background+monitor pair.
- `step3-checks` and `step6-checks` classify as `contract-failure` with `RESUME_HINT=none` — preserve the existing Step 8 Exit 4 invariant (no main-agent edits on `PHASE=checks` exhaustion).
- `classify --attempts-file` + `record-attempt` for durable prior-signature interface.
- Existing `session-env.sh` rehydration; no new `current-implement-env` file.
- Harness wired via `test-harnesses-N` shard + `.PHONY` + `scripts/harness-timer.sh`.
- Three-layer `STALL_TRACKING` resolution (in-memory → `ship-pr-state.sh` → `session-env.sh`).
- One control-flow model: recovery drives the run forward to merge inline; teardown is single-pass.
- Dry-run lives in the reference; harness asserts no real `/larch:issue` call.
- Four surface allowlists in a committed TSV; `lint` subcommand for doc-vs-code parity; deny-list sentinel test.
- `--failure-detail-log` strict validation (absolute, canonical, regular, non-symlink, under tmpdir, ≤ 64 KB).
- Missing `ship-pr-state.sh` → bounded `unrecoverable`, NOT exit 3.
- Atomic ordering: write temp → read-back-verify → `mv -f` → read-disk-verify → clear in-memory.
- Single caps authority: `stall-recovery-report.md` only; reference points to it.
- Closed `RESUME_HINT` enum: `step2-impl`, `step5-review`, `step8-shippr`, `none`.

### Edge cases

- Missing `ship-pr-state.sh` on early bailouts → bounded `unrecoverable`.
- Consumer repo with no `gh` auth → consumer chat-print path; larch-clone `gh` failure logged as Tool Failures.
- Stall inside recovery gate → no recursion into Step 18; per-class cap exhaustion triggers terminal failure.
- `/larch:issue` semantic-dedup hits an existing open larch issue → existing issue receives the terminal-failure comment.
- `forked_target=true` → Step 18a uses the consumer-repo print path.
- Operator re-invokes `/implement` mid-recovery → existing `parent-issue.md` sentinel prevents double-adoption.
- Crash between in-memory clear and disk write → impossible by construction (atomic ordering inverts this case).
- `--failure-detail-log` outside tmpdir → validator rejects; classify continues without the optional log.

### Failure modes

1. **Allowlist regression leaks consumer IP into a public larch issue.** Earliest signal: harness case 13 (deny-list sentinel parity) fails. Mitigation: three independent backstops — the deny-list parity test, the doc-vs-code parity (`lint` subcommand), and `scripts/redact-secrets.sh`. SECURITY.md documents residual risk.
2. **Classifier misroutes a stall** (e.g., `unrecoverable` auth as `transient-infra`, wasted retries). Earliest signal: retry-attempt table in terminal comment shows 4 identical-signature attempts. Mitigation: string-pattern classifier with documented evidence sources per class; harness cases 1-8 cover each branch; `same-cause-repeat` catches the degenerate loop after attempt 2.
3. **Recovery success but disk `STALL_TRACKING=true`** → Step 18b takes Branch A `[STALLED]` despite a real merge. Earliest signal: harness case 19 (atomic-ordering simulation) regresses. Mitigation: four-step write → read-back → `mv -f` → read-disk-verify makes wrong order impossible by construction; any read-back failure routes to terminal failure instead of clearing the flag.

### Testing strategy

- Hermetic offline harness at `skills/implement/scripts/test-stall-recovery-report.sh` (21 cases enumerated above). Wired via `scripts/harness-timer.sh` and assigned to exactly one `test-harnesses-N` shard line.
- `make lint` (`scripts/relevant-checks.sh`) asserts `Makefile` has `test-stall-recovery-report` in `.PHONY` and on at least one shard line.
- Manual integration verification: `LARCH_STALL_RECOVERY_DRY_RUN=1` induces a synthetic stall and observes Step 18a prose + chat output. The `gh` stub in case 18 proves no real issue is filed.
- No new external-reviewer test fixtures.
- Final validation: `bash scripts/relevant-checks.sh` (equivalent to `make lint`).

## Acceptance

The implementation is complete when ALL of the following are demonstrably true:

1. **Step 18 restructure** — `skills/implement/SKILL.md` contains Step 18a (recovery gate) and Step 18b (existing teardown body) under a single Step 18 umbrella. Step 18a unconditionally runs at Step 18 entry, with the existing `STALL_TRACKING=true` bail-path bullets unchanged. `make lint` passes.
2. **`stall-recovery-report.sh`** ships with all 8 subcommands (`classify`, `init-attempts`, `record-attempt`, `is-larch-dev-clone`, `bug-body`, `bug-comment`, `issue-input-file`, `lint`), each emitting the documented KV contract, with the closed-enum behavior described above.
3. **`stall-recovery-report.md`** ships as the single normative source for per-class retry caps (exact values listed above), with the four surface allowlists documented verbatim from the TSV.
4. **`stall-recovery-report-allowlists.tsv`** ships with the four-surface schema; `lint` subcommand asserts code/doc/TSV parity.
5. **`references/stall-recovery.md`** ships with the 9-sub-step procedure (resolve → init-attempts → classify → first-detection issue filing → dispatch → retry loop → atomic success path → terminal failure → continue to teardown) and the enumerated safety constraints.
6. **`lib-larch-dev-clone.sh`** ships and is sourced by both `scripts/check-stale-plugin.sh` and `skills/implement/scripts/stall-recovery-report.sh`. `check-stale-plugin.sh` behavior is byte-equivalent.
7. **`test-stall-recovery-report.sh`** harness ships with all 21 cases passing; `make test-stall-recovery-report` succeeds; the harness is on a `test-harnesses-N` shard.
8. **SECURITY.md** has a "Stall recovery sanitization" section enumerating the four surfaces and the allowlist invariant.
9. **Makefile** has `test-stall-recovery-report` in `.PHONY`, with a recipe using `scripts/harness-timer.sh`, on exactly one shard line.
10. **Manual integration test**: with a stubbed `gh` recording all invocations and `LARCH_STALL_RECOVERY_DRY_RUN=1`, a synthetic stall fires Step 18a, prints the Action-required block (consumer-repo print path), and does NOT invoke `gh` for issue creation. With dry-run off and `LARCH_DEV_CLONE=true`, a synthetic stall files exactly one larch issue via `/larch:issue --input-file` with title `[Bug] /implement stall: <class> at <step>`.
11. **`bash scripts/relevant-checks.sh`** passes.

diff_lines: 1450
