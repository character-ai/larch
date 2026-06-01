### FINDING_1: Anti-halt line 29 still gates final-summary on render helper exit 0
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-driver-exit-contract-output.txt
- **Severity**: important
- **Concern**: The global anti-halt reminder at `skills/design/SKILL.md:29` still requires verbatim `final-summary.md` emission to be gated on `render-final-summary.sh` (or similar helper) exit 0 and helper printing to chat. Step 5c item 5, the Final summary block, and the post-`design-publish.sh` contract gate on a non-empty `FINAL_SUMMARY_PATH` after the driver handoff (`_publish_rc` 0 or 1), including when plan-block-write fails (driver exit 1 with non-empty `final-summary.md`). An orchestrator following line 29 can skip required verbatim top-chat summary emit or wait on a stale helper-exit-0 signal that no longer matches the driver contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update line 29 to reference design-publish.sh handoff and non-empty FINAL_SUMMARY_PATH gate; remove helper-exit-0 language.
  - From cursor-specialist-correctness-output.txt: Align line 29 with post-driver non-empty-file gate; pin against stale helper-exit-0 prose in test-render-cost-line-callsites.sh or test-design-structure.sh.
  - From cursor-specialist-edge-cases-output.txt: Align line 29 with post-design-publish.sh non-empty FINAL_SUMMARY_PATH gate; remove helper-exit-0 wording.
  - From cursor-specialist-plan-fidelity-output.txt: Align line 29 with Step 5c post-driver non-empty-file gate; drop helper-exit-0 for Step 5c; optional structure-test negative grep
  - From dyn-driver-exit-contract-output.txt: Replace line 29’s helper-exit-0 gate with the same post-driver, non-empty-file language used in Step 5c item 5 / Final summary block; optionally add a negative grep in `scripts/test-render-cost-line-callsites.sh` so the stale phrase cannot return.

### FINDING_2: Silent `[DESIGNED]` rename failure after successful publish
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-prune-invariants-output.txt
- **Severity**: latent
- **Concern**: In `skills/design/scripts/design-publish.sh` (rename block ~287–297), when `SESSION_ID` is set and `PUBLISH_OK=true`, `[DESIGNED]` rename uses if-success-only parsing with no `else` on `tracking-issue-write.sh` non-zero exit and no WARN when `RENAMED=` is omitted (unlike `design-init-runparams.sh`). A failed rename is dropped: no `RENAMED=` in `.design-publish-result.env`, no `WARN=` replay, no `append-tool-failure.sh` entry, while the driver can still exit 0—plan and logs may publish but the issue title never gets `[DESIGNED]`, and Step 6 cleanup may still run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror init-runparams rename WARN branches; add rename-failure harness case.
  - From dyn-prune-invariants-output.txt: Mirror that pattern: on non-zero rename rc, `add_warn` with a `[DESIGNED]`-specific message (and optionally append via `append-tool-failure.sh`); on success with no `RENAMED=` line, warn like 0b. Add a harness case where the rename stub exits non-zero with `PUBLISH_OK=true` and assert `WARN=` in the result env.

### FINDING_3: Step 6 cites wrong Step 5c item for skip-cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:1387` references Step 5c item 5 for skip-cleanup on plan-write failure; item 5 is summary emit and item 7 is the failure branch. The misnumbered cross-reference may confuse the orchestrator about which Step 5c item owns skip-cleanup semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reference item 7 or neutral plan-block-write failure wording.

### FINDING_4: Harness missing plan-required RENDER_LOG / render-env assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-render-env-binding-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-publish.sh` does not assert the three render invocations (failed-plan-write, pre-publish, post-publish) receive `ISSUE_NUMBER`, `SESSION_ID`, and `DESIGN_TMPDIR` via `RENDER_LOG` greps, including on the plan-block-write failure path. Structure pins only require export strings exist somewhere in `design-publish.sh`, not before the first render call—regressions that drop or reorder exports could pass CI while breaking the plan contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add RENDER_LOG greps for three render calls and UPSERT_STUB_RC failure continues test.
  - From cursor-specialist-testing-output.txt: Grep RENDER_LOG after failure/happy/empty-SID cases for all three outcomes and exported env vars per plan.
  - From cursor-specialist-plan-fidelity-output.txt: Add upsert-failure stub case and RENDER_LOG assertions for failed-plan-write pre/post and empty SESSION_ID post-publish env
  - From dyn-render-env-binding-output.txt: After the plan-block-write failure run, `grep` `RENDER_LOG` for a line containing `failed-plan-write` with `ISSUE_NUMBER=42`, `SESSION_ID=sid-1`, and `DESIGN_TMPDIR` set to the canonical tmpdir; add analogous assertions on the happy path for pre-publish and post-publish lines, and on the empty-`SESSION_ID` case for the expected render count and env values.

### FINDING_5: Harness missing upsert/marker non-blocking failure cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-design-publish.sh` omits planned cases for upsert failure and marker-write failure non-blocking paths. A mistaken exit or early return on upsert/marker failure could ship undetected until production `/design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub cases for UPSERT_STATUS=failed/nonzero rc and marker non-zero; assert exit 0 and continued tail per contract.
  - From cursor-specialist-plan-fidelity-output.txt: Add upsert-failure stub case and RENDER_LOG assertions for failed-plan-write pre/post and empty SESSION_ID post-publish env

### FINDING_6: Step 5b banner still describes inline Step 5c helpers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:1258` Step 5b continuation banner still lists inline Step 5c sub-steps instead of `design-publish.sh`, so operators may expect per-helper Step 5c calls instead of one foreground driver call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update banner to design-publish.sh publish tail.
  - From cursor-specialist-plan-fidelity-output.txt: Update prose to compose/validate/redact + design-publish.sh

### OOS_1: [OUT_OF_SCOPE] Branch bundles unrelated upgrade-larch / logs / version work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Branch bundles upgrade-larch, larch-logs, and version bumps with Step 5c extraction, widening PR scope beyond the feature; process suggestion, not a driver logic defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split or note in PR summary (process, not code fix).

### OOS_2: [OUT_OF_SCOPE] Unrelated `scripts/lib-net.sh` executable bit change
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Unrelated executable bit change in a relevant-checks fix commit with no identified impact on the design-publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Leave as-is or isolate in separate commit.

### FINDING_7: `relevant-checks.sh` skips render-callsite test on SKILL-only edits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh:101-104` does not run `test-render-cost-line-callsites` when only `skills/design/SKILL.md` changes. Future edits to post-driver final-summary emit prose can pass local relevant-checks and fail only in full harness shard 15.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Append test-render-cost-line-callsites for design SKILL.md and design-publish sibling edits.

### FINDING_8: Harness ordering checks use source line numbers, not call-log sequence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-publish.sh:179-188` ordering checks use source line numbers, not stub call-log sequence. Reordering inside `design-publish.sh` could break plan→upsert→publish while line-order greps still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert call-log order on happy path across PLAN_BLOCK_LOG, UPSERT_LOG, PUBLISH_LOG.

### OOS_3: [OUT_OF_SCOPE] Bundled upgrade-larch prune/stamp lacks automated tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bundled `upgrade-larch` prune/stamp changes lack automated tests; mid-upgrade cache deletion or wrong retention ranking is unguarded by CI on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a focused offline harness for prune retention/backfill (separate from design-publish work).

### FINDING_9: `FINAL_SUMMARY_PATH` emit not confined to `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The orchestrator verbatim-emits `FINAL_SUMMARY_PATH` from `.design-publish-result.env` without confining reads to `DESIGN_TMPDIR`. A same-UID attacker could race `FINAL_SUMMARY_PATH=/path/to/secret` before parse; Step 5c item 5 could cat and emit it to chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: After parse require FINAL_SUMMARY_PATH empty or canonically under DESIGN_TMPDIR; refuse symlink emit targets.

### FINDING_10: `SESSION_ID` validated only for newline/CR in driver
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh:20-25` validates `SESSION_ID` only for newline/CR, not log slug rules. Malformed `--session-id` could reach helpers before `design-log-publish` rejects it (defense-in-depth only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate non-empty SESSION_ID with larch_log_slug_is_valid (or shared helper) before publish/rename.

### OOS_4: [OUT_OF_SCOPE] `composed-plan.redacted.md` checked with `-s` only, not regular file
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `composed-plan.redacted.md` is checked with `-s` only, not as a regular file; a symlink in tmpdir could point plan-block-write at non-redacted content (broader hardening, pre-existed inline Step 5c).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require regular file or reject symlinks before plan-block-write (broader hardening).

### FINDING_11: Duplicate driver WARN replay in Step 5c parse block
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:1329-1344` replays driver warnings from `.design-publish-result.env` and `_publish_out` with undeduped `WARN) printf '%s\n' "WARN=$_value"`. `design-publish.sh` writes each warning twice (`phase_driver_write_result_env` and `emit_kv WARN`), so e.g. empty `SESSION_ID` emits the same WARN line twice. Step 0b uses `_route_warn_lines` dedup; Step 5c does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-warn-replay-output.txt: Port the `_route_warn_lines` dedup pattern into the Step 5c parse block, or only merge stdout `WARN` keys when the result-env file was absent/unread.

### FINDING_12: Driver WARN bodies may not reach top chat (operator visibility regression)
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: For SESSION_ID-empty and similar cases, the driver records warnings via `add_warn` (quiet-safe), but the orchestrator only replays them inside the Bash fence as `WARN=<markdown>`. Unlike Step 5c item 5 / Final summary block, there is no SKILL prose requiring verbatim top-chat replay of parsed WARN bodies; Step 5d “Final warning replay” covers external-reviewer warnings only—warnings may stay trapped as machine KV in Bash output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-warn-replay-output.txt: Add Step 5c post-parse prose mirroring item 5: emit each parsed WARN `_value` verbatim to top chat (optionally change the parse branch to `printf '%s\n' "$_value"` instead of prefixing `WARN=`), and/or list driver WARN replay in Step 5d.

### OOS_5: [OUT_OF_SCOPE] `add_warn` → result-env → `emit_kv WARN` chain is intentional
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: nit
- **Concern**: The `add_warn` → `phase_driver_write_result_env` → `emit_kv WARN` chain in `design-publish.sh` matches `design-init-runparams.sh` and the quiet-driver contract; no defect there.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Step 0b undeduped WARN replay predates this branch
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: nit
- **Concern**: Step 0b `design-init-runparams.sh` parsing uses the same undeduped `WARN=$_value` replay pattern; predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_13: Step 5c abort paths do not halt `/design`; items 6–7 lack rc/parse guards
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: important
- **Concern**: Abort branches in `skills/design/SKILL.md:1311-1351` use `exit 1` inside the Step 5c Bash fence (fails only the subshell). Items 5–7 sit outside the fence. Item 5 correctly limits emit to `_publish_rc` ∈ {0,1}, but items 6–7 branch on `PLAN_WRITE_OK` without repeating the rc guard or a “parse succeeded” precondition. After rc=2 or unexpected-rc abort, `PLAN_WRITE_OK` is never set while line 29’s anti-halt rule still pushes continuing—an agent may mis-run item 7 (unset treated as false) or proceed to Step 5d/6 after a configuration abort, unlike the validator Cancel branch that forbids remaining Step 5c work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-driver-exit-contract-output.txt: After each abort branch, add explicit halt prose: stop `/design`; do not run Step 5c items 5–7, Step 5d, or Step 6. Gate items 6–7 with “only when `_publish_rc` is 0 or 1 and `.design-publish-result.env` was parsed,” and tighten item 7 to “when `PLAN_WRITE_OK=false` after that parse,” not merely when the variable is empty.

### FINDING_14: Document quiet-driver file-first parse; pin fence must parse on rc=1
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: The rc ∈ {0,1} parse path is structurally sound (file-first parse authoritative when quiet mode leaves `_publish_out` empty), but maintainers need explicit documentation and a structure pin that the fence must not `exit` before parsing when `_publish_rc` is 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-driver-exit-contract-output.txt: No change required to the parse loop itself; document in `design-publish.md` / Step 5c prose that file-first parse is authoritative when quiet mode leaves `_publish_out` empty, and add a structure pin that the fence must not `exit` before parsing when `_publish_rc` is 1.

### OOS_7: [OUT_OF_SCOPE] Symlink refusal on `.design-publish-result.env` warns but does not abort
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: Symlink refusal on `.design-publish-result.env` prints a warning but does not abort (same pattern as Step 0b); pre-existing, not introduced by this extraction.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Step 0b clarify sub-step still describes inline log publish
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: Step 0b clarify sub-step 3 (~349) still describes inline `design-log-publish.sh` capture; stale prose outside Step 5c’s new driver surface.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: `design-publish.md` ordering section omits render phases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/design-publish.md:43-45` ordering invariants omit `render-final-summary` phases, so maintainers may misread publish ordering relative to the driver and plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Expand ordering section to match driver and plan

### OOS_9: [OUT_OF_SCOPE] upgrade-larch prune path reviewed—no defect found
- **Reviewer(s)**: dyn-prune-invariants-output.txt
- **Severity**: nit
- **Concern**: On this branch, `INSTALLED_VERSION` / `prune_cached_versions` / retention caps / `version_is_retained` for duplicate target—no correctness defect found in that path.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] Dropped architecture diagram banner is accepted UX
- **Reviewer(s)**: dyn-prune-invariants-output.txt
- **Severity**: nit
- **Concern**: Dropping the `> **🔶 /design 5c.5: larch:diagrams (architecture)**` banner while keeping orchestrator `⏩ 5c.5:` was flagged acceptable in design run logs; not a functional regression.
- **Suggested revisions (informational for voters; coder decides)**:
