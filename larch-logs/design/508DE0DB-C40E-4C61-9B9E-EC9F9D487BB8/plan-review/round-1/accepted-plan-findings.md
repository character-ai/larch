### FINDING_1: Canonical security/install docs not synced with new stamp/prune contract
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-dyn-retention-invariants, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-doc-contract-sync
- **Severity**: important
- **Concern**: The plan changes `/upgrade-larch` install-stamp and prune trust behavior (stamp on any successful install, mtime backfill during prune, running/target retention) but only updates the sibling script contract (`upgrade-larch.md`). `SECURITY.md` and `docs/installation-and-setup.md` still describe the old model: prune does not write mtime-derived stamps, stamps apply only to verified or already-latest stable dirs, and legacy unstamped dirs use mtime only at ranking time. After merge, canonical docs would contradict implementation and misstate cache mutation and retention for operators and reviewers. The sibling doc’s edit-in-sync list names `docs/installation-and-setup.md`, but the plan omits updating it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan to include the minimal matching edits to docs/installation-and-setup.md and SECURITY.md, or explicitly justify why SECURITY.md needs no change after the redaction-helper availability fix
  - From Codex-Edge: Update the /upgrade-larch install-stamp prune trust paragraph to match the proposed behavior, including unverified-install stamping, mtime backfill, running-dir retention, and verified-only pruning
  - From Cursor-Innovation: Add SECURITY.md:240 to Files to modify: document stamp-on-any-successful-install with prune still gated; backfill mtime stamps during prune; retain target plus INSTALLED_VERSION
  - From Codex-Innovation: Update these two lines minimally to match the new stamp/backfill contract, or remove Defect C/unverified stamping from the plan.
  - From Codex-Pragmatic: Add minimal matching updates to SECURITY.md and docs/installation-and-setup.md, or drop Change 3 from the plan.
  - From Codex-Requirements: Keep the implementation scope narrow, but add targeted updates to SECURITY.md and docs/installation-and-setup.md for Change 2 and Change 3, or drop Change 3/unstable stamping if the two-file constraint is meant to remain binding.
  - From Codex-dyn-doc-contract-sync: Add a minimal SECURITY.md update covering any successfully installed version stamp, verified-only prune, best-effort mtime backfill for numeric cached dirs, and target/running-dir retention.
  - From Codex-dyn-doc-contract-sync: Add a small docs/installation-and-setup.md edit matching the sibling contract: stamp any successful install, prune remains verified-only, running and target dirs are retained when present/version-shaped, and unstamped dirs are normally backfilled from mtime before ranking.


### FINDING_3: Sibling/plan doc overstates unstamped dirs as always short-lived after prune
- **Reviewer(s)**: Cursor-dyn-doc-contract-sync, Codex-dyn-doc-contract-sync
- **Severity**: important
- **Concern**: Proposed sibling-doc and plan wording treats unstamped legacy dirs as transient until the next prune backfills them, but backfill runs only at prune entry inside `prune_cached_versions`. When prune is skipped (e.g. `gh` unavailable, verify fail) or `stat_mtime`/stamp write fails (e.g. read-only cache), dirs can remain unstamped across many runs and still sort below stamped dirs. Operators may believe the unstamped tier always disappears after every prune.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-contract-sync: Qualify sibling doc text: unstamped legacy dirs get mtime backfill at prune entry only; they persist until a prune run, and some may remain unstamped if backfill cannot run
  - From Codex-dyn-doc-contract-sync: Word the sibling doc as best-effort: unstamped numeric dirs are normally backfilled from mtime before ranking, but failed mtime reads or stamp writes leave them unstamped and bottom-ranked as before.

