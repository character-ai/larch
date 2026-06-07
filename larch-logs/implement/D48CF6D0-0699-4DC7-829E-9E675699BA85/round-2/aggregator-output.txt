### FINDING_1: Default Gate B auto-apply exposes SIMPLE runs without an equivalent quality/security gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Default Gate B auto-apply can merge accepted findings into `plan.txt` without operator confirmation; SIMPLE runs have no assessor, leaving only size brakes and validator escalation before publication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: Cursor auto-fix can mutate repo or host files without dirty-tree recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, dyn-autofix-launch-output.txt
- **Severity**: important
- **Concern**: Cursor auto-fix uses write-enabled trusted execution without a post-dispatch dirty-tree checkpoint, so prompt-injected or defective agents may mutate repo/home files outside the intended workspace and still let `/design` continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-security-output.txt, dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_3: Snapshot revert accepts symlink restore sources
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `revert-round` copies `restore_src` without rejecting symlinks, so a malicious snapshot symlink could pull arbitrary host file bytes into `plan.txt` and later into a public plan write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: Auto-fix agents can mutate non-target tmpdir artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: Write-enabled auto-fix is scoped to `$DESIGN_TMPDIR` but not mechanically limited to the target plan file, so agents can mutate session state, snapshots, review artifacts, or other tmpdir files that later steps trust.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_5: Auto-fix exposes unredacted plan contents to external vendors
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Validator logs are redacted in prompts, but the auto-fix agent can read the full workspace plan file, allowing secrets embedded in `plan.txt` to leak to Codex/Cursor vendor APIs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Revert failure can leave operator-visible rollback semantics incorrect
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Revert failure handling can continue after rollback fails or partially succeeds, leaving operators believing rollback occurred while the applied or partially restored plan state remains active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Auto-fix dispatch override env vars are too permissive
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_AUTOFIX_*` environment variables allow full dispatch override, so a compromised local shell environment could redirect auto-fix to attacker-controlled scripts outside test contexts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Stale Step 3 prose contradicts Gate B auto-apply default
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Runtime prose still says Gate B is always explicit, contradicting the new default auto-apply behavior and risking an unintended prompt when `approve_requested=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Auto-fix reuses stale validator evidence
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Auto-fix preserves one global validator log and reuses it across later failures, so subsequent Gate B or Step 5c defects may send/log stale evidence from an earlier validation site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Single-vendor auto-fix availability can burn duplicate attempts
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When only one vendor is available, auto-fix may retry that same vendor up to `MAX_ATTEMPTS`, wasting another full timeout before operator escalation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Python 3.11 floor is inconsistent with Ruff py312 target
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Lowering `requires-python` to 3.11 while leaving Ruff target at `py312` can allow Python 3.12-only syntax to pass lint while failing under the 3.11 runtime floor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Cursor auto-fix may lack required write-capable force mode
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Cursor auto-fix launcher omits write-capable `--force` mode, so Cursor-only auto-fix may fail to edit `plan.txt` and unnecessarily fall through to operator prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Auto-fix cycle sentinel is too coarse and durable
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: The auto-fix cycle cap is keyed only by site and not cleared across independent validator failures or Gate C re-run cycles, so later defects can skip available vendor auto-fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-design-flow-output.txt: Address the concern above.

### FINDING_14: Gate B auto-apply regression coverage is only static
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-runtime-compat-output.txt
- **Severity**: important
- **Concern**: Tests pin strings but do not mechanically exercise default auto-apply, `--approve` prompt restoration, or size-brake branches, so contradictory runtime prose and behavior can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_15: First-round HARD auto-apply lacks assessor substitute
- **Reviewer(s)**: dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: Step 3.6 skips assessor dispatch when `ROUND_NUM < 2`, so the common first-round auto-apply path removes the old Gate B human checkpoint without adding the intended assessor quality gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt: Address the concern above.

### FINDING_16: Revert path leaves stale post-apply completion state
- **Reviewer(s)**: dyn-design-flow-output.txt
- **Severity**: important
- **Concern**: Revert restores core plan/review files but does not clear post-apply sentinels, trailer snapshots, or postplan emit state, leaving contradictory settled-state markers after resume or re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt: Address the concern above.

### FINDING_17: Step 3.5 discussion routing still references unreachable Gate B branch
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: Step 3.5 prose says Round 2 discussion is reached through Gate B “Switch to discussion mode,” but default auto-apply skips the Gate B prompt; default-path discussion is via Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Python 3.11 floor changes are incidental scope creep
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: The branch bundles Python 3.11 floor alignment with unrelated `/design` Gate B work, increasing review and rollback surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Assessor skip behavior is pre-existing or specified
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: Some assessor-skip behavior predates the branch or is explicitly specified for SIMPLE until later work, though default auto-apply amplifies its impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_20: Auto-fix success path skips optional-trailer dedup/drift guard
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: important
- **Concern**: After successful auto-fix, the handler re-enters postplan validation without the Gate B trailer snapshot/dedup guard, allowing optional plan-size metadata to be corrupted or stale on the silent auto-apply path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_21: Auto-fix revalidation hides infrastructure failures
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: latent
- **Concern**: `revalidate()` silences validator stderr and treats infrastructure errors like ordinary remaining defects, potentially burning full vendor attempts without durable diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_22: Auto-fix KV capture lacks standard quiet-disable wrapper
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: latent
- **Concern**: The shared handler invokes `auto-fix-plan-commands.sh` without the `env LARCH_QUIET_DISABLE=1` wrapper used by other KV-capturing design fences, leaving the capture contract less structurally protected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Validator repo-root behavior is pre-existing
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: nit
- **Concern**: Initial validation and auto-fix both use the plugin root rather than a consumer repo root for Tier-3 resolution; this is unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Reduced Gate B chat visibility is intentional
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: nit
- **Concern**: Default auto-apply intentionally removes Gate B chat visibility, and logging auto-fix outcomes only through warnings matches the stated acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.

### FINDING_25: Python 3.11 py-lint path lacks clear version guard
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: `py-test` has an explicit Python 3.11+ guard, but `py-lint` does not, so Python 3.10 hosts may fail opaquely despite docs/CI describing both as 3.11 jobs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Python 3.12 reference mismatch appears resolved
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Runtime docs, CI, and config no longer appear to retain Python 3.12 references outside `larch-logs/` artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.
