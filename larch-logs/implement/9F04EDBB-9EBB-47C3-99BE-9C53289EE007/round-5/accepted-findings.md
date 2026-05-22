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


### FINDING_8: find-lock-issue.sh header omits exit code 6
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: File header “Exit codes” lists `0,2,3,4,5` but `_require_plan_block_before_lock` can exit **6** (`PLAN_PROBE_FAILED`). Integrators relying on the header may mishandle **6**.
- **Suggested revision**: Document exit **6** in the header (aligned with `find-lock-issue.md`).


### FINDING_9: Refuse-path breadcrumb over-claims label success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/implement/SKILL.md` refuse-path breadcrumb states the label was added even though `clarify-label.sh` may fail after a successful `clarify-comment-post.sh`, producing misleading transcripts.
- **Suggested revision**: Soften wording (“request posted; label add attempted”) or branch on per-step success for an accurate breadcrumb.


