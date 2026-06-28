### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] `regression` is not a serialized OOS focus-area token. Scenario: Reviewer templates and `plan_review_round.py` emit only `code-quality`, `risk-integration`, `correctness`, `architecture`, and `security` in `- **Focus area**:` lines. Matching `focus-area: regression` adds parser branches and tests for a value the filing pipeline never produces; correctness-tagged deferrals already map to `correctness`.
- **Proposed resolution**: Limit `HIGH_RISK_FOCUS_VALUES` to `{"correctness"}` (or reuse the canonical five-value enum subset) and drop regression-specific unit tests unless a real serializer path is added first.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/oos_priority.py
- **Concern**: [SCOPE-REDUCTION] Third focus-area regex duplicates existing parsers. Scenario: The plan adds `oos_priority.is_high_risk_oos_block()` with regex mirroring `file_oos._FOCUS_AREA_LINE_RE` / `oos._FOCUS_AREA_FIELD_RE`. A third copy drifts when security matching was fixed separately in the past and expands the ~1155-line surface without new behavior beyond `correctness`.
- **Proposed resolution**: Export one shared high-risk matcher from `file_oos.py` or `oos.py` (parameterized value set) and have `oos_priority.py` re-export constants only.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:104-196; python/larch/design/design_lifecycle.py:172-196; python/larch/issue/oos_filer.py:53-100
- **Concern**: [SCOPE-REDUCTION] The plan adds a second label-only retry state machine and durable cross-session sidecars. Scenario: The MVP already has to add priority labeling and a backlog section. This retry plumbing expands the surface area into new prepare/annotate actions, cache restore logic, and extra completion rules that are not needed to satisfy the stated feature
- **Proposed resolution**: Remove the label-only retry and durable sidecar branches unless a concrete correctness failure requires them. Keep the change to same-run filing-time labeling plus backlog reporting
