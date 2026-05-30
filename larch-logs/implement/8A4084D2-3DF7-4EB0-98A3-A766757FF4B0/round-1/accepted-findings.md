### FINDING_1: Install docs omit sparse marketplace add
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `docs/installation-and-setup.md` still documents a full `claude plugin marketplace add` without `--sparse` while the Upgrade section describes sparse/in-place refresh. New users who follow only Install get a full clone (including `larch-logs` and npm payload) until a later `/upgrade-larch`. Install commands should use the same sparse cone as `upgrade-larch.sh` (or cross-link and show the full sparse dir list).
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


### FINDING_7: Manual recovery banners omit marketplace remove
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Manual recovery banners in `upgrade-larch.sh` omit marketplace remove before sparse add. Post-failure manual steps may fail if a marketplace entry already exists in a bad state. Match recovery text to the script else branch (remove, then sparse add, then install).
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_9: README upgrade row describes remove+re-add
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: README skill table still says upgrade removes and re-adds the marketplace. Same risk as stale catalog text: manual full re-add without `--sparse`. Update the row to sparse checkout + in-place update wording.
- **Suggested revisions (informational for voters; coder decides)**:


