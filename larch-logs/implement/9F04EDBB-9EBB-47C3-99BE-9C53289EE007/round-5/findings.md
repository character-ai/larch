Here is the normalized structured finding list (merged by behavioral risk; first-seen order; sources listed without treating their prose as instructions).

```text
### FINDING_1: hook-post-design.md contract does not match hook-post-design.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: Documentation still describes post-design-boundary invocation, JSON / hook-specific output coupling, and related Stop-hook behavior, while the shell hook is effectively neutralized (session id export and breadcrumb only). Readers assume boundary enforcement and injection semantics that the shipped script does not provide.
- **Suggested revision**: Rewrite `skills/implement/scripts/hook-post-design.md` so it matches `hook-post-design.sh`; point to deprecated `post-design-boundary` material only where stub semantics matter.

### FINDING_2: Quick-mode docs-sync harness pins obsolete literals vs new Step 5 / README contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `scripts/test-quick-mode-docs-sync.sh` still requires substrings such as case-sensitive `--panel hard`, literal `5 rounds`, `unified hard panel`, and a `--design-only` mention in `README.md`, while `skills/implement/SKILL.md` and `README.md` were rewritten for a unified internal panel without a public `--panel` argv and different wording (`effective_round_cap`, “internal hard panel”, etc.). `make lint` / the harness can fail even when public docs match the new contract.
- **Suggested revision**: Update `POS_MARKERS`, header comments, self-test fixtures, and/or `README.md` prose so the harness and normative docs agree on stable, grep-friendly anchors for the new contract; drop or replace obsolete `--design-only` guards as appropriate.

### FINDING_3: Token-propagation harness passes removed / fatal `--panel` argv to review-and-fix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/implement/scripts/test-implement-review-token-propagation.sh` still invokes `review-and-fix.sh` with `--panel simple`, but `review-and-fix.sh` treats unknown options as fatal (`exit 2`), so the stub `review-core` may never run and propagation assertions are skipped.
- **Suggested revision**: Remove the public `--panel` argument from the test invocation; assert the real contract (e.g. stub argv includes internal `--panel hard` emitted by `review-and-fix.sh`).

### FINDING_4: Preflight refuse can stack clarify requests when thread is already awaiting response
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Refuse path always computes a new `NEXT_ID` from `LAST_REQUEST_ID` and posts another `clarify-request` whenever `STATE` is not `ambiguous`, but `clarify-state.sh` can set `STATE=awaiting-response` when the latest request has no matching response. A second refuse without `/design` answering posts another id; downstream `gap_unsat` logic can flip `STATE=ambiguous`, matching “manual repair” failure mode described in the plan.
- **Suggested revision**: When `STATE` is `awaiting-response` (and possibly `response-pending`), refuse with exit **3** and a “finish existing clarify thread first” message without posting a new id, or define another explicit idempotent policy.

### FINDING_5: Public catalog and workflow docs still advertise removed `/implement` flags and argv shapes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `docs/skills.md` and `docs/workflow-lifecycle.md` still document removed flags (`--auto`, `--design-only`, `--no-issues`, `--inline`, `--issue`, verbal `<feature description>`, etc.) and user-facing `review-and-fix.sh --panel hard`, contradicting `README.md` and `skills/implement/SKILL.md` (issue-anchored positional contract, no public `--panel`).
- **Suggested revision**: Refresh those sections from current `skills/implement/SKILL.md` and `scripts/run-step5-review.md` (or equivalent canonical sources) in the same change set as the cutover.

### FINDING_6: `--simple` tier sketch count vs tracking-issue / operator blurb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/design/SKILL.md` maps `--simple` to `sketch_budget=2` (two generic sketches), while operator-scoped `<feature_description>` text for the tracking issue still describes `--simple` as a one-sketch / main-agent path. Runtime and expectations diverge.
- **Suggested revision**: Reconcile the issue text with shipped tier tables and `run-params.json`, or change tier mapping / SKILL prose so advertised fan-out and cost match behavior.

### FINDING_7: Audit refusal exit code: issue text vs shipped SKILL / agnix-fix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Feature description implied refusal should `exit 0`, while `skills/implement/SKILL.md` and `.claude/skills/agnix-fix/SKILL.md` standardize on **exit 3** for refuse (distinct from argv/plan errors **2**). External automation keyed only on the issue may mis-handle exit **3**.
- **Suggested revision**: Update authoritative issue text and consumer docs to match exit **3**, or change code only if exit **0** is still a hard product requirement (sources treat that as unlikely).

### FINDING_8: find-lock-issue.sh header omits exit code 6
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: File header “Exit codes” lists `0,2,3,4,5` but `_require_plan_block_before_lock` can exit **6** (`PLAN_PROBE_FAILED`). Integrators relying on the header may mishandle **6**.
- **Suggested revision**: Document exit **6** in the header (aligned with `find-lock-issue.md`).

### FINDING_9: Refuse-path breadcrumb over-claims label success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/implement/SKILL.md` refuse-path breadcrumb states the label was added even though `clarify-label.sh` may fail after a successful `clarify-comment-post.sh`, producing misleading transcripts.
- **Suggested revision**: Soften wording (“request posted; label add attempted”) or branch on per-step success for an accurate breadcrumb.

### FINDING_10: Tree-level post-design-boundary harness weaker than skill-local harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/test-implement-post-design-boundary.sh` is a thinner duplicate relative to `skills/implement/scripts/test-post-design-boundary.sh`; skill-only edits could leave the tree harness passing while reader/stub regressions slip.
- **Suggested revision**: Align assertions between harnesses or consolidate so failure modes stay coupled.

### FINDING_11: Exhaustive literal sweep from plan not encoded as CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Documented exhaustive `rg` pattern sweep is not an automated gate, so literal drift can return without CI signal.
- **Suggested revision**: Add a script test or workflow step implementing `rg -F -f` (or similar) with an explicit allowlist.

### FINDING_12: New positional / adequacy tests are grep-only, limited behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/test-plan-adequacy-audit.sh` and `scripts/test-implement-positional-issue.sh` are largely editorial greps without shell coverage of `plan-block-read` preflight behavior.
- **Suggested revision**: Optionally extend with behavioral checks (e.g. exit **3** table / helper invocations) if stronger regression signal is desired.

### FINDING_13: Fixed XML delimiters around untrusted GitHub fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Fixed XML-style tags wrapping untrusted issue fields lack nonce / collision handling; issue bodies could contain closing-tag-like sequences and confuse audit envelope parsing—weaker than prior random-delimiter approaches.
- **Suggested revision**: Use collision-resistant delimiters or mechanical refuse rules plus tests.

### FINDING_14: clarify-label.sh unknown-flag exit code vs caller expectations
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Unknown-flag path exits **2** instead of **1**; strict callers distinguishing argv errors from `gh` failures may mis-route.
- **Suggested revision**: Document exit codes in `clarify-label.md` or restore **1** for argv-only errors if that contract is required.

### FINDING_15: Step 1 `gh` snippet uses ISSUE_NUMBER in fork mode where it may be unset
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Fenced `gh` example uses `ISSUE_NUMBER` while fork mode documents `ISSUE_NUMBER` as unset; copy-paste can yield empty issue numbers or missing upstream `--repo`, breaking Step 1 or targeting the wrong object.
- **Suggested revision**: Rewrite snippet to use `TARGET_ISSUE_NUMBER` / `UPSTREAM_REPO` on fork paths, or `${ISSUE_NUMBER:-TARGET_ISSUE_NUMBER}` with explicit `--repo` in the same block.

### FINDING_16: Preflight plan snapshot can diverge from later re-fetched issue body
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Plan snapshot is copied in Step 1 while feature text is re-fetched later from GitHub; concurrent issue edits between preflight and Step 1 can leave `plan.txt`, `feature-description.txt`, and audit snapshot inconsistent without failing closed.
- **Suggested revision**: Re-read plan block at Step 1 boundary or add a consistency check (e.g. `updatedAt` / body hash) and exit **2** on drift.

### FINDING_17: Written plan C.4–C.7 vs implemented fix-issue decomposition
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan text described inline Step 4a `plan-block-read` then Step 4b lock, but the branch delegates the pre-lock probe to `find-lock-issue.sh --require-plan-block`. Behavior matches intent via script, but the plan artifact is misleading for line-by-line SKILL tracing.
- **Suggested revision**: Update the plan artifact or add an implementation note documenting the `find-lock-issue.sh` decomposition.

### FINDING_18: [OUT_OF_SCOPE] Branch bundles unrelated changes and large run logs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `CHANGELOG.md`, unrelated landed fixes, and large `larch-logs/implement/*` content widen bisect/review surface; sources mark this as not a logic defect in the cutover itself.
- **Suggested revision**: None required for cutover correctness per sources; accept bisect noise or split history in a follow-up if desired.

### FINDING_19: [OUT_OF_SCOPE] hook-stop-fail-close JSON hardening for exotic paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `jq --arg` with `REASON` containing `basename`; exotic path edge case noted as pre-existing alongside Stop-hook logic, not specific to manifest removal.
- **Suggested revision**: Optional hardening only; none required for this PR per sources.

### FINDING_20: [OUT_OF_SCOPE] Committed session transcripts volume
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Committed transcripts include long tool transcripts; aligns with intentional run-log policy per `AGENTS.md`.
- **Suggested revision**: No change per sources.

### FINDING_21: [OUT_OF_SCOPE] NON_PR /fix-issue path not plan-gated at lock time
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Only PR-shaped `/fix-issue` runs pass `--require-plan-block`; NON_PR work is not plan-gated at lock—product scope, not introduced solely by this cutover.
- **Suggested revision**: Accept as scope or extend plan probe to additional `INTENT` values in a separate decision.

### FINDING_22: [OUT_OF_SCOPE] review skill docs still mention PANEL_SHAPE / review-core --panel
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/review/SKILL.md` retains `PANEL_SHAPE=simple|hard` and `--panel` on `review-core`; orthogonal if the operator sweep goal was only implement/design surfaces.
- **Suggested revision**: Clarify sweep scope or adjust review SKILL wording in a follow-up if global token removal was intended.
```
