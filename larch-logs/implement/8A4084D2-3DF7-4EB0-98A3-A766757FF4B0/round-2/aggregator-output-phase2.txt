Normalized aggregator output from the supplied reviewer slots. Merged items that describe the same behavioral risk; kept separate items that imply different fixes or code paths. `[OUT_OF_SCOPE]` sources are listed under `### OOS_N:` and were not merged into in-scope findings (including counter-evidence that disputes in-scope cone-matching risk).

### FINDING_1: Sparse cone equality may never match, blocking steady-state marketplace update
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `marketplace_sparse_cone_matches` compares raw or normalized `git sparse-checkout list` output to `LARCH_SPARSE_DIRS` tokens; cone-mode CLI/git output may include meta-patterns, `/*` / `!/*/`, or other formatting that does not equal bare sorted directory names. If the check is almost always false, steady-state `claude plugin marketplace update` is skipped and every upgrade (or repair) does remove + sparse re-add instead of in-place update, defeating Part 2 speed goals and adding operator churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Normalize both sides before compare or use plan probe: .git present and larch-logs absent for update path; keep strict cone compare only if normalized
  - From cursor-specialist-correctness-output.txt: Normalize paths before compare or use a dedicated sparse marker instead of raw list output.
  - From cursor-specialist-testing-output.txt: Operator-verify sparse-checkout list after add; adjust normalize/compare to match real CLI output or relax check beyond string equality.
  - From cursor-specialist-edge-cases-output.txt: Operator-verify list format after sparse add; normalize comparison or match documented CLI/git output
  - From cursor-specialist-plan-fidelity-output.txt: Operator-verify sparse-checkout list format matches normalization on real install; adjust comparison if needed.

### FINDING_2: Already-latest path repairs marketplace but does not slim active plugin install
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When the operator is already on latest stable, marketplace cone repair can run without uninstall+install. Legacy fat dirs (`larch-logs/`, install-time `node_modules/`, etc.) can remain in the active `PLUGIN_ROOT` cache until a version bump, so disk/speed wins are deferred for always-current users.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After marketplace repair on the already-latest branch (or when legacy larch-logs/ was detected), run uninstall+install or document mandatory one-time reinstall.
  - From cursor-specialist-security-output.txt: Resync cache on cone repair (same-version install) or document that only marketplace—not active install—was slimmed
  - From cursor-specialist-edge-cases-output.txt: Detect legacy install artifacts on idempotent path and force one-time uninstall+install; note restart when slimming reinstall runs

### FINDING_3: Already-latest branch mutates marketplace contrary to closed plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The already-latest early-exit calls `refresh_larch_marketplace` when the cone check fails, contradicting the closed plan decision that the idempotent path performs no marketplace mutation. Users on latest stable with a legacy full marketplace clone can trigger remove + sparse re-add on every `/upgrade-larch` without a plugin reinstall, whereas the plan intended one-time migration on the next actual upgrade only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Remove marketplace repair from the already-latest branch; keep repair only on the upgrade path; revert related doc claims in upgrade-larch.md step 2 and docs/installation-and-setup.md Upgrade paragraph.

### FINDING_4: Failed marketplace remove is ignored before sparse re-add
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: latent
- **Concern**: In `refresh_larch_marketplace`, failed `claude plugin marketplace remove` is swallowed (`|| true`) but `add_sparse_larch_marketplace` still runs while `$MARKETPLACE_CLONE` may remain. `marketplace add` can fail with already-exists, tripping `ERR`/`recover()` after uninstall on the full upgrade path—leaving no installed plugin and a wedged marketplace until manual `rm -rf` and recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed unless clone dir is absent; align with recovery banner rm -rf step.
  - From cursor-specialist-security-output.txt: Fail closed on remove failure or require manual rm -rf of MARKETPLACE_CLONE before add
  - From cursor-specialist-edge-cases-output.txt: Fail closed on remove failure for re-add path, or rm -rf clone before add when remove fails
  - From dyn-shell-upgrade-logic-output.txt: Before `add_sparse_larch_marketplace` in both re-add branches, if `remove_larch_marketplace` fails (or unconditionally when `[ -d "$MARKETPLACE_CLONE" ]`), run `rm -rf -- "$MARKETPLACE_CLONE"` and log that automatic cleanup ran; then call `add_sparse_larch_marketplace`. Keep `recover()` as the backstop for add/network failures.
  - From dyn-migration-path-risk-output.txt: Mirror `recover()` inside the automated re-add paths: if `remove_larch_marketplace` fails (or before any sparse re-add), `rm -rf -- "$MARKETPLACE_CLONE"` when `[ -d "$MARKETPLACE_CLONE" ]`, then call `add_sparse_larch_marketplace`; optionally log that automatic cleanup ran. Keep the existing warning/recovery banner as a backstop for add/network failures.

### FINDING_5: Sparse include list duplicated without drift guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The sparse include list is duplicated across `upgrade-larch.sh`, install docs, `SKILL.md`, and `docs/skills.md` with no automated drift test after harness removal. A new top-level runtime dir added to the script but omitted from prose copies can ship incomplete consumer installs while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize list in upgrade-larch.sh; docs reference LARCH_SPARSE_DIRS or one shared snippet
  - From cursor-specialist-testing-output.txt: Treat LARCH_SPARSE_DIRS as sole executable source; cross-link docs; or accept plan comment-only maintenance.
  - From cursor-specialist-security-output.txt: Document invariant in SECURITY.md/upgrade-larch.md or add separate dir-list drift check
  - From cursor-specialist-edge-cases-output.txt: Add lightweight ls-tree vs sparse-list lint or release checklist (not full upgrade harness)
  - From cursor-specialist-plan-fidelity-output.txt: Extend MAINTENANCE comment to list all sync sites or consolidate to one canonical reference.

### FINDING_6: Upgrade-larch offline harnesses removed with no CI substitute
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: All offline upgrade-larch and prune harnesses were removed per plan Part 4 with no CI substitute. Regressions in prune cap, gh redaction, sparse refresh, or already-latest repair can ship without automated signal (plan-accepted; needs explicit manual verification in PR/acceptance).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_7: upgrade-larch.md step 2 wording misstates idempotent marketplace behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Idempotency step 2 says a valid sparse clone is left alone, but code can still refresh/repair the marketplace on the already-latest path. Operators miss that stale-cone repair can run marketplace update without matching steady-state vs repair branches in step 4.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_8: upgrade-larch.md stale step cross-reference (prune step 8 vs 7)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: After step renumbering, the idempotency bullet still says prune runs at step 8 while prune is now step 7, misdirecting readers tracing behavior cross-references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Change step 8 to step 7 in the idempotency bullet.

### FINDING_9: Install docs --sparse enumeration beyond closed plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `docs/installation-and-setup.md` Install section documents `--sparse` though closed plan Part 5 only authorized the Upgrade paragraph change. Strict plan-traceability reviewers may treat this as undeclared scope expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document intentional scope expansion in PR notes, or revert Install section if strict adherence required.

### FINDING_10: mmdc resolved only under mermaid-lint after toolchain move
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `lint-mermaid-fences` resolves `mmdc` only under `mermaid-lint/node_modules`. Developers with legacy root `node_modules` still fail fenced-md lint until `(cd mermaid-lint && npm ci)`; migration note may be needed beyond docs already updated in installation-and-setup.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_11: mermaid-safe-content.md still documents root npm audit
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: latent
- **Concern**: After Part 3 removed root `package.json`, the shared skill contract still tells maintainers to run bare `npm audit` from repo root, breaking the documented bump workflow vs `mermaid-lint/package.json` and `(cd mermaid-lint && npm ci)` used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mermaid-path-sync-output.txt: Change the sentence to run audit from the toolchain directory (for example, “Run `(cd mermaid-lint && npm audit)` opportunistically during bumps”) so it matches `docs/installation-and-setup.md`, `docs/linting.md`, and the `(cd mermaid-lint && npm ci)` pattern used everywhere else.

### OOS_1: [OUT_OF_SCOPE] ERR trap recover prints banner without exiting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `recover` prints recovery guidance without exiting; unrelated failures may continue afterward (pre-existing). Tightening global error handling may require `recover` to exit 1.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] lint-mermaid-fences.sh lazy ensure_mmdc refactor beyond minimal repoint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Broader lazy `ensure_mmdc` refactor widens diff surface on an install-speed PR; defer or split if a smaller PR is preferred.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] test-mermaid-fragments accepts exit 2 when mmdc missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Shard 9 can pass without mermaid-lint toolchain for nested-fence case; pre-existing, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Wildcard Bash allowlist for all larch script paths unchanged
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Compromised or unexpected script under any cached version remains pre-authorized; narrow allowlist is a follow-up, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Install-stamp prune contract lacks dedicated harness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After `test-upgrade-larch-prune` removal, future prune/stamp regressions lack CI signal (plan-accepted tradeoff).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] ERR trap after uninstall mid-upgrade leaves plugin uninstalled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing failure mode unrelated to sparse-checkout changes; operator must run manual recover.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Prune keeps eight stamped dirs; legacy fat versions age out slowly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing; harness removal increases refactor risk without CI guard; plan-intentional test removal.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] CHANGELOG historical entries rewritten
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Removed test-upgrade-larch names from historical changelog entries; not required by plan; no functional impact.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Cone matching likely correct for current git cone output
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: sorted `git sparse-checkout list` vs sorted `normalize_sparse_dirs` is order-robust; cone mode emits bare directory names, so string equality is not inherently format-broken for current git behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] recover() ERR trap and already-latest failure ordering
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt
- **Severity**: nit
- **Concern**: `trap recover ERR` expands variables at call time; if `refresh_larch_marketplace` fails on already-latest repair, script aborts before printing misleading “Already at latest…” success line.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_11: [OUT_OF_SCOPE] Already-latest marketplace-only repair is contract-intentional
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: documented in upgrade-larch.md; repair without reinstall does not strand the user without an install the way upgrade-path remove-then-failed-add can; on success stamp/prune still run and exit 0.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_12: [OUT_OF_SCOPE] Round-1 migration from pre-sparse release
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt
- **Severity**: latent
- **Concern**: First hop from older script on a version bump may still use prior marketplace logic until a second `/upgrade-larch` at latest stable; pre-existing migration class, not introduced by cone helpers alone.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_13: [OUT_OF_SCOPE] Test removal (Part 4) intentional
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Harness deletion is plan-intentional; no additional in-scope shell defect from deletion alone for this focus area.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_14: [OUT_OF_SCOPE] Recovery contract documents manual rm -rf; gap is automation only
- **Reviewer(s)**: dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: upgrade-larch.md and `recover()`/verification banners already document operator steps when remove+add fails.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_15: [OUT_OF_SCOPE] Mermaid path repointing otherwise consistent
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: lint script, Makefile, CI cache paths, and docs align on `mermaid-lint/`; `test-mermaid-fragments.sh` delegates without hardcoded root `node_modules`; setup-node cache pattern matches subdirectory lockfile.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_16: [OUT_OF_SCOPE] Legacy gitignored root node_modules not used by new resolution
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: nit
- **Concern**: Pre-move root `node_modules` may linger locally but is not used by updated resolution order and was not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
