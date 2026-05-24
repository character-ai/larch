### FINDING_1: Step 18 double-emits the rendered summary block via `write-final-report.sh --print-stdout`
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements (UNANIMOUS, all 9 substantive reviewers)
- **Concern**: After deleting the Step 18 token/timing chat tail, `/implement` still calls `write-final-report.sh --print-stdout` at `skills/implement/SKILL.md:1868-1883` which prints the entire rendered summary (including the `- **Cost**:` bullet) a SECOND time, AFTER Step 17 already printed it via the same renderer. The plan's "single chat-side emission" invariant is silently violated because the Step 18 print is not in the edit list. This is the most-flagged finding in the panel.
- **Proposed resolution**: Add an `skills/implement/SKILL.md` Step 18 edit: change the Step 18 `write-final-report.sh` refresh call to omit `--print-stdout` (so it does the GitHub upsert + log refresh silently). Plus update `scripts/test-implement-structure.sh:242-249` which currently PINS Step 18 to keep `--print-stdout`. Without this fix, `make lint` will fail post-merge AND chat will show the cost line twice per /implement run.


### FINDING_10: `skills/design/references/discussion-rounds.md` still references `### Terminal cost line` for Step 1c/1d semantic-sprawl cancel
- **Reviewers**: Codex-Innovation, Codex-Requirements, Codex-Exit-Path-Auditor (MEDIUM, 3 reviewers)
- **Concern**: `skills/design/references/discussion-rounds.md:22-26` and `skills/design/SKILL.md:592-600` route Step 1c / Step 1d semantic-sprawl Cancel through the `### Terminal cost line` block. The plan does not list `discussion-rounds.md` as updated, so after the rename those Cancel paths reference a removed section.
- **Proposed resolution**: Add UPDATED: `skills/design/references/discussion-rounds.md` to the file list. Route semantic-sprawl Cancel through a new `--outcome cancelled-sprawl`. Update `render-run-summary.md` outcome enumeration. Cover in the design dispatcher harness.


### FINDING_11: `cancelled-plan-size-soft` outcome named in plan but Step 2b.5 soft prompt has no Cancel option
- **Reviewers**: Codex-Innovation, Codex-Exit-Path-Auditor (HIGH contradiction, 2 reviewers)
- **Concern**: The current Step 2b.5 soft branch (and partition-soft, semantic-soft) offers only Split / Continue. Approval-gates.md confirms this. The plan introduces `cancelled-plan-size-soft` as an outcome string, but there is NO Cancel option on the soft prompt today. Either the outcome is unreachable, or the plan introduces an unacknowledged UX change.
- **Proposed resolution**: Pick one: (a) Remove `cancelled-plan-size-soft` from the outcome enumeration; the soft branch's two options stay Split / Continue and a soft Cancel never happens. (b) Add an explicit "Cancel" option to the soft AskUserQuestion and update `approval-gates.md` + the soft prompt prose. The cost-line consolidation PR should NOT silently introduce a new UX option — pick (a) for scope safety unless the user explicitly wants the UX change.


### FINDING_12: Cost N/A vs $0.00 fallback — token-cost.sh returns $0.00 for all-zero inputs, masking failed accounting as a free run
- **Reviewers**: Codex-Edge (HIGH, 1 reviewer but technically sharp)
- **Concern**: When token-report.sh or jq fails, the plan says the renderer is invoked with zero token counts. But `render-run-summary.sh:130-164` shells to `token-cost.sh:225-236`, which returns `TOTAL_COST=0.00` for all-zero inputs. The plan-stated "Cost N/A" path actually emits `- **Cost**: 💰 ~$0.00` — failed accounting silently looks like a free run.
- **Proposed resolution**: Add an explicit cost-unavailable signal — either a `--cost-unavailable` flag to `render-run-summary.sh`, or have `render-final-summary.sh` detect zero-token failure and pass empty cost args (so the renderer's `tc=N/A` branch fires the literal `N/A` text). Add a test fixture asserting `- **Cost**: N/A` when token capture fails.


### FINDING_13: `--exec-issues` and `--warnings` counting algorithm unspecified
- **Reviewers**: Cursor-Edge (MEDIUM, 1 reviewer)
- **Concern**: The renderer requires integer counts for `--exec-issues` and `--warnings`. /implement's `write-final-report.sh:221-227` greps `execution-issues.ndjson`. /design's execution-issues.md is markdown (produced by `append-tool-failure.sh`). The plan says "compose bullet text from execution-issues.md" but does not specify how to extract integer counts.
- **Proposed resolution**: Define a deterministic counter — either grep `^### Tool Failures` and `^### Warnings` section headers, or count `^\*\*Step` entries, or `append-tool-failure.sh` emits a sidecar count file. Document the counting rule beside the `render-run-summary.sh` invocation in `render-final-summary.md`.


### FINDING_14: `test-design-structure.sh` anchor demands BOTH `render-final-summary.sh` AND `tracking-issue-summary.sh` strings — risks duplicate upsert prose
- **Reviewers**: Cursor-Edge, Cursor-Requirements, Cursor-Foreground-Compliance, Codex-Pragmatic, Codex-Foreground-Compliance (MEDIUM, 5 reviewers)
- **Concern**: The plan's `test-design-structure.sh` Item 1 says Step 5 must reference BOTH `render-final-summary.sh` AND `tracking-issue-summary.sh upsert-summary`. But the dispatcher helper is supposed to ENCAPSULATE the upsert call (keeping SKILL.md simple). Requiring both strings in SKILL.md prose either forces redundant text or fails the anchor if SKILL.md only invokes the helper.
- **Proposed resolution**: Pick one — either (a) the helper owns upsert internally, SKILL.md mentions only `render-final-summary.sh`, and the anchor asserts only that; or (b) the SKILL.md prose explicitly cross-references `tracking-issue-summary.sh upsert-summary` once in documentation form (no second invocation). Update both the plan's structure-test item AND the SKILL.md prose to match the chosen layering.


### FINDING_15: `scripts/token-report.md`, `scripts/token-cost.md`, `scripts/render-cost-line.md` still encode the OLD `--summary` dollar-line contract
- **Reviewers**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements (MEDIUM, 4 Codex reviewers)
- **Concern**: After the consolidation, these sibling docs still describe `token-report.sh --summary` as the dollar-primary surface, `render-cost-line.sh` as the /design caller, and the harness expectation as the old dollar-line. Operators following the docs may reintroduce duplicate emissions or misunderstand the new invariant. Also affects `docs/linting.md:272-279` and the matrix row for `test-token-report-summary-format`.
- **Proposed resolution**: Add UPDATED: `scripts/token-report.md`, `scripts/token-cost.md`, `scripts/render-cost-line.md`, `docs/linting.md` to the file list. Each gets a short prose update describing the new sole-source contract. Mark `render-cost-line.sh` explicitly as a deprecated standalone helper with no in-flow callers.


### FINDING_16: Already-planned cancel path (Step 0b sub-step 4(c)) unmapped — no `--outcome` assigned
- **Reviewers**: Codex-Exit-Path-Auditor (HIGH, 1 reviewer but covers a real exit path)
- **Concern**: `skills/design/SKILL.md:181-189` describes the already-planned router branch with a `(c) cancel` option that currently runs the Terminal cost line and exits 0. The plan's callsite list maps clarify, tier-gate Other, plan-size, happy, and failed-plan-write — but not the already-planned cancel. After replacing the shared block, this cancel path has no named `--outcome` or explicit exclusion.
- **Proposed resolution**: Add this exit to the plan's callsite enumeration with `--outcome cancelled-already-planned`. Document in `render-run-summary.md` outcome list. Cover in `test-render-final-summary.sh`.


### FINDING_18: Plan says "foreground banner remains" — but the current Terminal cost line block has NO canonical banner today
- **Reviewers**: Cursor-Foreground-Compliance, Codex-Foreground-Compliance (LOW but precise, 2 dynamic reviewers)
- **Concern**: `plan.txt:101` says the banner "remains" above the new fenced block. But `skills/design/SKILL.md:243-275` (the current Terminal cost line block) has only the `### Terminal cost line` heading and a "When" paragraph — no canonical `**⚠ Foreground required …**` banner exists today. The plan's "remains" misstates pre-PR layout.
- **Proposed resolution**: Reword the plan: "Add the canonical `**⚠ Foreground required — do NOT set \`run_in_background: true\`.**` banner immediately above the new opening ```bash fence" AND "add `# Foreground required: see BASH_AUTHORING.md §4` within five in-fence lines above each `render-final-summary.sh` or `tracking-issue-summary.sh` invocation-shaped anchor". Required only if FINDING_17 (a) is adopted; if (b), the banner/comment add is unnecessary but the prose still needs correction (delete the "remains" claim).


### FINDING_19: Split-path outcome name `cancelled-plan-size-split` is named but the plan also says "omit summary on Split-path"
- **Reviewers**: Cursor-Innovation, Cursor-Foreground-Compliance, Codex-Exit-Path-Auditor (MEDIUM, 3 reviewers)
- **Concern**: The plan introduces the outcome string `cancelled-plan-size-split` AND says Split-path deliberately does NOT emit a summary. Both cannot be normative. If Split-path skips render, the outcome string is dead test surface and creates documentation drift.
- **Proposed resolution**: Pick one — (a) Split-path skips render entirely (preserves `$DESIGN_TMPDIR` for operator re-run); remove `cancelled-plan-size-split` from the outcome enumeration. (b) Split-path renders a final summary; keep the outcome. The current `$DESIGN_TMPDIR`-preservation semantics favor (a). Apply consistently across plan/SKILL/tests.


### FINDING_2: Upsert-gate contradiction — helper says `ISSUE_NUMBER`-only; SKILL.md says `ISSUE_NUMBER + PLAN_WRITE_OK`
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-Exit-Path-Auditor (UNANIMOUS, 9 reviewers)
- **Concern**: The plan's NEW `render-final-summary.sh` step 6 says "upsert when `ISSUE_NUMBER` is non-empty and body is non-empty", but the UPDATED `skills/design/SKILL.md` item 4 says "non-happy paths skip upsert because the helper checks `ISSUE_NUMBER + PLAN_WRITE_OK`". These rules conflict on clarify-loop exit, plan-size cancel paths, and `failed-plan-write`. The Round 1 contract states "emit on ALL post-Step-0a exits" — if upsert is gated on `PLAN_WRITE_OK` (only assigned at Step 5c), non-happy exits would render to chat but silently skip the GitHub upsert, breaking the Round-1 promise.
- **Proposed resolution**: Adopt a single contract — `tracking-issue-summary.sh upsert-summary` runs after successful render whenever `ISSUE_NUMBER` is non-empty and the rendered body is non-empty, EXCEPT for explicit exclusions (Split-path, pre-Step-0a skips). Decouple publish/rename gating (`PLAN_WRITE_OK`) from upsert gating (issue-bound). Document the matrix in one place (helper sibling .md) and reference it from SKILL.md prose.


### FINDING_20: Byte-alignment assertion in plan narrows to "no trailing whitespace divergence" — should require FULL byte identity
- **Reviewers**: Cursor-Byte-Alignment-Parity (LOW, 1 reviewer)
- **Concern**: `plan.txt:88-89` qualifies the byte-alignment check as "no trailing whitespace divergence". Interior body drift (e.g., a sentinel newline mismatch, an in-body whitespace change) would not be caught if tests only strip trailing whitespace.
- **Proposed resolution**: Require full byte identity via `cmp -s file stdout-capture` (no whitespace pre-processing). Update both `scripts/test-render-run-summary.sh` and `skills/design/scripts/test-render-final-summary.sh` to use `cmp -s` as the canonical byte-identity assertion.

---

## Out-of-Scope observations


### FINDING_3: `token-report.sh --summary` becomes EMPTY after stripping `larch_emit_cost_line` — no replacement token emit
- **Reviewers**: Cursor-Edge, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements (HIGH, 6 reviewers)
- **Concern**: The current `token-report.sh --summary` success branch (lines 743-745) emits ONLY `larch_emit_cost_line`. Removing that without adding a replacement emit makes `--summary` produce empty stdout. The plan says "per-bucket Tokens line stays" but does not specify the new emit. Direct/ad-hoc operator invocations and test harnesses break.
- **Proposed resolution**: After removing the `larch_emit_cost_line` emit, add an explicit token-only summary emit on the success branch derived from the existing `$report` JSON — e.g. `Tokens: <N>k` plus per-vendor token counts (formatted in a stable shape suitable for assertions). Update both success and token-cost-failure branches consistently. Add a `Tests` item to update `scripts/test-token-report.sh` AND `scripts/test-token-report-summary-format.sh` together (next finding).


### FINDING_4: `scripts/test-token-report.sh` harness still asserts dollar-line — plan only updates `test-token-report-summary-format.sh`
- **Reviewers**: Cursor-Requirements, Codex-Arch, Codex-Innovation, Codex-Requirements (HIGH, 4 reviewers)
- **Concern**: `scripts/test-token-report.sh:516-534` is part of `make lint` and currently asserts `💰 Cost: TOTAL` in `--summary` output samples. The plan only edits `test-token-report-summary-format.sh`. `make lint` will FAIL post-merge until this harness is also updated.
- **Proposed resolution**: Add `scripts/test-token-report.sh` to the "Files to modify" list. Update Cases 1 and 2 (and any other dollar-line assertions) to assert (a) ABSENCE of the dollar-primary cost line in `--summary` output, and (b) PRESENCE of the new non-cost Tokens summary line introduced by FINDING_3.


### FINDING_5: `scripts/test-design-structure.sh` Check 15 hard-wires the OLD `### Terminal cost line` / `render-cost-line.sh` strings
- **Reviewers**: Cursor-Arch, Cursor-Innovation, Cursor-Foreground-Compliance, Codex-Pragmatic (HIGH, 4 reviewers)
- **Concern**: `scripts/test-design-structure.sh:373-401` Check 15 uses a 45-55-line look-back window to pair `render-cost-line.sh` or `### Terminal cost line` with cancel/footer markers. The plan removes those literals but does not retarget the Check 15 pairing logic. `make lint` and `scripts/test-design-structure.sh` will FAIL until the harness is updated in the same change.
- **Proposed resolution**: Add an explicit work item to retarget Check 15 to the new strings (`### Final summary block` and `render-final-summary.sh`) while preserving the pairing-distance intent. Update the sibling spec `scripts/test-design-structure.md` accordingly.


### FINDING_6: `--duration` sourcing for /design is hand-waved — needs concrete `timing-report.sh` invocation matching `/implement` parity
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Requirements, Codex-Edge, Codex-Innovation (HIGH, 6 reviewers)
- **Concern**: The plan's `render-final-summary.sh` step 5 passes `--duration <elapsed-from-timing-ledger>` but never specifies WHERE that value comes from. `/implement`'s `write-final-report.sh:188-190` runs `timing-report.sh --format json --output …/timing-report.json` and parses `total_hms` via `jq`. /design has `timing-ledger.sh mark` calls but no canonical `timing-report.json` under `$DESIGN_TMPDIR` before publish. Cancel paths skip publish entirely. Without explicit duration sourcing, `--duration` will be `N/A` or each implementer invents a different path.
- **Proposed resolution**: Add a concrete step to `render-final-summary.sh`: best-effort `timing-report.sh --full --format json --output "$DESIGN_TMPDIR/timing-report-final.json"` with `LARCH_TIMING_SKILL=design` and `LARCH_TIMING_LEDGER` from session env, then parse `total_hms` via `jq` (same field name as `write-final-report.sh`). Fallback: empty `--duration` → renderer shows `N/A`. Cover the cancel-path no-publish case in `test-render-final-summary.sh`.


### FINDING_7: Step 5c ordering — render+upsert BEFORE `design-log-publish.sh` means publish failures can't be reflected in the summary
- **Reviewers**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Innovation (HIGH, 4 Codex reviewers)
- **Concern**: The plan renders, prints to chat, and upserts the GitHub comment BEFORE `design-log-publish.sh` runs. If publish fails, the existing flow appends a `Warnings` entry to `execution-issues.md` AFTERWARD, but the summary has already been committed to GitHub with stale Warnings count and a `larch-logs/design/<RUN_ID>/` path that may not actually land. Users see an inaccurate final summary.
- **Proposed resolution**: Two-phase render. Phase 1: render `final-summary.md` to disk (no print, no upsert) BEFORE publish so the committed `larch-logs/design/<RUN_ID>/final-summary.md` projection is in place when `design-log-publish.sh` enumerates `$DESIGN_TMPDIR`. Phase 2: after publish completes (success or failure → updated Warnings count), RE-RENDER with the final Warnings/Cost/Run-logs state, THEN print to chat AND upsert via `tracking-issue-summary.sh`. Document the two-phase order in `skills/design/scripts/render-final-summary.md`.


### FINDING_8: `scripts/render-run-summary.sh` `usage()` text still says implement-only after argv widens to `design`
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Requirements, Codex-Pragmatic (MEDIUM mechanical, 5 reviewers)
- **Concern**: After extending argv validation to `implement|design`, the `usage()` function at `scripts/render-run-summary.sh:28-29` still says "render-run-summary.sh --skill implement ...". Operators running `--help` see misleading text. Trivially fixable but explicitly not in plan's edit list.
- **Proposed resolution**: Add a sub-bullet under UPDATED: `scripts/render-run-summary.sh`: update `usage()` to list both `implement` and `design` skills, or point to `render-run-summary.md` for full argv reference.


### FINDING_9: `skills/implement/SKILL.md:1814-1818` Step 17 prose still says "continue to the token summary" after deletion
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Requirements, Codex-Pragmatic (MEDIUM, 5 reviewers)
- **Concern**: After deleting the Step 18 token/timing chat tail block, the surrounding prose at lines 1814-1818 still tells orchestrators to "continue to the token summary block" on `write-final-report.sh` failure. Stale instruction can cause halt or improvised chat output.
- **Proposed resolution**: Rewrite the Step 17 failure-continuation prose to point to Step 18 cleanup directly (or to silent ledger refresh) and remove all references to a removed token-summary block. Same edit pass as the Bash block removal.


