### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:357-386
- **Concern**: Label-only annotate still inherits mandatory accepted/order_file guards.. Scenario: The plan only moves label-only ahead of the empty `oos-issue.stdout.txt` check. `file_oos_annotate_main()` still exits 2 when `oos-design-filing-order.txt` or `oos-accepted-design.md` is missing. Cross-session restore syncs sentinel/combined/order sidecars, not accepted text, so label-only retry after cleanup cannot run even though the plan tests expect it.
- **Proposed resolution**: Branch on `--label-only` / `label-only-retry` before any accepted/order_file requirements. Label-only may run with restored `oos-issues-created.md` plus post-cap `oos-combined.md` and optional filing-order only.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/finalize-step5.md:43-47
- **Concern**: Same-session `annotate-label-failed` still falls through to Step 5b.5.. Scenario: After `/larch:issue` plus failed priority labeling, lifecycle can return non-zero without writing `.completed/step-5b`. `finalize-step5.md` still routes generic non-zero annotate to "continue to Step 5b.5". `design-step3b-entry.sh` then hard-fails on missing `step-5b` instead of re-running label-only annotate, even though `.oos-priority-label-pending` and `STEP5B_NEEDS_ANNOTATE=true` are meant to allow same-session retry.
- **Proposed resolution**: In the `NEXT_ACTION=file-issues` annotate section, carve out `annotate-label-failed` / pending-marker paths: re-invoke `design-step5b-annotate.sh --label-only` once or stop for repair. Do not use the generic "continue to Step 5b.5" prose on those paths.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py
- **Concern**: Design label `gh` helpers omit explicit repo wiring.. Scenario: Plan adds `_run_gh()`, `_ensure_oos_correctness_label()`, and `_apply_oos_correctness_label()` but never binds `REPO` from design session env (implement Step 9a.1 already threads `repo` through batch filing). Label create/edit can target the wrong repository or fail when cwd is not the filing repo.
- **Proposed resolution**: Thread `REPO` from session env / `oos-filing-prepare.env` into every design label argv builder (`gh label create`, `gh issue edit --add-label`), matching implement `oos_filer.py` repo handling; fail closed when `REPO` is missing.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:216-266
- **Concern**: Label-only retry still depends on `oos-accepted-design.md` and can fall through `skip-no-items` when the tmpdir was cleaned. Scenario: After Step 6 cleanup, the plan restores only sentinel, combined, and filing-order sidecars. If the accepted markdown is absent in the fresh tmpdir, `prepare` exits before the new `label-only` branch can run, so high-risk issues still cannot be relabeled without re-filing.
- **Proposed resolution**: Check the label-retry marker before the no-items guard too, and either restore `oos-accepted-design.md` from cache or make the label-only annotate path operate directly from the restored sentinel and combined sidecars.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] `regression` is not a serialized OOS focus-area token. Scenario: Reviewer templates and `plan_review_round.py` emit only `code-quality`, `risk-integration`, `correctness`, `architecture`, and `security` in `- **Focus area**:` lines. Matching `focus-area: regression` adds parser branches and tests for a value the filing pipeline never produces; correctness-tagged deferrals already map to `correctness`.
- **Proposed resolution**: Limit `HIGH_RISK_FOCUS_VALUES` to `{"correctness"}` (or reuse the canonical five-value enum subset) and drop regression-specific unit tests unless a real serializer path is added first.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_oos.py:97-100
- **Concern**: Durable label-retry sidecars stay keyed by bare issue number only. Scenario: Prior neutral finding still applies: new `*.priority-pending`, `*.combined.md`, and `*.filing-order.txt` paths under `~/.cache/larch/design-oos-filed/` follow the existing `<issue>.md` pattern with no repo disambiguation. Issue numbers collide across remotes, so a pending sidecar from repo A issue 42 can be restored during repo B issue 42 label-only retry and apply `oos-correctness` to the wrong URLs.
- **Proposed resolution**: Include a repo slug (for example `owner__repo__42.priority-pending`) in every cross-session path helper, migrate readers/writers together, and extend `--clear-cross-session-cache` to delete the repo-scoped set.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] Third focus-area regex duplicates existing parsers. Scenario: The plan adds `oos_priority.is_high_risk_oos_block()` with regex mirroring `file_oos._FOCUS_AREA_LINE_RE` / `oos._FOCUS_AREA_FIELD_RE`. A third copy drifts when security matching was fixed separately in the past and expands the ~1155-line surface without new behavior beyond `correctness`.
- **Proposed resolution**: Export one shared high-risk matcher from `file_oos.py` or `oos.py` (parameterized value set) and have `oos_priority.py` re-export constants only.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: issue_number_from_url() must support GH_HOST-backed enterprise issue URLs, not only github.com. Scenario: Duplicate-label backfill will fail on GitHub Enterprise or any custom host because the plan uses the URL parser to derive the issue number before gh issue edit.
- **Proposed resolution**: Parse the host-agnostic issue path or mirror the existing GH_HOST-aware URL pattern already used by issue_create.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:59-63,93-99
- **Concern**: The duplicate OR path misses rows that already carry Filed URL because the filed-url branch bypasses the priority merge.. Scenario: A later duplicate can be the only high-risk copy, but it is diverted into already before the retained block absorbs its priority bit, so the filed issue stays unlabeled.
- **Proposed resolution**: Move priority extraction before the filed-url continue, or merge filed duplicates back into the retained normalized-title block and carry that bit into backfill.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py
- **Concern**: The label-only priority map does not define how to align surviving URLs after a partial create failure.. Scenario: The plan covers mixed /larch:issue partial failures, but the mapping only handles equal-count and sole-rollup cases. With gaps in ISSUE_n results, label-only retry can assign oos-correctness to the wrong issue or skip a survivor entirely.
- **Proposed resolution**: Map surviving URLs by the original ISSUE_n order plus failure markers, not just by raw list length or the rollup special case.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py
- **Concern**: Priority pending marker timing is ambiguous relative to early sentinel write. Scenario: The plan requires writing `oos-issues-created.md` before the first label call, but only describes `.oos-priority-label-pending` in the label-failure branch. If labeling is implemented as write-sentinel then gh calls with pending created only after a failed edit, a crash between those steps leaves a filed sentinel and no pending marker; the next prepare hits `skip-sentinel` and never enters `label-only-retry`, so high-risk issues can stay unlabeled.
- **Proposed resolution**: State explicitly that when any post-cap URL needs `oos-correctness`, create `.oos-priority-label-pending` and sync durable sidecars at label-phase entry before the first `gh label create`/`gh issue edit`, then remove them only after all required labels succeed; keep the failure handler as a backstop, not the only writer.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/finalize-step5.md:45-47
- **Concern**: `annotate-label-failed` still follows the generic non-zero annotate continue path. Scenario: Prior fixes target `.completed/step-5b` and Step 5c gating, but the `NEXT_ACTION=file-issues` branch still says non-zero annotate without `ISSUES_FAILED>0` should append Tool Failures and continue to Step 5b.5. `annotate-label-failed` matches that path (`ISSUES_FAILED=0`, non-zero rc, non-empty stdout), so the orchestrator advances to a failing 5b.5 instead of halting or re-running label-only annotate in-session.
- **Proposed resolution**: Add an explicit carve-out: when annotate stdout is `annotate-label-failed`, `.oos-priority-label-pending` exists, or durable `*.priority-pending` is set, do not continue to Step 5b.5; stop/repair and rerun annotate in `--label-only` mode (or re-prepare with `label-only-retry`) before diagram/publish.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:379-386
- **Concern**: Label-only retry still hard-requires oos-accepted-design.md, but the plan only restores sentinel, combined, and filing-order sidecars.. Scenario: A fresh-session label-only retry after Step 6 cleanup still exits 2 before it can apply labels, so the new cross-session recovery path cannot complete.
- **Proposed resolution**: Skip the accepted-file guard on the --label-only branch, or restore oos-accepted-design.md as part of the durable retry state.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_issues.py:202-216
- **Concern**: Backlog section only reports issues that already carry the new oos-correctness label. Scenario: Pre-existing open [OOS] correctness/regression issues that were filed before this PR stay invisible, so the feature does not actually surface the backlog it is meant to prioritize
- **Proposed resolution**: Classify open OOS rows by body text as well as label, or add a one-time backfill for existing high-risk OOS before the report depends on the new label



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:104-196; python/larch/design/design_lifecycle.py:172-196; python/larch/issue/oos_filer.py:53-100
- **Concern**: [SCOPE-REDUCTION] The plan adds a second label-only retry state machine and durable cross-session sidecars. Scenario: The MVP already has to add priority labeling and a backlog section. This retry plumbing expands the surface area into new prepare/annotate actions, cache restore logic, and extra completion rules that are not needed to satisfy the stated feature
- **Proposed resolution**: Remove the label-only retry and durable sidecar branches unless a concrete correctness failure requires them. Keep the change to same-run filing-time labeling plus backlog reporting



