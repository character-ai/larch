### OOS_1:
- **Description**: Stale `current-implement-env-*.sh` regular files are never reaped. Scenario: Cleanup only removes dangling `current-design-env-*.sh` symlinks; crashed runs before Step 18 leave orphan pointer files until manual deletion or overwrite
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/cleanup/scripts/cleanup.sh:133-145
- **Phase**: design

### OOS_2:
- **Description**: When design and implement pointers both match `cwd`, newest mtime wins without `SKILL_KIND` priority. Scenario: A paused `/design` symlink newer than the implement pointer can make `p` show design progress during an active `/implement`
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/progress_report.py:37-42
- **Phase**: design

