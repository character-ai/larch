---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: SessionStart payload gating may never reset stale statusline progress
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The statusline reset logic appears to depend on `payload["source"]`, but the existing SessionStart hook paths described here do not appear to supply that field. If SessionStart events arrive without `source`, the reset becomes a no-op and stale `current` progress pointers can keep rendering old breadcrumbs at startup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Split hooks/hooks.json statusline SessionStart into startup|clear vs resume|compact matchers (reset only on the first), or document and add a hook-harness fixture proving SessionStart stdin includes source before shipping.`


### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline.py:RESET_SESSION_SOURCES
- **Concern**: [SCOPE-REDUCTION] Reset on source=clear can drop live foreground-run breadcrumbs. Scenario: The issue requires clearing stale breadcrumbs when Claude starts, not on every SessionStart event. Including clear in RESET_SESSION_SOURCES deletes current after progress activate at Step 0 while many /design and /implement steps before the first bgjob still append via append_breadcrumb, which no-ops without current. A context-clear during an active run hides all later statusline output until a new skill bootstrap re-activates.
- **Proposed resolution**: Limit RESET_SESSION_SOURCES to frozenset({"startup"}) only. Drop clear-specific tests and docs bullets that treat clear like startup. Keep resume and compact as no-op sources. 1. **correctness** (`python/larch/report/statusline.py`) — **[SCOPE-REDUCTION] Reset on `source=clear` can drop live foreground-run breadcrumbs.** The bound issue is stale breadcrumbs when Claude **starts**, not on every SessionStart event. Treating `clear` like `startup` deletes `current` after Step 0 has already called `progress activate`, while many early `/design` and `/implement` steps (before the first bgjob) still write through `append_breadcrumb`, which returns `False` when `current` is missing. A context clear during an active foreground run would silence the statusline for the rest of that run. Limit `RESET_SESSION_SOURCES` to `{"startup"}`; remove `clear`-specific tests and doc bullets that equate it with startup.


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/statusline.py:RESET_SESSION_SOURCES
- **Concern**: [SCOPE-REDUCTION] Drop source=clear from session reset set. Scenario: Bootstrap and design Step 0 call progress activate once (python/larch/state/bootstrap.py:502-503, python/larch/design/design_step0.py:199-208). Later timing marks use append_breadcrumb, which requires current (python/larch/report/progress_file.py:127-129). SessionStart clear can fire mid-session before bgjob registration; deactivate_run then removes current with no re-activate, so statusline stays blank for the rest of the run. The bug report only requires a clean statusline on fresh Claude start.
- **Proposed resolution**: Limit RESET_SESSION_SOURCES to {"startup"} only; keep resume and compact as no-op. Remove clear-specific tests/docs unless a separate active-session guard is added. ### FINDING 1: [risk-integration] Drop `source=clear` from reset set **Location:** `python/larch/report/statusline.py` (`RESET_SESSION_SOURCES`) **Concern:** The plan resets on `startup` and `clear`, but only live bgjobs block reset. `/design` and `/implement` activate `current` once at Step 0, then append breadcrumbs through `append_breadcrumb`, which no-ops when `current` is missing. A mid-session `clear` SessionStart event (before Step 3 bgjobs exist) can delete `current` while the skill is still running. Nothing re-activates the pointer until a new run starts. **Suggested revision:** Restrict reset to `source=startup` only. That matches the issue scope (“when claude starts”) with minimal surface area. Keep `resume` and `compact` as no-op. Drop `clear` from the frozenset, tests, and docs unless you add an active-session guard (for example tmpdir resolution like `sessionstart-health.sh`). --- Overall the plan is well aligned with existing fd-safe helpers (`_open_existing_directory_fd`, symlink refusal) and correctly re-feeds captured stdin to both CLI calls, which avoids the double-read failure mode. The startup + live-bgjob guard path should fix the reported stale breadcrumb on fresh session start.

---LARCH-REJECTED-END---
