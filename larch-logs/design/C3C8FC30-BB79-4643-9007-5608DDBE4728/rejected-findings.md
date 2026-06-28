### [Plan Review] FINDING_4

### FINDING_4: Durable label-retry sidecars lack repo disambiguation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Cross-session paths under `~/.cache/larch/design-oos-filed/` (`*.priority-pending`, `*.combined.md`, `*.filing-order.txt`) follow the existing bare `<issue>.md` pattern with no repo slug. Issue numbers collide across remotes, so a pending sidecar from repo A issue 42 can be restored during repo B issue 42 label-only retry and apply `oos-correctness` to the wrong URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Include a repo slug (for example `owner__repo__42.priority-pending`) in every cross-session path helper, migrate readers/writers together, and extend `--clear-cross-session-cache` to delete the repo-scoped set.


### [Plan Review] FINDING_5

### FINDING_5: issue_number_from_url() lacks GH_HOST enterprise support
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate-label backfill derives issue number from URL before `gh issue edit`, but the parser only handles github.com. On GitHub Enterprise or custom hosts, backfill fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Parse the host-agnostic issue path or mirror the existing GH_HOST-aware URL pattern already used by issue_create.


### [Plan Review] FINDING_9

### FINDING_9: Backlog report ignores pre-label high-risk OOS issues
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Backlog section only reports issues that already carry the new `oos-correctness` label. Pre-existing open [OOS] correctness/regression issues filed before this change stay invisible, so the feature does not surface the backlog it is meant to prioritize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Classify open OOS rows by body text as well as label, or add a one-time backfill for existing high-risk OOS before the report depends on the new label.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] `regression` is not a serialized OOS focus-area token. Scenario: Reviewer templates and `plan_review_round.py` emit only `code-quality`, `risk-integration`, `correctness`, `architecture`, and `security` in `- **Focus area**:` lines. Matching `focus-area: regression` adds parser branches and tests for a value the filing pipeline never produces; correctness-tagged deferrals already map to `correctness`.
- **Proposed resolution**: Limit `HIGH_RISK_FOCUS_VALUES` to `{"correctness"}` (or reuse the canonical five-value enum subset) and drop regression-specific unit tests unless a real serializer path is added first.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] Third focus-area regex duplicates existing parsers. Scenario: The plan adds `oos_priority.is_high_risk_oos_block()` with regex mirroring `file_oos._FOCUS_AREA_LINE_RE` / `oos._FOCUS_AREA_FIELD_RE`. A third copy drifts when security matching was fixed separately in the past and expands the ~1155-line surface without new behavior beyond `correctness`.
- **Proposed resolution**: Export one shared high-risk matcher from `file_oos.py` or `oos.py` (parameterized value set) and have `oos_priority.py` re-export constants only.


