### FINDING_1: Install docs omit sparse marketplace add
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `docs/installation-and-setup.md` still documents a full `claude plugin marketplace add` without `--sparse` while the Upgrade section describes sparse/in-place refresh. New users who follow only Install get a full clone (including `larch-logs` and npm payload) until a later `/upgrade-larch`. Install commands should use the same sparse cone as `upgrade-larch.sh` (or cross-link and show the full sparse dir list).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_2: Skill catalog misstates /upgrade-larch steady-state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `docs/skills.md` still says upgrade removes and re-adds the marketplace every run. Readers expect always-slow teardown; steady-state in-place sparse update is undocumented in the primary catalog. Rewrite the `/upgrade-larch` section to match `upgrade-larch.md` and add `docs/skills.md` to Edit-in-sync.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: SKILL.md intro shows non-sparse marketplace add
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/upgrade-larch/SKILL.md` intro still shows non-sparse marketplace add for standard GitHub install. Operators following SKILL.md for manual setup miss `--sparse` and get a full clone. Update the intro command to include `--sparse` (same cone as the script) or defer to `upgrade-larch.md`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: upgrade-larch.md Edit-in-sync Makefile claim stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Edit-in-sync claims Makefile wires local validation targets after harness removal. Maintainers search Makefile for deleted `test-upgrade-larch` targets. Remove or reword the Makefile bullet to reflect remaining wiring (e.g. `lint-mermaid` only).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: Duplicated marketplace remove + sparse add branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `upgrade-larch.sh` duplicates marketplace remove + sparse add in fallback and else branches. Future edits may update one branch only and diverge silently. Extract a shared `sparse_marketplace_readd` helper used by both branches and recovery banners.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_6: Sparse vs legacy clone detection is heuristic and brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-clone-detection-output.txt
- **Severity**: latent
- **Concern**: Steady-state vs migration is inferred mainly from absence of `larch-logs/` (and related directory heuristics), not verified sparse-checkout state. Legacy full clones with `larch-logs/` removed, file/symlink paths named `larch-logs`, or pulls that re-materialize excluded trees can take `marketplace update` instead of one-time `remove` + `add --sparse`, leaving fat installs, ambiguous cones, or committed run logs copied back into the plugin cache. Detection should key off git sparse-checkout (or explicit markers/secondary legacy signals), not directory presence alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-clone-detection-output.txt: Treat any existing `larch-logs` path as legacy, e.g. `[ -e "$MARKETPLACE_CLONE/larch-logs" ]` in the `else` branch condition (or combine `! -d` with `[ -f ]` / `[ -L ]` checks), or probe git sparse-checkout state (`git -C "$MARKETPLACE_CLONE" sparse-checkout list`) instead of inferring from filesystem shape alone.
  - From dyn-sparse-clone-detection-output.txt: Add secondary legacy signals the sparse cone will never have after migration—e.g. `[ -e "$MARKETPLACE_CLONE/package.json" ]` or `[ -d "$MARKETPLACE_CLONE/mermaid-lint" ]` on pre-migration trees—or require `git -C "$MARKETPLACE_CLONE" sparse-checkout list` to succeed and show the expected cone before taking the update path; otherwise force the `remove` + `add --sparse` branch.

### FINDING_7: Manual recovery banners omit marketplace remove
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Manual recovery banners in `upgrade-larch.sh` omit marketplace remove before sparse add. Post-failure manual steps may fail if a marketplace entry already exists in a bad state. Match recovery text to the script else branch (remove, then sparse add, then install).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_8: [OUT_OF_SCOPE] stat_mtime duplicated in cleanup.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stat_mtime` is duplicated in `cleanup.sh`. Portability fixes must be applied in two places. Extract `scripts/lib-stat-mtime.sh` (pre-existing; not introduced here).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_9: README upgrade row describes remove+re-add
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: README skill table still says upgrade removes and re-adds the marketplace. Same risk as stale catalog text: manual full re-add without `--sparse`. Update the row to sparse checkout + in-place update wording.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_10: Steady-state update does not refresh sparse cone when includes change
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On the marketplace-update path, `upgrade-larch.sh` does not expand or reapply `--sparse` when `LARCH_SPARSE_DIRS` gains a new top-level directory. A future release can add a shipped top-level dir and update the include list; existing sparse installs pull successfully but never gain the new path in the clone, so plugin install succeeds but runtime files are missing. Detect sparse-cone / include-list drift after update and force `remove` + `add --sparse` when the cone changes; document in `upgrade-larch.md`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_11: CHANGELOG still references removed test-upgrade-larch harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Historical `CHANGELOG.md` line still mentions `test-upgrade-larch-prune.sh` (or related harness name). Repo-wide `git grep test-upgrade-larch` still hits that line though Makefile/CI harness references were removed, so plan/PR acceptance expecting zero grep hits can fail. Reword or remove the bullet, narrow acceptance grep scope, or document CHANGELOG as exempt historical text.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_12: Hook doc overstates mmdc requirement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/installation-and-setup.md` hook/dev-setup text overstates the mmdc requirement after lazy toolchain resolution. Contributors editing Markdown without Mermaid fences may believe `npm ci` is mandatory when the hook now exits 0 without probing mmdc. Update dev-setup text to match `lint-mermaid-fences.md`: toolchain required only when fences are present.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_13: [OUT_OF_SCOPE] test-mermaid harness tolerates missing mmdc
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-mermaid-fragments.sh` can pass nested-fence lint without resolving `mermaid-lint/node_modules/.bin/mmdc`; only the lint-mermaid job covers the repointed path (pre-existing gap, file untouched by this branch). Consider tightening the harness or adding a cheap path probe for stronger regression signal later.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_14: [OUT_OF_SCOPE] Puppeteer --no-sandbox CI fallback pre-existing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-mermaid-fences.sh` Puppeteer `--no-sandbox` render fallback for CI is pre-existing. Dev/CI Chromium runs without sandbox on Linux runners; local dev risk unchanged by this PR. No change required here; track separately if hardening CI sandbox is desired.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: [OUT_OF_SCOPE] Global mmdc PATH fallback trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Global mmdc PATH fallback is pre-existing. A malicious `mmdc` earlier on PATH could run during local lint. Prefer repo-pinned binary only or document PATH trust for dev setups.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_16: [OUT_OF_SCOPE] SECURITY.md omits sparse-install payload boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` omits sparse-install payload boundary. Security auditors reading `SECURITY.md` alone may miss what consumer installs exclude. Add a sparse-install trust paragraph when `SECURITY.md` is next edited in sync.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: First-hop upgrade from pre-sparse release skips sparse migration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Sparse migration may not run on the first hop from a pre-sparse release: the old installed script runs the upgrade and idempotent exit can skip marketplace refresh afterward. A user on release N−1 upgrading once to N (this PR) may still get a full marketplace clone; the next `/upgrade-larch` at latest stable can exit 0 without sparse re-add, leaving fat installs (~61k files + npm) until N+1 or manual repair. Before idempotent exit, detect legacy/fat marketplace or install and force sparse `remove`+`add`, or document mandatory second upgrade/manual steps.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_18: Upgrade docs overstate single-hop sparse migration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Upgrade docs claim the first upgrade performs sparse re-add for all users. Single-hop upgraders from the prior release may not run sparse migration on that upgrade, misleading operators troubleshooting install size. Document two-hop migration or manual sparse re-add and align with `upgrade-larch.md` recovery commands.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_19: Marketplace update fallback can leave corrupt clone after uninstall
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: important
- **Concern**: On `marketplace update` failure, fallback runs `marketplace remove` with `|| true` then mandatory `marketplace add`. If `remove` fails but `add` also fails, `set -e` aborts after the plugin was already uninstalled, potentially leaving `~/.claude/plugins/marketplaces/larch-local` corrupt and `larch-local` not installable without manual cleanup. The script does not surface remove failure or suggest deleting `$MARKETPLACE_CLONE` when add fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-clone-detection-output.txt: After a failed `remove`, log an explicit warning with the clone path; if `add` fails, extend the verification-failure / `recover()` text to include `rm -rf` of `$MARKETPLACE_CLONE` plus the sparse `marketplace add` command, or gate `add` on a successful remove / absent directory check.

### FINDING_20: [OUT_OF_SCOPE] recover() ERR banner omits marketplace remove
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `recover()` ERR banner omits marketplace remove before sparse re-add (and related uninstall/marketplace teardown). Manual recovery after partial failure or mid-pipeline failure may fail on stale marketplace registration or add conflicts. Pre-existing; optional follow-up to extend `recover()` with full teardown sequence.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_21: [OUT_OF_SCOPE] docs/skills.md catalog stale (plan out of scope)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Catalog text still describes remove+re-add marketplace flow. Readers of `docs/skills.md` get an outdated mental model vs `upgrade-larch.md` and `SKILL.md`. Update the `/upgrade-larch` section to match sparse checkout and in-place marketplace update (not in plan file list).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_22: [OUT_OF_SCOPE] Fresh install docs omit --sparse (plan follow-up)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Fresh install docs omit `--sparse`. New installs via the Install section still get a full clone until first `/upgrade-larch`. Consider sparse marketplace add on first install in a follow-up (explicitly out of plan scope).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_23: [OUT_OF_SCOPE] LARCH_SPARSE_DIRS CLI usage is correct
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: nit
- **Concern**: `LARCH_SPARSE_DIRS` usage is correct: CLI paths use intentional word-splitting with `# shellcheck disable=SC2086`; recovery and verification strings only echo the expanded command for copy-paste and do not execute it.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_24: [OUT_OF_SCOPE] .git as file (worktree) routes to re-add path
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: nit
- **Concern**: When `.git` is a file (worktree), `[ -d "$MARKETPLACE_CLONE/.git" ]` is false, so the script takes the else re-add path—safe, if slightly heavy-handed.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_25: [OUT_OF_SCOPE] Uninstall-before-marketplace teardown risk pre-existing
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: nit
- **Concern**: Uninstall-before-marketplace at `upgrade-larch.sh:270-271` means any marketplace/install failure leaves the operator without an installed plugin; pattern predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_26: [OUT_OF_SCOPE] test-upgrade-larch references only in larch-logs and CHANGELOG
- **Reviewer(s)**: dyn-sparse-clone-detection-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch*` references remain only under `larch-logs/` and `CHANGELOG.md`, not in runtime/Makefile surfaces—consistent with Part 4 of the plan (informational; overlaps FINDING_11 acceptance nuance).
- **Suggested revisions (informational for voters; coder decides)**:
