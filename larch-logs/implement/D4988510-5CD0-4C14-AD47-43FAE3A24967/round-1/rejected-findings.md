### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Empty `XDG_CACHE_HOME` misroutes the activation sentinel
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: If `XDG_CACHE_HOME=""`, the skill-side sentinel path and the hook-side `activation_dir()` path can diverge, so activation can fail or stay inert because the two sides are no longer looking in the same cache root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Mirror activation_dir() branching in skills/bug/SKILL.md and skills/research/SKILL.md; add test-deny-edit-write case for XDG_CACHE_HOME="".


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: A fresh sentinel can leak the hook until TTL expiry
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-hook-lifecycle
- **Severity**: important
- **Concern**: If `/research` or `/bug` exits after activation but before cleanup, the fresh sentinel can keep a leaked registration armed and deny unrelated writes until the 360-minute TTL expires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document residual risk; consider shorter TTL or explicit sentinel refresh; optional operator troubleshooting note.
  - From cursor-specialist-edge-cases: Shorten TTL or document manual rm of ~/.cache/larch/deny-edit-write-active/research-*; consider sentinel heartbeat during long runs.
  - From dyn-dyn-hook-lifecycle: Lower the operational TTL, add operator-visible troubleshooting for manual rm under `deny-edit-write-active/`, and/or centralize create/remove in a `python/cli.py` helper called from all documented abort and cleanup fences so fewer paths depend on orchestrator recall alone.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Cleanup and abort fences must self-contain the sentinel path
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-hook-lifecycle
- **Severity**: important
- **Concern**: Cleanup and abort snippets rely on sentinel bindings or removals carried across fresh Bash fences, so a later shell, context loss, or missed branch can make `rm -f` a no-op and leave the activation sentinel live until TTL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: After each activation block, explicitly parse and retain the printed sentinel path, and make cleanup snippets self-contained by assigning the parsed path before `rm -f`, or route sentinel create/remove through a helper that persists the path safely.
  - From cursor-specialist-edge-cases: Put rm -f "$RESEARCH_DENY_ACTIVE_SENTINEL" in a shared cleanup Bash fence like Step 4 and research-phase aborts.
  - From codex-specialist-edge-cases: After each sentinel `printf`, add explicit prose to parse and bind the sentinel path, like the existing `$BUG_TMPDIR` / `$RESEARCH_TMPDIR` parsing guidance. Make later cleanup snippets either use that parsed path explicitly or rederive it safely before `rm -f`.
  - From dyn-dyn-hook-lifecycle: In every cleanup and abort Bash fence, recompute and remove the sentinel from `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/deny-edit-write-active/<token>-$PPID` (or `rm -f` the token’s glob under that directory) instead of relying solely on the Step 0/2 parsed variable.
  - From dyn-dyn-hook-lifecycle: Align filing-failure branches with Step 3.5 item 7: remove the sentinel, then always proceed to Step 4 cleanup (or fold both into one shared cleanup snippet pinned by structure tests).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Sentinel TTL can expire mid-run without refresh
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The sentinel is created once and then only checked by age, so a `/research` run that lasts longer than the TTL can lose enforcement mid-flight unless the mtime is refreshed or the run aborts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh sentinel mtime at step boundaries or on long waits; or fail closed / abort when activation expires during an active run; add harness coverage for mid-run TTL expiry.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

