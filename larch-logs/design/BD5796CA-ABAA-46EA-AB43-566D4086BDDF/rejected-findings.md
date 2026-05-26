### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: AGENTS.md:51-53; scripts/lib-design-reentry-guard.sh (planned)
- **Concern**: Marker path is keyed only by issue number and PPID, not repository identity. Scenario: A same Claude process can work across repositories while the invariant is only per repo; issue #2935 in another repo within the TTL can be falsely refused by a marker from this repo
- **Proposed resolution**: Include a stable repo discriminator in the marker grammar, such as resolved owner/repo or a sanitized/hash repo root, and add same-PPID same-issue different-repo coverage to the harness


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:23,82,975
- **Concern**: Step 5c item 11 ties marker write to the same PUBLISH_OK/rename gate as item 10. Scenario: When plan-block-write succeeds but PUBLISH_OK=false (item 8 continues) or rename is skipped, no marker is written; a same-session re-fire sees no [DESIGNED] title and passes sub-step 2.6 — the gap the plan cites is only partially closed
- **Proposed resolution**: Gate design_reentry_marker_write on Step 5c step-4 success (PLAN_WRITE_OK=true) only; keep rename/publish semantics separate


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-design-reentry-guard.sh (proposed marker path), scripts/session-setup.sh:230-267
- **Concern**: Marker key omits repository identity. Scenario: The planned design-completed-<issue>-<ppid> path collides for sequential same-session work in two repositories with the same issue number within the TTL. The plan cites the single-runner invariant, but that invariant is per repository and does not prevent sequential same-PPID multi-repo designs.
- **Proposed resolution**: Include a sanitized repo key in the marker path, using resolved owner/repo when available or the same clone-tag style session-setup already uses, and cover same issue plus different repo in the harness.


### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:49-50,114
- **Concern**: Marker identity is repo-agnostic while issue numbers are only repo-scoped. Scenario: A same Claude session can legitimately operate on another checkout or fork with the same issue number, but design-completed-<issue>-<ppid> would refuse it; the plan dismisses this by treating the single-runner invariant as global when it is per repo
- **Proposed resolution**: Include a repo/checkout discriminator in the marker key, preferably a sanitized resolve-repo.sh owner/repo value after issue binding, or fall back to the clone tag pattern used by session-setup.sh


### [Plan Review] FINDING_40

### FINDING_40:
- **Reviewer(s)**: Codex-dyn-bash-library-portability
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-design-reentry-guard.sh (proposed), <TMPDIR>/plan.txt:51
- **Concern**: design_reentry_marker_hit does not specify clean handling for race deletion between the existence check and stat. Scenario: A marker can be removed after the function decides it is present but before stat runs; without stderr suppression and an explicit failed-stat branch, raw stat errors can surface in the operator Bash transcript instead of a clean MARKER_HIT=false return
- **Proposed resolution**: Add an explicit stat-failure branch that treats ENOENT or any nonnumeric mtime as a miss, prints a single KV line such as MARKER_HIT=false REASON=absent-or-stat-failed, returns 1, and suppresses stat stderr; add a test using a stubbed stat or removed marker to pin no stderr leakage


