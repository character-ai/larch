### FINDING_1: Label-only retry blocked by accepted-file guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: After Step 6 cleanup, cross-session label-only retry restores sentinel, combined, and filing-order sidecars but not `oos-accepted-design.md`. `file_oos_annotate_main()` / `prepare` still hard-require accepted text and/or order files before the label-only branch runs, so high-risk issues cannot be relabeled without re-filing even though the plan and tests expect label-only retry to work from restored sidecars alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Branch on `--label-only` / `label-only-retry` before any accepted/order_file requirements. Label-only may run with restored `oos-issues-created.md` plus post-cap `oos-combined.md` and optional filing-order only.
  - From Codex-Arch: Check the label-retry marker before the no-items guard too, and either restore `oos-accepted-design.md` from cache or make the label-only annotate path operate directly from the restored sentinel and combined sidecars.
  - From Codex-Pragmatic: Skip the accepted-file guard on the --label-only branch, or restore oos-accepted-design.md as part of the durable retry state.

### FINDING_2: Same-session annotate-label-failed routes to Step 5b.5
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: When priority labeling fails in-session (`annotate-label-failed`, non-zero rc, `ISSUES_FAILED=0`), `finalize-step5.md` still treats generic non-zero annotate as "continue to Step 5b.5". The lifecycle can return without writing `.completed/step-5b`, then `design-step3b-entry.sh` hard-fails on missing step-5b instead of re-running label-only annotate, even though `.oos-priority-label-pending` and `STEP5B_NEEDS_ANNOTATE=true` are meant to allow same-session retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `NEXT_ACTION=file-issues` annotate section, carve out `annotate-label-failed` / pending-marker paths: re-invoke `design-step5b-annotate.sh --label-only` once or stop for repair. Do not use the generic "continue to Step 5b.5" prose on those paths.
  - From Cursor-Pragmatic: Add an explicit carve-out: when annotate stdout is `annotate-label-failed`, `.oos-priority-label-pending` exists, or durable `*.priority-pending` is set, do not continue to Step 5b.5; stop/repair and rerun annotate in `--label-only` mode (or re-prepare with `label-only-retry`) before diagram/publish.

### FINDING_3: Design label gh helpers omit explicit repo wiring
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Plan adds `_run_gh()`, `_ensure_oos_correctness_label()`, and `_apply_oos_correctness_label()` but never binds `REPO` from design session env. Label create/edit can target the wrong repository or fail when cwd is not the filing repo, unlike implement `oos_filer.py` which already threads `repo` through batch filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Thread `REPO` from session env / `oos-filing-prepare.env` into every design label argv builder (`gh label create`, `gh issue edit --add-label`), matching implement `oos_filer.py` repo handling; fail closed when `REPO` is missing.

### FINDING_4: Durable label-retry sidecars lack repo disambiguation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Cross-session paths under `~/.cache/larch/design-oos-filed/` (`*.priority-pending`, `*.combined.md`, `*.filing-order.txt`) follow the existing bare `<issue>.md` pattern with no repo slug. Issue numbers collide across remotes, so a pending sidecar from repo A issue 42 can be restored during repo B issue 42 label-only retry and apply `oos-correctness` to the wrong URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Include a repo slug (for example `owner__repo__42.priority-pending`) in every cross-session path helper, migrate readers/writers together, and extend `--clear-cross-session-cache` to delete the repo-scoped set.

### FINDING_5: issue_number_from_url() lacks GH_HOST enterprise support
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate-label backfill derives issue number from URL before `gh issue edit`, but the parser only handles github.com. On GitHub Enterprise or custom hosts, backfill fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Parse the host-agnostic issue path or mirror the existing GH_HOST-aware URL pattern already used by issue_create.

### FINDING_6: Filed-url duplicate path skips priority merge
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: In `oos_filer.py`, the filed-url branch bypasses the priority merge. A later duplicate can be the only high-risk copy but is diverted into "already filed" before the retained block absorbs its priority bit, so the filed issue stays unlabeled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move priority extraction before the filed-url continue, or merge filed duplicates back into the retained normalized-title block and carry that bit into backfill.

### FINDING_7: Label-only priority map undefined for partial create failures
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: The label-only priority map only handles equal-count and sole-rollup cases. With gaps in `ISSUE_n` results after mixed `/larch:issue` partial failures, label-only retry can assign `oos-correctness` to the wrong issue or skip a survivor entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Map surviving URLs by the original ISSUE_n order plus failure markers, not just by raw list length or the rollup special case.

### FINDING_8: Priority pending marker timing ambiguous at label-phase entry
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan requires writing `oos-issues-created.md` before the first label call but only describes `.oos-priority-label-pending` in the label-failure branch. If labeling writes the sentinel then calls `gh` with pending created only after a failed edit, a crash between those steps leaves a filed sentinel and no pending marker; the next prepare hits `skip-sentinel` and never enters `label-only-retry`, so high-risk issues can stay unlabeled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly that when any post-cap URL needs `oos-correctness`, create `.oos-priority-label-pending` and sync durable sidecars at label-phase entry before the first `gh label create`/`gh issue edit`, then remove them only after all required labels succeed; keep the failure handler as a backstop, not the only writer.

### FINDING_9: Backlog report ignores pre-label high-risk OOS issues
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Backlog section only reports issues that already carry the new `oos-correctness` label. Pre-existing open [OOS] correctness/regression issues filed before this change stay invisible, so the feature does not surface the backlog it is meant to prioritize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Classify open OOS rows by body text as well as label, or add a one-time backfill for existing high-risk OOS before the report depends on the new label.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] `regression` is not a serialized OOS focus-area token. Scenario: Reviewer templates and `plan_review_round.py` emit only `code-quality`, `risk-integration`, `correctness`, `architecture`, and `security` in `- **Focus area**:` lines. Matching `focus-area: regression` adds parser branches and tests for a value the filing pipeline never produces; correctness-tagged deferrals already map to `correctness`.
- **Proposed resolution**: Limit `HIGH_RISK_FOCUS_VALUES` to `{"correctness"}` (or reuse the canonical five-value enum subset) and drop regression-specific unit tests unless a real serializer path is added first.

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] Third focus-area regex duplicates existing parsers. Scenario: The plan adds `oos_priority.is_high_risk_oos_block()` with regex mirroring `file_oos._FOCUS_AREA_LINE_RE` / `oos._FOCUS_AREA_FIELD_RE`. A third copy drifts when security matching was fixed separately in the past and expands the ~1155-line surface without new behavior beyond `correctness`.
- **Proposed resolution**: Export one shared high-risk matcher from `file_oos.py` or `oos.py` (parameterized value set) and have `oos_priority.py` re-export constants only.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:104-196; python/larch/design/design_lifecycle.py:172-196; python/larch/issue/oos_filer.py:53-100
- **Concern**: [SCOPE-REDUCTION] The plan adds a second label-only retry state machine and durable cross-session sidecars. Scenario: The MVP already has to add priority labeling and a backlog section. This retry plumbing expands the surface area into new prepare/annotate actions, cache restore logic, and extra completion rules that are not needed to satisfy the stated feature
- **Proposed resolution**: Remove the label-only retry and durable sidecar branches unless a concrete correctness failure requires them. Keep the change to same-run filing-time labeling plus backlog reporting
