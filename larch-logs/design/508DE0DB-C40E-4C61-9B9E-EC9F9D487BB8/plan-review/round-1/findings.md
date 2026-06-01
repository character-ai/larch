### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:30-35
- **Concern**: Plan updates only the script sibling doc but skips named canonical/edit-in-sync docs for the changed install-stamp and pruning contract. Scenario: docs/installation-and-setup.md:38-40 will still say stamps are written only on verified/already-latest paths, legacy unstamped dirs fall back to mtime only, and only the target is always retained; SECURITY.md also remains unchecked despite the redaction-helper/running-dir protection being security-relevant
- **Proposed resolution**: Update the plan to include the minimal matching edits to docs/installation-and-setup.md and SECURITY.md, or explicitly justify why SECURITY.md needs no change after the redaction-helper availability fix

### FINDING_2:
- **Reviewer(s)**: Codex-Edge, Codex-dyn-retention-invariants
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:240
- **Concern**: Plan changes the install-stamp prune trust model but does not update SECURITY.md. Scenario: After the PR, code would stamp unverified installed versions and backfill stamps from mtime for every unstamped cached numeric dir, while SECURITY.md would still claim prune writes no mtime-derived stamps and stamp writes target only the verified/already-latest stable directory
- **Proposed resolution**: Update the /upgrade-larch install-stamp prune trust paragraph to match the proposed behavior, including unverified-install stamping, mtime backfill, running-dir retention, and verified-only pruning

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:240-240
- **Concern**: Plan updates only upgrade-larch.md but not SECURITY.md trust bullets. Scenario: Post-merge SECURITY.md still says prune never writes mtime-derived stamps and stamp writes target only verified/already-latest dirs; after Change 2 and backfill_install_stamps that text is false and misstates retention (running dir)
- **Proposed resolution**: Add SECURITY.md:240 to Files to modify: document stamp-on-any-successful-install with prune still gated; backfill mtime stamps during prune; retain target plus INSTALLED_VERSION

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:240; docs/installation-and-setup.md:40
- **Concern**: Plan changes install-stamp trust behavior but updates only the sibling script doc. Scenario: After the PR, canonical docs would still claim prune never writes mtime-derived stamps and stamp writes target only, while the script backfills stamps for every unstamped cached dir and stamps unverified installs
- **Proposed resolution**: Update these two lines minimally to match the new stamp/backfill contract, or remove Defect C/unverified stamping from the plan.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:240; docs/installation-and-setup.md:40
- **Concern**: Plan changes prune to persist mtime-derived install stamps for legacy cached dirs but only updates the sibling script contract; canonical security and install docs will still say prune does not write mtime stamps and only the verified/already-latest target is stamped.. Scenario: After merge, operators and reviewers rely on stale trust-model docs that omit the new write surface and changed rollback ranking behavior.
- **Proposed resolution**: Add minimal matching updates to SECURITY.md and docs/installation-and-setup.md, or drop Change 3 from the plan.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:240; docs/installation-and-setup.md:38-40
- **Concern**: Plan changes the /upgrade-larch install-stamp trust model but only updates the sibling script doc. SECURITY.md still says prune does not write stamps from mtimes and stamps only verified or already-latest stable dirs; installation docs say legacy unstamped dirs fall back to mtime at ranking time only.. Scenario: After this PR, canonical security/user docs would contradict the implemented behavior for unverified install stamping and mtime backfill.
- **Proposed resolution**: Keep the implementation scope narrow, but add targeted updates to SECURITY.md and docs/installation-and-setup.md for Change 2 and Change 3, or drop Change 3/unstable stamping if the two-file constraint is meant to remain binding.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-scope-creep-audit
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:185-207; docs/installation-and-setup.md:38-40
- **Concern**: Change 3 turns the current ranking-time-only mtime fallback for legacy unstamped dirs into a persistent stamp-on-prune backfill, despite the existing contract that stamped dirs sort before unstamped legacy dirs and mtime is only a fallback at ranking time.. Scenario: With Change 1 the running dir is already protected, and with Change 2 future installs are stamped. Backfilling every cached dir before ranking lets a recent legacy unstamped dir become stamped and outrank older real stamped installs, changing rollback cache retention beyond the urgent fix.
- **Proposed resolution**: Remove Change 3 from this plan, including the helper, prune call, doc bullets, and manual-test expectation. Keep only Changes 1 and 2; handle legacy stamp backfill in a separate scoped follow-up if still desired.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-doc-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:123
- **Concern**: Transient unstamped doc bullet overstates post-change behavior. Scenario: Backfill runs only inside prune_cached_versions; when prune is skipped (gh unavailable, verify fail) or stat_mtime/backfill write fails, dirs can stay unstamped across many runs — operators may think unstamped cache dirs are always short-lived
- **Proposed resolution**: Qualify sibling doc text: unstamped legacy dirs get mtime backfill at prune entry only; they persist until a prune run, and some may remain unstamped if backfill cannot run

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-doc-contract-sync
- **Severity**: important
- **Focus area**: security
- **Location**: AGENTS.md:19-21; SECURITY.md:240
- **Concern**: The plan changes the install-stamp trust model but does not update SECURITY.md, even though the current security text says prune does not write stamps from mtimes and stamp writes target only verified or already-latest stable directories.. Scenario: After the PR lands, security docs would deny the new mtime-backfill writes and unverified-success stamp writes, misleading reviewers and operators about the cache mutation surface.
- **Proposed resolution**: Add a minimal SECURITY.md update covering any successfully installed version stamp, verified-only prune, best-effort mtime backfill for numeric cached dirs, and target/running-dir retention.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-doc-contract-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:30-35; docs/installation-and-setup.md:38-40
- **Concern**: The sibling doc's edit-in-sync list names docs/installation-and-setup.md, but the plan omits updating it; its current cache paragraph would become stale after the proposed stamp and backfill behavior lands.. Scenario: Operators would read that stamps are written only for verified/already-latest stable installs and that legacy unstamped dirs fall back to mtime only at ranking time, while the script now stamps unverified successful installs and persistently backfills stamps before prune.
- **Proposed resolution**: Add a small docs/installation-and-setup.md edit matching the sibling contract: stamp any successful install, prune remains verified-only, running and target dirs are retained when present/version-shaped, and unstamped dirs are normally backfilled from mtime before ranking.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-doc-contract-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:19; <TMPDIR>/plan.txt:120-123
- **Concern**: The proposed sibling-doc wording says unstamped dirs are transient and only present until the next prune backfills them, but the planned helper skips dirs when stat_mtime returns 0 or stamp writes fail.. Scenario: On a read-only cache or stat failure, unstamped dirs remain and still sort below stamped dirs; the doc would overpromise that the unstamped tier disappears after every prune.
- **Proposed resolution**: Word the sibling doc as best-effort: unstamped numeric dirs are normally backfilled from mtime before ranking, but failed mtime reads or stamp writes leave them unstamped and bottom-ranked as before.
